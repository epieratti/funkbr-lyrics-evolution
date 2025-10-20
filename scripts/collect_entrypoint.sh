#!/usr/bin/env bash
set -euo pipefail
TOP="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
set -a; source "$TOP/.env"; set +a

SNAPSHOT="${SNAPSHOT:-NOW}"
SEEDS="${SEEDS:-$TOP/seed/seeds_raw.txt}"
OUT="$TOP/data/raw/funk_br_discografia_raw_${SNAPSHOT}.jsonl"

mkdir -p "$TOP/data/raw" "$TOP/logs"

if [ "${COLLECT_MODE:-disabled}" = "disabled" ]; then
  echo "[collect] BLOCKED MODE: gerando mock a partir dos seeds → $OUT"
  python "$TOP/scripts/diag/mock_spotify_collect.py" \
    --seeds "$SEEDS" --out "$OUT" --limit 200 \
    >> "$TOP/logs/collect_$(date +%F).log" 2>&1
  exit 0
fi

echo "[collect] REAL MODE: rodando coletor real → $OUT"
python "$TOP/scripts/diag/run_collect_min.py" \
  >> "$TOP/logs/collect_$(date +%F).log" 2>&1
