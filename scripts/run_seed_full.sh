#!/usr/bin/env bash
set -eo pipefail
[ "${TRACE:-0}" = "1" ] && set -x

SEED="${1:-}"
if [[ -z "$SEED" || ! -f "$SEED" ]]; then
  echo "Usage: $0 data/seed/seed_part_X.txt"; exit 1
fi

echo "Seed: $SEED"
echo "Window: ${YEAR_START:-2005}-${YEAR_END:-2025} | MARKET=${MARKET:-BR}"

# Normalize CRLF -> LF and drop empty lines
tmp_seed="$(mktemp)"
sed 's/\r$//' "$SEED" | grep -v '^[[:space:]]*$' > "$tmp_seed"
mapfile -t LINES < "$tmp_seed"
rm -f "$tmp_seed"

echo "Artists in seed: ${#LINES[@]}"
mkdir -p data/raw logs

i=0
for NAME in "${LINES[@]}"; do
  ((++i))
  echo
  echo "[$i] Collecting: $NAME"

  TS="$(date +%Y%m%d_%H%M%S)"
  SAFE="$(printf '%s' "$NAME" | sed -E 's/[^A-Za-z0-9._-]+/_/g')"
  OUTJ="data/raw/one_${TS}_${SAFE}_albums_tracks.jsonl"
  OUTC="data/raw/one_${TS}_${SAFE}_albums_tracks.csv"
  LOGF="logs/collect_${TS}_${SAFE}.log"

  # Collect (albums + tracks)
  PYTHONUNBUFFERED=1 \
  OUTPUT_JSONL="$OUTJ" \
  OUTPUT_CSV="$OUTC" \
  LOG_FILE="$LOGF" \
  ARTIST_NAME="$NAME" \
  YEAR_START="${YEAR_START:-2005}" \
  YEAR_END="${YEAR_END:-2025}" \
  MARKET="${MARKET:-BR}" \
  FLUSH_EVERY_N_ROWS="${FLUSH_EVERY_N_ROWS:-50}" \
  python code/run_one_artist_full.py | tee -a "$LOGF"

  # Enrich if Spotify client credentials are present
  if [[ -n "${SPOTIFY_CLIENT_ID:-}" && -n "${SPOTIFY_CLIENT_SECRET:-}" ]]; then
    echo "Enriching..." | tee -a "$LOGF"
    python code/enrich_latest.py | tee -a "$LOGF"
  else
    echo "Skipping enrich (SPOTIFY_CLIENT_ID/SECRET missing)" | tee -a "$LOGF"
  fi

  echo "Deduplicating..." | tee -a "$LOGF"
  python code/dedupe_albums_tracks.py | tee -a "$LOGF"
done

echo
echo "Done: $SEED"
echo "Latest dedup files:"
ls -1t data/raw/*_dedup.csv | head || true
