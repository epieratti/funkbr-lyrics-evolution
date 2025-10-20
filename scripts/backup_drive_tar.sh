#!/usr/bin/env bash
set -euo pipefail

TOP="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
OUT_DIR="$TOP/backups"
LOG_DIR="$TOP/logs"
mkdir -p "$OUT_DIR" "$LOG_DIR"

REMOTE="${REMOTE:-gdrive:Backups/funkbr-lyrics-evolution}"

TAR_PATH="${1:-}"
if [[ -z "${TAR_PATH}" ]]; then
  TAR_PATH="$(ls -1t "${OUT_DIR}"/funkbr_*.tar.gz 2>/dev/null | head -n1 || true)"
  [[ -n "${TAR_PATH}" ]] || { echo "Nenhum tar encontrado em ${OUT_DIR}"; exit 1; }
fi

[[ -s "${TAR_PATH}" ]] || { echo "Tar inexistente/vazio: ${TAR_PATH}"; exit 1; }
STAMP="$(basename "${TAR_PATH%.tar.gz}" | sed 's/^funkbr_//')"
SUMS_PATH="${OUT_DIR}/SHA256SUMS-${STAMP}.txt"
[[ -s "${SUMS_PATH}" ]] || { echo "Checksums não encontrado: ${SUMS_PATH}"; exit 1; }

echo "Enviando:"
echo " - $(basename "${TAR_PATH}")"
echo " - $(basename "${SUMS_PATH}")"
echo " → ${REMOTE}"

rclone copyto "${TAR_PATH}"  "${REMOTE}/$(basename "${TAR_PATH}")"  --progress --fast-list
rclone copyto "${SUMS_PATH}" "${REMOTE}/$(basename "${SUMS_PATH}")" --progress --fast-list

echo "OK: enviados para ${REMOTE}" | tee -a "${LOG_DIR}/backup_$(date +%F).log"
