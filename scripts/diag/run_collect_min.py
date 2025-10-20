#!/usr/bin/env python3
import os, sys, pathlib, importlib.util

REPO = pathlib.Path(__file__).resolve().parents[2]
MOD  = REPO / "code" / "collect_spotify_catalog.py"

spec = importlib.util.spec_from_file_location("collector_mod", str(MOD))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

token = os.environ.get("SPOTIFY_TOKEN")
if not token:
    print("[runner] ERRO: defina SPOTIFY_TOKEN no ambiente (Bearer <token>)", file=sys.stderr)
    sys.exit(2)

H = {"Authorization": f"Bearer {token}"}

# args simples
snapshot   = os.environ.get("SNAPSHOT", "NOW_TEST")
seeds_file = os.environ.get("SEEDS", str(REPO / "seed" / "seeds_raw.txt"))
out_path   = str(REPO / "data" / "raw" / f"funk_br_discografia_raw_{snapshot}.jsonl")

print(f"[runner] seeds: {seeds_file}")
print(f"[runner] out:   {out_path}")

with open(seeds_file, "r", encoding="utf-8") as fh:
    seeds = [ln.strip() for ln in fh if ln.strip()]

ok = 0
for q in seeds:
    try:
        m.collect_for_artist(H, q, "BR", out_path)
        ok += 1
    except Exception as e:
        print(f"[runner] AVISO: seed={q!r} falhou: {e}", file=sys.stderr)

print(f"[runner] finalizado. seeds_ok={ok}, arquivo={out_path}")
