#!/usr/bin/env bash
set -euo pipefail
SNAP="${1:-$(date +%Y%m%d)}"
echo "[run] coletando snapshot=$SNAP"
python code/coletar_discografia_funk_br.py --snapshot "$SNAP"
echo "[run] dedup global em data/raw/*.jsonl"
python code/dedup_snapshot.py --path data/raw --pattern "*.jsonl" --scope global || \
python code/dedup_snapshot.py --path data/raw --pattern "*.jsonl"
echo "[run] ok"
