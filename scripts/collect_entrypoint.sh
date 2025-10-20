#!/usr/bin/env bash
set -euo pipefail
TOP="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

if [ -f "$TOP/.env" ]; then
  while IFS='=' read -r key value; do
    case "$key" in
      SPOTIFY_CLIENT_ID|SPOTIFY_CLIENT_SECRET|COLLECT_MODE)
        export "$key"="${value}";;
    esac
  done < <(grep -E '^(SPOTIFY_CLIENT_ID|SPOTIFY_CLIENT_SECRET|COLLECT_MODE)=' "$TOP/.env" || true)
fi

"$TOP/scripts/require_cmd.sh" python flock

SNAPSHOT="${SNAPSHOT:-NOW}"
SEEDS="${SEEDS:-$TOP/seed/seeds_raw.txt}"
OUT="$TOP/data/raw/funk_br_discografia_raw_${SNAPSHOT}.jsonl"

mkdir -p "$TOP/data/raw" "$TOP/logs" "$TOP/locks"

if [ "${COLLECT_MODE:-disabled}" = "disabled" ]; then
  echo "[collect] BLOCKED MODE: gerando mock a partir dos seeds → $OUT"
  python "$TOP/scripts/diag/mock_spotify_collect.py" \
    --seeds "$SEEDS" --out "$OUT" --limit 200 \
    >> "$TOP/logs/collect_$(date +%F).log" 2>&1
  exit 0
fi

echo "[collect] REAL MODE: rodando coletor real → $OUT"
"$TOP/scripts/with_lock.sh" "$TOP/locks/collect_entrypoint.lock" -- \
  python "$TOP/scripts/diag/run_collect_min.py" \
  >> "$TOP/logs/collect_$(date +%F).log" 2>&1
