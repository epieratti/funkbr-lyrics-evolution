#!/usr/bin/env bash
set -euo pipefail

# Uso:
#   HEALTH_STRICT=true ./scripts/health_warning_gate.sh --data-dir data/raw --window-end "06:30"
# Parâmetros:
#   --data-dir     pasta onde ficam os JSONL do dia
#   --window-end   horário local de fechamento da janela, formato HH:MM
#   --tag          opcional, rótulo do snapshot (ex: 20251021_SPOTIFY)
#
# Saída: escreve um arquivo reports/health/health_YYYY-MM-DD_HHMM.txt e printa no stdout.

DATA_DIR=""
WINDOW_END=""
TAG=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --data-dir)    DATA_DIR="$2"; shift 2;;
    --window-end)  WINDOW_END="$2"; shift 2;;
    --tag)         TAG="$2"; shift 2;;
    *) echo "Parâmetro desconhecido: $1" >&2; exit 2;;
  esac
done

if [[ -z "${DATA_DIR}" || -z "${WINDOW_END}" ]]; then
  echo "Obrigatório: --data-dir e --window-end" >&2
  exit 2
fi

# Data de hoje no timezone da VM
TODAY="$(date +%F)"
NOW_HM="$(date +%H:%M)"
STAMP="$(date +%Y-%m-%d_%H%M)"
OUT_DIR="reports/health"
OUT_FILE="${OUT_DIR}/health_${STAMP}.txt"
mkdir -p "${OUT_DIR}"

# Soma de bytes dos JSONL do DIA dentro de DATA_DIR
# Considera arquivos modificados hoje
TOTAL_BYTES=0
while IFS= read -r -d '' f; do
  sz=$(stat -c%s "$f" 2>/dev/null || echo 0)
  TOTAL_BYTES=$((TOTAL_BYTES + sz))
done < <(find "${DATA_DIR}" -type f -name "*.jsonl" -newermt "${TODAY} 00:00" ! -newermt "${TODAY} 23:59:59" -print0 2>/dev/null || true)

STATUS="INFO"
REASON="janela ainda não fechou"
if [[ "${NOW_HM}" > "${WINDOW_END}" ]]; then
  if [[ "${TOTAL_BYTES}" -eq 0 ]]; then
    if [[ "${HEALTH_STRICT:-false}" == "true" ]]; then
      STATUS="WARNING"
      REASON="JSONL do dia com 0 bytes após janela ${WINDOW_END}"
    else
      STATUS="OK"
      REASON="STRICT desativado e 0 bytes após janela; apenas informativo"
    fi
  else
    STATUS="OK"
    REASON="dados presentes após janela ${WINDOW_END}"
  fi
fi

{
  echo "HEALTH REPORT — FunkBR-Lyrics-Evolution"
  echo "Data........: ${TODAY}"
  echo "Hora local..: ${NOW_HM}"
  echo "Janela fim..: ${WINDOW_END}"
  echo "Tag.........: ${TAG:-n/a}"
  echo "Data dir....: ${DATA_DIR}"
  echo "Total bytes.: ${TOTAL_BYTES}"
  echo "Status......: ${STATUS}"
  echo "Motivo......: ${REASON}"
} | tee "${OUT_FILE}"

# exit code sempre 0: é um gate informativo
exit 0
