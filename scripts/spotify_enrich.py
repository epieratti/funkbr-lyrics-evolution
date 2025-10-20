#!/usr/bin/env python
import os, sys, json, time, itertools
from typing import Iterable, Dict, Any, List, Optional
from dotenv import load_dotenv

# ---- deps Spotify ----
try:
    import spotipy
    from spotipy.oauth2 import SpotifyClientCredentials
except Exception as e:
    print("❌ spotipy não encontrado. Rode: source venv/bin/activate && pip install spotipy python-dotenv", file=sys.stderr)
    sys.exit(2)

def chunked(seq: Iterable[str], n: int) -> Iterable[List[str]]:
    it = iter(seq)
    while True:
        batch = list(itertools.islice(it, n))
        if not batch:
            return
        yield batch

def backoff_sleep(resp_headers: Dict[str, str], default: float = 1.0):
    retry = resp_headers.get("Retry-After")
    if retry:
        try:
            time.sleep(float(retry))
            return
        except: pass
    time.sleep(default)

def load_artists_from_jsonl(path: str) -> List[Dict[str, Any]]:
    out = []
    with open(path, "r", encoding="utf-8") as f:
        for ln in f:
            ln = ln.strip()
            if not ln: continue
            try:
                d = json.loads(ln)
                if d.get("artist_id") or d.get("artist_name"):
                    out.append(d)
            except: 
                continue
    return out

def pick_artist_id(sp: "spotipy.Spotify", rec: Dict[str, Any], market: Optional[str]) -> Optional[str]:
    """Prefer artist_id; fallback: search by name."""
    if rec.get("artist_id"):
        return rec["artist_id"]
    name = (rec.get("artist_name") or rec.get("artist_query") or "").strip()
    if not name:
        return None
    q = f'artist:"{name}"'
    while True:
        try:
            res = sp.search(q=q, type="artist", limit=1, market=market or None)
            items = (res.get("artists") or {}).get("items") or []
            return items[0]["id"] if items else None
        except spotipy.SpotifyException as e:
            if e.http_status == 429:
                backoff_sleep(getattr(e, "headers", {}) or {})
                continue
            raise

def get_all_albums(sp: "spotipy.Spotify", artist_id: str, market: Optional[str])_

# Garante backup antes de editar
cp code/coletar_discografia_funk_br.py code/coletar_discografia_funk_br.py.bak_$(date +%H%M)

# Adiciona helper completo e integração automática
cat >> code/utils/spotify_collect.py <<'PY'
from typing import Iterable, Dict, List
from spotipy import Spotify
from itertools import islice
import os, json

def chunked(iterable: Iterable[str], size: int) -> Iterable[List[str]]:
    it = iter(iterable)
    while True:
        batch = list(islice(it, size))
        if not batch: break
        yield batch

def fetch_artist_catalog_with_isrc(sp: Spotify, artist_id: str, market: str = "BR") -> List[Dict]:
    albums, seen = [], set()
    resp = sp.artist_albums(artist_id, include_groups="album,single,appears_on,compilation", market=market, limit=50)
    while True:
        for a in resp.get("items", []):
            if a["id"] in seen: continue
            seen.add(a["id"]); albums.append(a)
        if resp.get("next"): resp = sp.next(resp)
        else: break

    album_meta = {}
    for batch in chunked([a["id"] for a in albums], 20):
        det = sp.albums(batch)
        for a in det.get("albums", []):
            album_meta[a["id"]] = {
                "upc": (a.get("external_ids") or {}).get("upc"),
                "release_date": a.get("release_date"),
                "release_date_precision": a.get("release_date_precision"),
                "label": a.get("label"),
                "album_type": a.get("album_type"),
            }

    album_tracks = []
    for alb in albums:
        tr = sp.album_tracks(alb["id"], market=market, limit=50)
        items = tr.get("items", [])
        while tr.get("next"):
            tr = sp.next(tr); items.extend(tr.get("items", []))
        for t in items: album_tracks.append((alb, t))

    ids = [t["id"] for _, t in album_tracks if t.get("id")]
    track_meta = {}
    for batch in chunked(ids, 50):
        det = sp.tracks(batch)
        for trk in det.get("tracks", []):
            ext = trk.get("external_ids") or {}
            track_meta[trk["id"]] = {
                "isrc": ext.get("isrc"),
                "popularity": trk.get("popularity"),
                "duration_ms": trk.get("duration_ms"),
                "explicit": trk.get("explicit"),
                "spotify_url": (trk.get("external_urls") or {}).get("spotify"),
            }

    features = {}
    for batch in chunked(ids, 100):
        feats = sp.audio_features(batch) or []
        for f in feats:
            if not f: continue
            features[f["id"]] = {
                "danceability": f.get("danceability"),
                "energy": f.get("energy"),
                "tempo": f.get("tempo"),
                "key": f.get("key"),
                "mode": f.get("mode"),
                "loudness": f.get("loudness"),
                "time_signature": f.get("time_signature"),
                "acousticness": f.get("acousticness"),
                "instrumentalness": f.get("instrumentalness"),
                "liveness": f.get("liveness"),
                "speechiness": f.get("speechiness"),
                "valence": f.get("valence"),
            }

    rows = []
    for alb, t in album_tracks:
        trk = track_meta.get(t["id"], {})
        feat = features.get(t["id"], {})
        rows.append({
            "artist_id": alb["artists"][0]["id"] if alb.get("artists") else None,
            "artist_name": alb["artists"][0]["name"] if alb.get("artists") else None,
            "album_id": alb["id"],
            "album_name": alb["name"],
            "album_upc": album_meta.get(alb["id"], {}).get("upc"),
            "album_release_date": album_meta.get(alb["id"], {}).get("release_date"),
            "album_release_date_precision": album_meta.get(alb["id"], {}).get("release_date_precision"),
            "album_label": album_meta.get(alb["id"], {}).get("label"),
            "album_type": album_meta.get(alb["id"], {}).get("album_type"),
            "track_id": t.get("id"),
            "track_name": t.get("name"),
            "disc_number": t.get("disc_number"),
            "track_number": t.get("track_number"),
            "duration_ms": trk.get("duration_ms"),
            "explicit": trk.get("explicit"),
            "isrc": trk.get("isrc"),
            "track_popularity": trk.get("popularity"),
            "spotify_url": trk.get("spotify_url"),
            "audio_features": feat,
            "market": market,
        })
    return rows
