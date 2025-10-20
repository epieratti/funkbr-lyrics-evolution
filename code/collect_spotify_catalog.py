#!/usr/bin/env python
"""Spotify catalog collector with retry, locking and dry-run support."""
from __future__ import annotations

import argparse
import fcntl
import json
import os
import sys
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional

try:
    from spotify_client import SpotifyClient, SpotifyClientError
except ImportError:  # pragma: no cover - fallback when executed as module
    from .spotify_client import SpotifyClient, SpotifyClientError  # type: ignore[no-redef]


def load_env_file(env_path: Path) -> None:
    """Load a minimal set of environment variables from .env if missing."""
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key in {"SPOTIFY_CLIENT_ID", "SPOTIFY_CLIENT_SECRET"} and key not in os.environ:
            os.environ[key] = os.path.expandvars(value)


def chunked(seq: Iterable[Any], size: int) -> Iterator[List[Any]]:
    bucket: List[Any] = []
    for item in seq:
        bucket.append(item)
        if len(bucket) >= size:
            yield bucket
            bucket = []
    if bucket:
        yield bucket


def atomic_append_jsonl(path: Path, row: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.parent / f".{path.name}.tmp"
    with tmp_path.open("w", encoding="utf-8") as handle:
        json.dump(row, handle, ensure_ascii=False)
        handle.write("\n")
    with path.open("ab") as target, tmp_path.open("rb") as src:
        target.write(src.read())
    tmp_path.unlink(missing_ok=True)


def json_log(event: str, **payload: Any) -> None:
    data = {"event": event, "ts": int(time.time()), **payload}
    print(json.dumps(data, ensure_ascii=False), flush=True)


@contextmanager
def exclusive_lock(lock_path: Path) -> Iterator[None]:
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(lock_path, os.O_RDWR | os.O_CREAT)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        json_log("lock_acquired", lock=str(lock_path))
        yield
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


def collect_artist_catalog(
    client: SpotifyClient,
    artist_query: str,
    market: str,
    out_path: Path,
) -> int:
    search_payload = client.get(
        "https://api.spotify.com/v1/search",
        params={"q": artist_query, "type": "artist", "limit": 1, "market": market},
    )
    items = search_payload.get("artists", {}).get("items", [])
    if not items:
        warn_row = {
            "_type": "warn",
            "artist_query": artist_query,
            "market": market,
            "warning": "artist_not_found",
            "ts": int(time.time()),
        }
        atomic_append_jsonl(out_path, warn_row)
        json_log("artist_not_found", query=artist_query, market=market)
        return 0

    artist_id = items[0]["id"]
    artist_detail = client.get(f"https://api.spotify.com/v1/artists/{artist_id}")
    artist_row = {
        "_type": "artist_meta",
        "artist_query": artist_query,
        "artist_id": artist_id,
        "artist_name": artist_detail.get("name"),
        "followers": (artist_detail.get("followers") or {}).get("total"),
        "popularity": artist_detail.get("popularity"),
        "genres": ",".join(artist_detail.get("genres") or []),
        "market": market,
        "ts": int(time.time()),
    }
    atomic_append_jsonl(out_path, artist_row)
    json_log("artist_collected", artist_id=artist_id, query=artist_query)

    albums: List[Dict[str, Any]] = []
    next_url: Optional[str] = f"https://api.spotify.com/v1/artists/{artist_id}/albums"
    params = {
        "include_groups": "album,single,appears_on,compilation",
        "market": market,
        "limit": 50,
    }
    while next_url:
        page = client.get(next_url, params=params)
        params = {}
        albums.extend(page.get("items", []) or [])
        next_url = page.get("next")

    album_meta: Dict[str, Dict[str, Any]] = {}
    for batch in chunked([alb["id"] for alb in albums], 20):
        details = client.get("https://api.spotify.com/v1/albums", params={"ids": ",".join(batch)})
        for album in details.get("albums", []) or []:
            ext = album.get("external_ids") or {}
            album_meta[album["id"]] = {
                "album_label": album.get("label"),
                "album_release_date": album.get("release_date"),
                "album_release_precision": album.get("release_date_precision"),
                "album_type": album.get("album_type"),
                "album_total_tracks": album.get("total_tracks"),
                "album_upc": ext.get("upc"),
            }

    track_pairs: List[Dict[str, str]] = []
    for album in albums:
        album_tracks = client.get(
            f"https://api.spotify.com/v1/albums/{album['id']}/tracks",
            params={"market": market, "limit": 50},
        )
        for track in album_tracks.get("items", []) or []:
            track_pairs.append({"album_id": album["id"], "track_id": track["id"]})

    total_rows = 0
    for batch in chunked([pair["track_id"] for pair in track_pairs], 50):
        track_details = client.get(
            "https://api.spotify.com/v1/tracks", params={"ids": ",".join(batch)}
        )
        for track in track_details.get("tracks", []) or []:
            album_id = track.get("album", {}).get("id")
            markets = track.get("available_markets") or []
            row = {
                "_type": "track_row",
                "artist_id": artist_id,
                "artist_query": artist_query,
                "album_id": album_id,
                "album_label": album_meta.get(album_id, {}).get("album_label"),
                "album_release_date": album_meta.get(album_id, {}).get("album_release_date"),
                "album_release_precision": album_meta.get(album_id, {}).get(
                    "album_release_precision"
                ),
                "album_type": album_meta.get(album_id, {}).get("album_type"),
                "album_total_tracks": album_meta.get(album_id, {}).get("album_total_tracks"),
                "album_upc": album_meta.get(album_id, {}).get("album_upc"),
                "track_id": track.get("id"),
                "track_name": track.get("name"),
                "duration_ms": track.get("duration_ms"),
                "explicit": track.get("explicit"),
                "track_number": track.get("track_number"),
                "disc_number": track.get("disc_number"),
                "track_popularity": track.get("popularity"),
                "preview_url": track.get("preview_url"),
                "available_in_BR": "BR" in markets,
                "n_markets": len(markets),
                "available_markets": markets,
                "isrc": (track.get("external_ids") or {}).get("isrc"),
                "market": market,
                "ts": int(time.time()),
            }
            atomic_append_jsonl(out_path, row)
            json_log("track_persisted", track_id=row["track_id"], n_markets=row["n_markets"])
            total_rows += 1
    return total_rows


def dry_run(fixtures_path: Path) -> None:
    json_log("dry_run_start", fixtures=str(fixtures_path))
    for fixture_file in sorted(fixtures_path.glob("*.jsonl")):
        for line in fixture_file.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            payload = json.loads(line)
            json_log("dry_run_row", source=str(fixture_file), row=payload)
    json_log("dry_run_complete")


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Spotify catalog collector")
    parser.add_argument("--limit-artists", type=int, default=5)
    parser.add_argument("--snapshot", help="Snapshot identifier", required=False)
    parser.add_argument("--seed", default="seed/seed_artists.txt")
    parser.add_argument("--market", default=os.getenv("MARKET", "BR"))
    parser.add_argument("--output", default=None, help="Override output JSONL path")
    parser.add_argument(
        "--dry-run", action="store_true", help="Use fixtures instead of real API calls"
    )
    parser.add_argument(
        "--fixtures",
        default="tests/fixtures",
        help="Directory with dry-run JSONL fixtures",
    )
    parser.add_argument("--lock-file", default="locks/collect_spotify_catalog.lock")
    return parser.parse_args(argv)


def resolve_output(snapshot: Optional[str], override: Optional[str]) -> Path:
    if override:
        return Path(override)
    snapshot = snapshot or time.strftime("%Y%m%d")
    return Path("data/raw") / f"funk_br_discografia_raw_{snapshot}.jsonl"


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    repo_root = Path(__file__).resolve().parent.parent
    load_env_file(repo_root / ".env")

    if args.dry_run:
        dry_run(Path(args.fixtures))
        return 0

    out_path = resolve_output(args.snapshot, args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        client = SpotifyClient.from_env()
    except SpotifyClientError as exc:
        print(f"❌ {exc}", file=sys.stderr)
        return 2

    seed_path = Path(args.seed)
    if not seed_path.exists():
        print(f"❌ seed file not found: {seed_path}", file=sys.stderr)
        return 3

    with seed_path.open(encoding="utf-8") as handle:
        artists = [line.strip() for line in handle if line.strip() and not line.startswith("#")]
    artists = artists[: args.limit_artists]

    json_log("collector_start", artists=len(artists), market=args.market, out=str(out_path))
    lock_path = Path(args.lock_file)
    total_rows = 0
    start = time.time()
    try:
        with exclusive_lock(lock_path):
            for idx, artist in enumerate(artists, start=1):
                try:
                    rows = collect_artist_catalog(client, artist, args.market, out_path)
                    total_rows += rows
                    json_log("artist_done", artist_query=artist, rows=rows, index=idx)
                except Exception as exc:  # noqa: BLE001
                    json_log("artist_error", artist_query=artist, error=str(exc))
    except BlockingIOError:
        print(f"❌ lock busy: {lock_path}", file=sys.stderr)
        return 4

    elapsed = time.time() - start
    json_log(
        "collector_complete",
        artists=len(artists),
        rows=total_rows,
        seconds=round(elapsed, 2),
    )
    print(f"[ok] wrote -> {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
