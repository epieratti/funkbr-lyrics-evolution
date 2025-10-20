#!/usr/bin/env python3
import argparse, json, time, os, random, pathlib

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--limit", type=int, default=200)
    args = ap.parse_args()

    seeds = [s.strip() for s in open(args.seeds, encoding="utf-8") if s.strip()]
    ts = int(time.time())
    os.makedirs(pathlib.Path(args.out).parent, exist_ok=True)

    rnd = random.Random(42)
    wrote = 0
    with open(args.out, "w", encoding="utf-8") as fo:
        for artist in seeds:
            if wrote >= args.limit: break
            # linhas sintéticas no “formato parecido” com processed/ingest
            rec = {
                "artist_query": artist,
                "artist_name": artist,
                "album_id": f"mock_{wrote:06d}",
                "album_upc": f"000000{wrote:06d}",
                "track_id": f"mock_t_{wrote:06d}",
                "isrc": f"MOCK{wrote:06d}",
                "track_name": f"{artist} - Mock Track {wrote}",
                "market": "BR",
                "ts": ts,
                "country_score": 0,
                "isrc_score": 0,
                "pt_hint": 1,
                "seed_match": 1,
                "accept_in_brcorpus": 1,
                "pt_strict": 1,
                "es_strict": 0
            }
            fo.write(json.dumps(rec, ensure_ascii=False) + "\n")
            wrote += 1
    print(f"[mock] wrote={wrote} → {args.out}")
if __name__ == "__main__":
    main()
