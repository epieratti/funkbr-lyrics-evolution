import os, glob, csv, json, time
from urllib import request, parse

def get_token():
    cid = os.getenv("SPOTIFY_CLIENT_ID"); sec = os.getenv("SPOTIFY_CLIENT_SECRET")
    if not cid or not sec:
        raise SystemExit("Falta SPOTIFY_CLIENT_ID/SECRET no ambiente")
    basic = (cid + ":" + sec).encode()
    basic = __import__("base64").b64encode(basic).decode()
    data = parse.urlencode({"grant_type":"client_credentials"}).encode()
    req = request.Request("https://accounts.spotify.com/api/token", data=data, headers={"Authorization":"Basic "+basic})
    return json.load(request.urlopen(req))["access_token"]

def batch_get_tracks(token, ids):
    out = {}
    H = {"Authorization":"Bearer "+token}
    for i in range(0, len(ids), 50):
        chunk = ids[i:i+50]
        url = "https://api.spotify.com/v1/tracks?ids=" + ",".join(chunk)
        with request.urlopen(request.Request(url, headers=H)) as r:
            data = json.load(r)
        for tr in data.get("tracks",[]) or []:
            if tr:
                out[tr["id"]] = {
                    "isrc": ((tr.get("external_ids") or {}).get("isrc")),
                    "pop": tr.get("popularity")
                }
        time.sleep(0.1)
    return out

def main():
    # pega o CSV "one_*_albums_tracks.csv" mais recente
    paths = sorted(glob.glob("data/raw/*_albums_tracks.csv"))
    if not paths:
        raise SystemExit("Nenhum CSV *_albums_tracks.csv encontrado em data/raw/")
    src = paths[-1]
    dst = src.replace(".csv", "_enriched.csv")
    print("Lendo:", src)

    rows = []
    with open(src, newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r: rows.append(row)

    ids = [r["track_id"] for r in rows if r.get("track_id")]
    print("Tracks para enriquecer:", len(ids))

    tok = get_token()
    det = batch_get_tracks(tok, ids)

    flds = list(rows[0].keys()) + ["track_isrc","track_popularity"]
    with open(dst, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=flds)
        w.writeheader()
        for r in rows:
            d = det.get(r.get("track_id") or "", {})
            r["track_isrc"] = d.get("isrc")
            r["track_popularity"] = d.get("pop")
            w.writerow(r)
    print("OK ->", dst)

if __name__ == "__main__":
    main()
