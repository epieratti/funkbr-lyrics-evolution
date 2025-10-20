import os, sys, csv, json, time, base64, logging
from typing import List, Dict, Any
from urllib import request, parse
from dotenv import load_dotenv
from rapidfuzz import fuzz
import unicodedata, re

# ---------- Config ----------
load_dotenv()
SEED_FILE      = os.getenv("SEED_FILE", "data/seed/seed_artists.txt")
OUTPUT_JSONL   = os.getenv("OUTPUT_JSONL", "data/raw/funk_br_discografia_raw.jsonl")
OUTPUT_CSV     = os.getenv("OUTPUT_CSV", "data/raw/funk_br_discografia_2005_2025.csv")
LOG_FILE       = os.getenv("LOG_FILE", "logs/collector.log")
PROGRESS_FILE  = os.getenv("PROGRESS_FILE", "data/raw/progress.json")
YEAR_START     = int(os.getenv("YEAR_START","2005"))
YEAR_END       = int(os.getenv("YEAR_END","2025"))
MARKET         = os.getenv("MARKET","BR")
FLUSH_EVERY    = int(os.getenv("FLUSH_EVERY_N_ROWS","200"))

SPOTIFY_CLIENT_ID     = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")

os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
os.makedirs(os.path.dirname(OUTPUT_JSONL), exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler(LOG_FILE, encoding="utf-8"), logging.StreamHandler(sys.stdout)]
)

def _spotify_token() -> str:
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

def _read_seed(path: str) -> List[str]:
    with open(path, "r", encoding="utf-8") as f:
        return [ln.strip() for ln in f if ln.strip()]

def _norm(x:str)->str:
    x = unicodedata.normalize("NFKD", x or "")
    x = "".join(ch for ch in x if not unicodedata.combining(ch))
    x = re.sub(r"[^a-z0-9 ]+", "", x.lower())
    return re.sub(r"\s+", " ", x).strip()

def _search_artist(token: str, q: str) -> Dict[str,Any]:
    """
    Busca artista no Spotify e escolhe o melhor match pelo nome usando rapidfuzz.
    1) Query restrita: artist:"<q>" (limit=50, sem market)
    2) Rank por fuzz.ratio(nome_normalizado, q_normalizado)
    3) Se houver score 100, escolhe esse; senão, maior score.
       Empate: popularity -> followers.
    """
    q_orig = (q or "").strip()
    q_norm = _norm(q_orig)
    if not q_norm:
        return {}

    # 1) tentar com query restrita, sem market
    q_enc = parse.quote(f'artist:"{q_orig}"')
    url = f"https://api.spotify.com/v1/search?q={q_enc}&type=artist&limit=50"
    req = request.Request(url, headers={"Authorization": f"Bearer {token}"})
    try:
        with request.urlopen(req) as r:
            data = json.load(r)
        items = data.get("artists",{}).get("items",[]) or []
    except Exception as e:
        logging.warning(f"search_artist erro para '{q_orig}': {e}")
        items = []

    if not items:
        return {}

    ranked = []
    for it in items:
        name = it.get("name","")
        score = fuzz.ratio(_norm(name), q_norm)
        ranked.append((
            score,
            it.get("popularity") or -1,
            (it.get("followers") or {}).get("total") or -1,
            it
        ))
    ranked.sort(key=lambda t: (t[0], t[1], t[2]), reverse=True)

    best = ranked[0][3]
    # se houver algum com score 100, prioriza
    for tup in ranked:
        if tup[0] == 100:
            best = tup[3]
            break
    return best

def main():
    logging.info(f"Pilot runner iniciado | SEED={SEED_FILE} | OUT_JSONL={OUTPUT_JSONL} | OUT_CSV={OUTPUT_CSV} | {YEAR_START}-{YEAR_END} | MARKET={MARKET}")
    token = _spotify_token()
    seed = _read_seed(SEED_FILE)
    logging.info(f"{len(seed)} artistas no seed")

    is_new_csv = not os.path.exists(OUTPUT_CSV)
    csv_f = open(OUTPUT_CSV, "a", newline="", encoding="utf-8")
    csv_w = csv.DictWriter(csv_f, fieldnames=[
        "artist_query","artist_id","artist_name","followers","popularity","genres","year_start","year_end","market","ts"
    ])
    if is_new_csv:
        csv_w.writeheader()

    json_f = open(OUTPUT_JSONL, "a", encoding="utf-8")

    processed = 0
    for artist_q in seed:
        art = _search_artist(token, artist_q)
        row = {
            "artist_query": artist_q,
            "artist_id": art.get("id") or "",
            "artist_name": art.get("name") or "",
            "followers": (art.get("followers") or {}).get("total"),
            "popularity": art.get("popularity"),
            "genres": ",".join(art.get("genres",[])),
            "year_start": YEAR_START,
            "year_end": YEAR_END,
            "market": MARKET,
            "ts": int(time.time())
        }
        json_f.write(json.dumps(row, ensure_ascii=False) + "\n")
        csv_w.writerow(row)

        processed += 1
        if processed % FLUSH_EVERY == 0:
            csv_f.flush(); json_f.flush()
            logging.info(f"flush {processed} linhas")

    csv_f.flush(); json_f.flush()
    csv_f.close(); json_f.close()

    with open(PROGRESS_FILE,"w",encoding="utf-8") as pf:
        json.dump({"processed": processed, "seed": SEED_FILE, "market": MARKET, "window":[YEAR_START, YEAR_END]}, pf, ensure_ascii=False)

    logging.info(f"Pilot runner finalizado | linhas={processed}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
