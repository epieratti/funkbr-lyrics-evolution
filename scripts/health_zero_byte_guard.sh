#!/usr/bin/env bash
set -euo pipefail
TZ="${TZ:-America/Sao_Paulo}"
export TZ

RAW_DIR="${1:-data/raw}"
# hora local a partir da qual 0 bytes vira WARNING (ex.: fim de process+sanity)
END_HOUR_LOCAL="${END_HOUR_LOCAL:-06}"

TODAY="$(date +%Y%m%d)"
SHOULD_WARN=0

shopt -s nullglob
found=0
for f in "$RAW_DIR"/*"${TODAY}"*.jsonl "$RAW_DIR"/"${TODAY}"*.jsonl; do
  found=1

  # stat portável (GNU vs BSD)
  if size=$(stat -c%s "$f" 2>/dev/null); then :; else size=$(stat -f%z "$f" 2>/dev/null || echo 0); fi

  hour_now="$(date +%H)"   # ex.: 09, 17 etc.
  # FORÇAR base 10: 10#$var evita octal
  if (( 10#$hour_now >= 10#$END_HOUR_LOCAL && size == 0 )); then
    echo "[WARNING] $f tem 0 bytes após ${END_HOUR_LOCAL}:00 local."
    SHOULD_WARN=1
  else
    echo "[INFO] $f size=${size} bytes (hora=${hour_now})"
  fi
done

if [[ $found -eq 0 ]]; then
  echo "[INFO] Nenhum snapshot de hoje encontrado em $RAW_DIR (pode estar dentro da janela)."
fi

# código de saída não quebra pipeline
if [[ $SHOULD_WARN -eq 1 ]]; then
  exit 10
else
  exit 0
fi
