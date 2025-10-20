#!/usr/bin/env bash
set -euo pipefail
SNAP="${1:-$(date +%Y%m%d)}"
LIMIT="${LIMIT:-100}"
echo "[run] piloto LIMIT=$LIMIT snapshot=$SNAP"
python code/coletar_discografia_funk_br.py --limit_artists "$LIMIT" --snapshot "$SNAP"
echo "[run] dedup global em data/raw/*.jsonl"
python code/dedup_snapshot.py --path data/raw --pattern "*.jsonl" --scope global || \
python code/dedup_snapshot.py --path data/raw --pattern "*.jsonl"
echo "[run] ok"
