#!/usr/bin/env bash
set -euo pipefail

# Destino padrão
DRIVE_DIR="gdrive:Backups/funkbr-lyrics-evolution"
EXTRA_FLAGS=()

# Parse simples: primeiro argumento que NÃO começa com "-" vira destino.
# Todo o resto que começa com "-" vai para o rclone como flag.
for arg in "$@"; do
  if [[ "${arg}" == -* ]]; then
    EXTRA_FLAGS+=("$arg")
  elif [[ "${DRIVE_DIR}" == "gdrive:Backups/funkbr-lyrics-evolution" ]]; then
    DRIVE_DIR="${arg}"
  else
    echo "Ignorando argumento extra não reconhecido: ${arg}" >&2
  fi
done

echo "Destino: ${DRIVE_DIR}"
echo "Flags: ${EXTRA_FLAGS[*]:-nenhuma}"

rclone copy INDEX.md "${DRIVE_DIR}" "${EXTRA_FLAGS[@]}"
rclone copy CHECKLIST.txt "${DRIVE_DIR}" "${EXTRA_FLAGS[@]}"
rclone copy docs "${DRIVE_DIR}/docs" --copy-links "${EXTRA_FLAGS[@]}"

echo "Sincronizado com ${DRIVE_DIR}"
