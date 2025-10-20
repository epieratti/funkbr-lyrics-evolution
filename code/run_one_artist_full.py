import os, sys, csv, json, time, base64, logging, unicodedata, re
from typing import List, Dict, Any
from urllib import request, parse
from dotenv import load_dotenv
from rapidfuzz import fuzz

# ---------- Config/env ----------
load_dotenv()
ARTIST_NAME    = os.getenv("ARTIST_NAME") or ""
YEAR_START     = int(os.getenv("YEAR_START","2005"))
YEAR_END       = int(os.getenv("YEAR_END","2025"))
MARKET         = os.getenv("MARKET","BR")
OUT_JSONL      = os.getenv("OUTPUT_JSONL", "data/raw/one_artist_albums_tracks.jsonl")
OUT_CSV        = os.getenv("OUTPUT_CSV",   "data/raw/one_artist_albums_tracks.csv")
LOG_FILE       = os.getenv("LOG_FILE",     "logs/one_artist_albums_tracks.log")
FLUSH_EVERY    = int(os.getenv("FLUSH_EVERY_N_ROWS","100"))

SPOTIFY_CLIENT_ID     = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")

os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
os.makedirs(os.path.dirname(OUT_JSONL), exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler(LOG_FILE, encoding="utf-8"), logging.StreamHandler(sys.stdout)]
)

# ---------- Helpers ----------
def _norm(x:str)->str:
    x = unicodedata.normalize("NFKD", x or "")
    x = "".join(ch for ch in x if not unicodedata.combining(ch))
    x = re.sub(r"[^a-z0-9 ]+", "", x.lower())
    return re.sub(r"\s+", " ", x).strip()

def _token() -> str:
    if not SPOTIFY_CLIENT_ID or not SPOTIFY_CLIENT_SECRET:
        raise RuntimeError("SPOTIFY_CLIENT_ID/SECRET ausentes no .env")
    basic = base64.b64encode(f"{SPOTIFY_CLIENT_ID}:{SPOTIFY_CLIENT_SECRET}".encode()).decode()
    data = parse.urlencode({"grant_type":"client_credentials"}).encode()
    req = request.Request("https://accounts.spotify.com/api/token", data=data, headers={"Authorization":f"Basic {basic}"})
    with request.urlopen(req) as r:
        payload = json.load(r)
    tok = payload.get("access_token")
    if not tok: raise RuntimeError("Falha ao obter token Spotify")
    return tok

def _http_json(url: str, headers: Dict[str,str]) -> Dict[str,Any]:
    req = request.Request(url, headers=headers)
    with request.urlopen(req) as r:
        return json.load(r)

def _search_artist(token: str, q: str) -> Dict[str,Any]:
    q_enc = parse.quote(f'artist:"{q}"')
    url = f"https://api.spotify.com/v1/search?q={q_enc}&type=artist&limit=50"
    data = _http_json(url, {"Authorization": f"Bearer {token}"})
    items = data.get("artists",{}).get("items",[]) or []
    if not items: return {}
    qn = _norm(q)
    ranked = []
    for it in items:
        score = fuzz.ratio(_norm(it.get("name","")), qn)
        ranked.append((score, it.get("popularity") or -1, (it.get("followers") or {}).get("total") or -1, it))
    ranked.sort(key=lambda t: (t[0], t[1], t[2]), reverse=True)
    best = ranked[0][3]
    for t in ranked:
        if t[0] == 100:
            best = t[3]; break
    return best

def _iter_artist_albums(token: str, artist_id: str):
    # include_groups: álbuns próprios e singles; compilações opcional
    include_groups = "album,single,compilation"
    limit = 50
    offset = 0
    headers = {"Authorization": f"Bearer {token}"}
    while True:
        url = f"https://api.spotify.com/v1/artists/{artist_id}/albums?include_groups={include_groups}&limit={limit}&offset={offset}"
        data = _http_json(url, headers)
        items = data.get("items",[]) or []
        for it in items:
            yield it
        if len(items) < limit:
            break
        offset += limit
        time.sleep(0.1)

def _album_year(album: Dict[str,Any]) -> int:
    rd = (album.get("release_date") or "")[:10]
    try:
        return int(rd.split("-")[0])
    except Exception:
        return -1

