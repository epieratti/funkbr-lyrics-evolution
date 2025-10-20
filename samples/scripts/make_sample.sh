#!/usr/bin/env bash
set -euo pipefail
TOP="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
out_meta="$TOP/samples/metadata"
out_logs="$TOP/samples/logs"
mkdir -p "$out_meta" "$out_logs"

# 1) Mini metadata do corpus (se existir), limit 200 linhas
for f in "$TOP"/processed_brcorpus/brcorpus_*.jsonl; do
  [ -f "$f" ] || continue
  base="$(basename "$f")"
  head -n 200 "$f" > "$out_meta/${base%.jsonl}.sample.jsonl"
done

# 2) Mini logs: só linhas não vazias e primeiras 200
for f in "$TOP"/logs/*.log; do
  [ -f "$f" ] || continue
  base="$(basename "$f")"
  awk 'NF>0' "$f" | head -n 200 > "$out_logs/${base%.log}.sample.log"
done

echo "Samples geradas em samples/{metadata,logs}"
