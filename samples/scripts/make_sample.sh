#!/usr/bin/env bash
set -euo pipefail

mkdir -p samples/{metadata,logs}

# Fonte preferencial: JSONL do dia em processed_brcorpus/
# Fallback: qualquer brcorpus_*.jsonl disponível.
FULL_SRC="$(ls -1 processed_brcorpus/brcorpus_*.jsonl 2>/dev/null | sort | tail -n1 || true)"
PT_SRC="$(ls -1 processed_brcorpus/brcorpus_*_pt.jsonl 2>/dev/null | sort | tail -n1 || true)"

if [[ -n "${FULL_SRC}" ]]; then
  head -n 200 "$FULL_SRC" | jq -c 'del(.artist_id, .album_id, .track_id, .isrc, .album_upc, .album_upc_str, .ts, .ingestion_ts, .country_score, .isrc_score) | .pt_strict? as $x | del(.pt_strict,.es_strict)' \
    > samples/metadata/brcorpus_sample.jsonl || true
fi

if [[ -n "${PT_SRC}" ]]; then
  head -n 200 "$PT_SRC" | jq -c 'del(.artist_id, .album_id, .track_id, .isrc, .album_upc, .album_upc_str, .ts, .ingestion_ts, .country_score, .isrc_score) | .pt_strict? as $x | del(.pt_strict,.es_strict)' \
    > samples/metadata/brcorpus_pt_sample.jsonl || true
fi

# Logs — preferir health do dia; caso ausente, gera um log sintético.
if ls -1 logs/health_*.log >/dev/null 2>&1; then
  HL="$(ls -1 logs/health_*.log | sort | tail -n1)"
  tail -n 100 "$HL" | sed -E 's#/root/funkbr-lyrics-evolution#REDACTED_PROJECT_DIR#g' \
    > samples/logs/health_example.log
else
  cat > samples/logs/health_example.log <<'EOT'
2025-01-01 06:50:00 HEALTH START
- collector: OK
- process:   OK
- backup:    OK (dry-run)
- drive:     OK (dry-run)
- disk:      9% used
HEALTH OK
EOT
fi

echo "Samples geradas em samples/{metadata,logs}"