def _iter_album_tracks(token: str, album_id: str):
    limit=50; offset=0
    headers={"Authorization": f"Bearer {token}"}
    while True:
        url = f"https://api.spotify.com/v1/albums/{album_id}/tracks?limit={limit}&offset={offset}"
        data = _http_json(url, headers)
        items = data.get("items",[]) or []
        for it in items:
            yield it
        if len(items) < limit:
            break
        offset += limit
        time.sleep(0.1)

def _batch_get_tracks(token: str, ids: List[str]) -> Dict[str,Dict[str,Any]]:
    # opcional: enriquecer com ISRC e popularity por track
    out={}
    headers={"Authorization": f"Bearer {token}"}
    for i in range(0, len(ids), 50):
        chunk = ids[i:i+50]
        url = "https://api.spotify.com/v1/tracks?ids=" + ",".join(chunk)
        data = _http_json(url, headers)
        for tr in data.get("tracks",[]) or []:
            if tr: out[tr["id"]] = tr
        time.sleep(0.1)
    return out

def main() -> int:
    if not ARTIST_NAME.strip():
        logging.error("Defina ARTIST_NAME no ambiente.")
        return 2

    logging.info(f"Coleta 1 artista — '{ARTIST_NAME}' | {YEAR_START}-{YEAR_END}")
    token = _token()

    art = _search_artist(token, ARTIST_NAME)
    if not art:
        logging.error(f"Artista não encontrado: {ARTIST_NAME}")
        return 3

    artist_id = art.get("id")
    artist_name = art.get("name")
    logging.info(f"Match: {artist_name} ({artist_id}) | followers={ (art.get('followers') or {}).get('total') } pop={ art.get('popularity') }")

    is_new_csv = not os.path.exists(OUT_CSV)
    fcsv = open(OUT_CSV, "a", newline="", encoding="utf-8")
    wcsv = csv.DictWriter(fcsv, fieldnames=[
        "artist_id","artist_name",
        "album_id","album_name","album_release_date","album_release_precision","album_total_tracks","album_type",
        "track_id","track_name","track_number","disc_number","duration_ms","explicit",
        "year_window_start","year_window_end","market","ingestion_ts"
    ])
    if is_new_csv:
        wcsv.writeheader()
    fjson = open(OUT_JSONL, "a", encoding="utf-8")

    total_rows = 0
    track_ids_for_enrich = []
    rows_buffer = []

    for alb in _iter_artist_albums(token, artist_id):
        y = _album_year(alb)
        if y < YEAR_START or y > YEAR_END:
            continue
        album_id = alb.get("id"); album_name = alb.get("name")
        album_release_date = alb.get("release_date")
        album_release_precision = alb.get("release_date_precision")
        album_total_tracks = alb.get("total_tracks")
        album_type = alb.get("album_type")

        for tr in _iter_album_tracks(token, album_id):
            row = {
                "artist_id": artist_id,
                "artist_name": artist_name,
                "album_id": album_id,
                "album_name": album_name,
                "album_release_date": album_release_date,
                "album_release_precision": album_release_precision,
                "album_total_tracks": album_total_tracks,
                "album_type": album_type,
                "track_id": tr.get("id"),
                "track_name": tr.get("name"),
                "track_number": tr.get("track_number"),
                "disc_number": tr.get("disc_number"),
                "duration_ms": tr.get("duration_ms"),
                "explicit": tr.get("explicit"),
                "year_window_start": YEAR_START,
                "year_window_end": YEAR_END,
                "market": MARKET,
                "ingestion_ts": int(time.time())
            }
            rows_buffer.append(row)
            if row["track_id"]:
                track_ids_for_enrich.append(row["track_id"])

            if len(rows_buffer) >= FLUSH_EVERY:
                for r in rows_buffer:
                    fjson.write(json.dumps(r, ensure_ascii=False) + "\n")
                    wcsv.writerow(r)
                fcsv.flush(); fjson.flush()
                total_rows += len(rows_buffer)
                logging.info(f"flush {total_rows} linhas")
                rows_buffer.clear()

        time.sleep(0.2)  # leve respiro entre álbuns

    # flush final
    for r in rows_buffer:
        fjson.write(json.dumps(r, ensure_ascii=False) + "\n")
        wcsv.writerow(r)
    total_rows += len(rows_buffer)
    fcsv.flush(); fjson.flush(); fcsv.close(); fjson.close()

    logging.info(f"Coleta concluída | linhas={total_rows} | artista={artist_name} ({artist_id})")
    return 0

if __name__ == "__main__":
    sys.exit(main())
