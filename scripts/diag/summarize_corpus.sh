#!/usr/bin/env bash
set -euo pipefail
FULL="processed_brcorpus/brcorpus_$(date +%F).jsonl"
PT="processed_brcorpus/brcorpus_$(date +%F)_pt.jsonl"
[ -f "$FULL" ] && echo -n "full " && wc -l "$FULL" || echo "faltando $FULL"
[ -f "$PT" ]   && echo -n "pt   " && wc -l "$PT"   || echo "faltando $PT"
if [ -f "$FULL" ] && [ -f "$PT" ]; then
  diff <(sed 's/.*"track_id":"\([^"]*\)".*/\1/' "$FULL" | sort) <(sed 's/.*"track_id":"\([^"]*\)".*/\1/' "$PT" | sort) | head -n 50 || true
fi
