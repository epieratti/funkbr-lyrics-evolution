#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Coletor Spotify (sem endpoints de áudio) — pega:
- Artista: followers, popularity, genres
- Álbum: label, release_date, release_date_precision, album_type, total_tracks, UPC
- Faixa: duration_ms, explicit, track_number, disc_number, popularity, preview_url,
         available_markets, available_in_BR, n_markets, ISRC
Escrita atômica em JSONL (evita 0 bytes).
"""
import os, sys, time, json, argparse, tempfile, requests
from typing import Dict, List, Any, Iterable

# [patched] flexible dispatcher for collect_for_artist
def _call_collect_for_artist(artist_query, **base):
    import inspect
    try:
        sig = inspect.signature(collect_for_artist)
    except Exception:
        # se não conseguir inspecionar, cai no melhor esforço posicional
        try:
            return collect_for_artist(artist_query)
        except TypeError:
            raise

    # mapear nome do artista para um parâmetro aceito
    name_keys = ("artist_query", "artist", "query", "name", "artist_name")
    kwargs = {}
    for k in name_keys:
        if k in sig.parameters:
            kwargs[k] = artist_query
            break
    else:
        # sem parâmetro nomeado: tenta posição
        try:
            return collect_for_artist(artist_query)
        except TypeError:
            # se nem posicional serve, propaga erro
            raise

    # incluir só kwargs suportados (ex.: H, out, snapshot etc.)
    for k, v in base.items():
        if k in sig.parameters:
            kwargs[k] = v

    return collect_for_artist(**kwargs)

# ---------- utils ----------
def load_env_file():
    p = os.path.join(os.getcwd(), ".env")
    if os.path.isfile(p):
        try:
            with open(p, encoding="utf-8") as f:
                for line in f:
                    line=line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    k,v=line.split("=",1)
                    k=k.strip()
                    v=v.strip().strip('"').strip("'")
                    v=os.path.expandvars(v)
                    os.environ.setdefault(k, v)
        except Exception:
            pass
def chunked(seq: Iterable[Any], n: int) -> Iterable[List[Any]]:
    buf=[]
    for x in seq:
        buf.append(x)
        if len(buf)>=n:
            yield buf
            buf=[]
    if buf:
        yield buf
def atomic_append_jsonl(path: str, obj: Dict[str, Any]) -> None:
    d = os.path.dirname(path) or "."
    os.makedirs(d, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".tmp_jsonl_", dir=d)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")
    with open(path, "ab") as out, open(tmp, "rb") as src:
        out.write(src.read())
    os.remove(tmp)
def GET(headers: Dict[str,str], url: str, **params) -> Dict[str, Any]:
    r = requests.get(url, headers=headers, params=params, timeout=30)
    r.raise_for_status()
    return r.json()
# ---------- coleta ----------
def collect_for_artist(h, q: str, market: str, out_path: str):
    # 1) /search -> artista
    sr = GET(h, "https://api.spotify.com/v1/search",
             q=q, type="artist", limit=1, market=market)
    items = sr.get("artists", {}).get("items", [])
    if not items:
        atomic_append_jsonl(out_path, {"artist_query": q, "warning": "artist_not_found",
                                       "market": market, "ts": int(time.time()), "_type": "warn"})
        return 0
    ad = GET(h, f"https://api.spotify.com/v1/artists/{items[0]['id']}")
    aid = ad.get("id")
    artist_row = {
        "_type": "artist_meta",
        "artist_query": q,
        "artist_id": aid,
        "artist_name": ad.get("name"),
        "followers": (ad.get("followers") or {}).get("total"),
        "popularity": ad.get("popularity"),
        "genres": ",".join(ad.get("genres") or []),
        "market": market,
        "ts": int(time.time()),
        "year_start": 2005,
        "year_end": 2025,
    }
    atomic_append_jsonl(out_path, artist_row)
    # 2) /artists/{id}/albums (pagina)
    albums = []
    url = f"https://api.spotify.com/v1/artists/{aid}/albums"
    params = {"include_groups": "album,single,appears_on,compilation",
              "market": market, "limit": 50}
    while True:
        r = GET(h, url, **params)
        albums += r.get("items", [])
        url = r.get("next") or None
        if not url:
            break
    # 3) /v1/albums?ids=… (UPC/label/release_date/album_type/total_tracks)
    album_meta = {}
    for batch in chunked([a["id"] for a in albums], 20):
        det = GET(h, "https://api.spotify.com/v1/albums", ids=",".join(batch))
        for a in det.get("albums", []) or []:
            ext = a.get("external_ids") or {}
            album_meta[a["id"]] = {
                "upc": ext.get("upc"),
                "label": a.get("label"),
                "release_date": a.get("release_date"),
                "release_date_precision": a.get("release_date_precision"),
                "album_type": a.get("album_type"),
                "total_tracks": a.get("total_tracks"),
            }
    # 4) /albums/{id}/tracks + /v1/tracks?ids=… (ISRC e campos de faixa)
    tids = []
    for alb in albums:
        tr = GET(h, f"https://api.spotify.com/v1/albums/{alb['id']}/tracks",
                 market=market, limit=50)
        for t in tr.get("items", []) or []:
            tids.append((alb["id"], t["id"]))
    rows = 0
    for batch in chunked([tid for _,tid in tids], 50):
        det = GET(h, "https://api.spotify.com/v1/tracks", ids=",".join(batch))
        for t in det.get("tracks", []) or []:
            alb_id = t["album"]["id"]
            markets = t.get("available_markets") or []
            row = {
                "_type": "track_row",
                "artist_id": aid,
                "artist_query": q,
                "album_id": alb_id,
                "album_upc": album_meta.get(alb_id, {}).get("upc"),
                "album_label": album_meta.get(alb_id, {}).get("label"),
                "album_release_date": album_meta.get(alb_id, {}).get("release_date"),
                "album_release_date_precision": album_meta.get(alb_id, {}).get("release_date_precision"),
                "album_type": album_meta.get(alb_id, {}).get("album_type"),
                "album_total_tracks": album_meta.get(alb_id, {}).get("total_tracks"),
                "track_id": t["id"],
                "track_name": t.get("name"),
                "duration_ms": t.get("duration_ms"),
                "explicit": t.get("explicit"),
                "track_number": t.get("track_number"),
                "disc_number": t.get("disc_number"),
                "track_popularity": t.get("popularity"),
                "preview_url": t.get("preview_url"),
                "available_in_BR": ("BR" in markets),
                "n_markets": len(markets),
                "available_markets": markets,
                "isrc": (t.get("external_ids") or {}).get("isrc"),
                "market": market,
                "ts": int(time.time()),
            }
            atomic_append_jsonl(out_path, row)
            rows += 1
    return rows
def main():
    load_env_file()
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit_artists", type=int, default=5)
    ap.add_argument("--snapshot", required=True)
    ap.add_argument("--seed", default="data/seed/seed_artists.txt")
    args = ap.parse_args()
    market = os.getenv("MARKET", "BR")
    out_path = os.getenv("OUTPUT_JSONL",
                         os.path.join("data", "raw", f"funk_br_discografia_raw_{args.snapshot}.jsonl"))
    cid = os.getenv("SPOTIFY_CLIENT_ID") or os.getenv("SPOTIPY_CLIENT_ID")
    sec = os.getenv("SPOTIFY_CLIENT_SECRET") or os.getenv("SPOTIPY_CLIENT_SECRET")
    if not cid or not sec:
        print("❌ Falta SPOTIFY_CLIENT_ID/SECRET no ambiente (.env).", file=sys.stderr)
        sys.exit(2)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    print(f"[init] MARKET={market} | OUT={out_path}")
    tok = requests.post(
        "https://accounts.spotify.com/api/token",
        auth=(cid,sec), data={"grant_type":"client_credentials"}, timeout=30
    ).json().get("access_token")
    if not tok:
        print("❌ Não consegui token client_credentials", file=sys.stderr)
        sys.exit(3)
    H = {"Authorization": f"Bearer {tok}"}


# def GET(u, **q):
    """GET com retry/backoff:
    - 429 → respeita Retry-After (segundos)
    - 5xx → backoff exponencial + jitter
    - Pausa entre chamadas: SPOTIFY_REQ_SLEEP (default 0.35s)
    """
    import time, os, requests, random
    backoff = 1.0
    while True:
        r = requests.get(u, params=q, headers=H, timeout=30)
        if r.status_code == 429:
            ra = r.headers.get("Retry-After")
            try: wait = int(ra) if ra is not None else backoff
            except: wait = backoff
            wait = max(1, min(wait, 3600))
            print(f"[rate-limit] 429; aguardando {wait}s …", flush=True)
            time.sleep(wait)
            backoff = min(backoff*2, 600)
            continue
        if 500 <= r.status_code < 600:
            jitter = random.uniform(0,0.5)
            wait = min(backoff + jitter, 60)
            print(f"[retry] {r.status_code}; backoff {wait:.1f}s …", flush=True)
            time.sleep(wait); backoff = min(backoff*2, 60); continue
        r.raise_for_status()
        try: pause = float(os.getenv("SPOTIFY_REQ_SLEEP","0.35"))
        except: pause = 0.35
        if pause>0: time.sleep(pause)
        return r.json()


    print("[auth] client_credentials OK")
    artists=[]
    with open(args.seed, encoding="utf-8") as f:
        for line in f:
            line=line.strip()
            if line and not line.startswith("#"):
                artists.append(line)
    artists = artists[:args.limit_artists]
    t0=time.time()
    total_rows=0
    for i,q in enumerate(artists,1):
        try:
            rows = collect_for_artist(H, q, market, out_path)
            total_rows += rows
            print(f"[{i}/{len(artists)}] {q}: rows={rows}")
        except Exception as e:
            print(f"[{i}/{len(artists)}] {q}: ERRO -> {e}", file=sys.stderr)
    dt=time.time()-t0
    print(f"[done] artistas={len(artists)} | linhas={total_rows} | tempo={dt:.1f}s")
    print(f"[ok] wrote -> {out_path}")
# [patched] __main__ substituído para usar cli_main()
# [patched] (desabilitado guard __main__ original) if __name__ == "__main__":
# [patched] removed stray top-level cli_main() call
# [patched] removed stray top-level cli_main() call

# === injected runner (idempotente) ============================================
def cli_main():
    """
    Runner estável:
      - lê seeds de 'seed/seeds_raw.txt' (1 por linha; ignora vazias/#)
      - cria diretórios de saída se necessário
      - para cada seed, chama 'collect_for_artist' (função já existente no script)
    Requisitos:
      - função _call__call_collect_for_artist(artist_query, out_writer, snapshot_tag, log) deve existir no arquivo
    """
    import os, sys, json, time

    # Flags simples: --snapshot <TAG> (opcional)
    snapshot = None
    argv = sys.argv[1:]
    if '--snapshot' in argv:
        i = argv.index('--snapshot')
        if i+1 < len(argv): snapshot = argv[i+1]

    if not snapshot:
        snapshot = time.strftime("NOW_%Y%m%d_%H%M")

    repo_top = os.path.abspath(os.path.dirname(__file__) + "/..")
    seeds_file = os.path.join(repo_top, "seed", "seeds_raw.txt")
    out_dir = os.path.join(repo_top, "data", "raw")
    os.makedirs(out_dir, exist_ok=True)

    out_path = os.path.join(out_dir, f"funk_br_discografia_raw_{snapshot}.jsonl")
    print(f"[cli_main] seeds: {seeds_file}")
    print(f"[cli_main] out:   {out_path}")

    # Leitura de seeds
    if not os.path.exists(seeds_file):
        print(f"[cli_main] AVISO: arquivo de seeds não encontrado: {seeds_file}", file=sys.stderr)
        print("[cli_main] nada a fazer.")
        return

    with open(seeds_file, "r", encoding="utf-8") as fh:
        seeds = [ln.strip() for ln in fh if ln.strip() and not ln.strip().startswith("#")]

    if not seeds:
        print("[cli_main] AVISO: nenhum seed válido encontrado.")
        return

    # verifica existência da função collect_for_artist no módulo atual
    try:
        fn = globals().get("collect_for_artist", None)
        if not callable(fn):
            print("[cli_main] ERRO: função collect_for_artist não encontrada no script.", file=sys.stderr)
            sys.exit(2)
    except Exception as e:
        print(f"[cli_main] ERRO ao acessar collect_for_artist: {e}", file=sys.stderr)
        sys.exit(2)

    # abre writer de saída
    count = 0
    with open(out_path, "w", encoding="utf-8") as w:
        for seed in seeds:
            try:
                fn(artist_query=seed, out_writer=w, snapshot_tag=snapshot, log=print)
                count += 1
            except Exception as e:
                print(f"[cli_main] ERRO seed='{seed}': {e}", file=sys.stderr)
                continue

    print(f"[cli_main] finalizado. seeds_ok={count}, arquivo={out_path}")
# === end injected runner ======================================================

# [patched-tail] Guard padronizado

# [patched] canonical __main__ guard
if __name__ == "__main__":
    cli_main()
