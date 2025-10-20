#!/usr/bin/env bash
set -euo pipefail

# Configs
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SNAPSHOT="${SNAPSHOT:-$(date +%Y%m%d_%H%M)}"
REMOTE="${REMOTE:-gdrive:Backups/funkbr-lyrics-evolution}"
DEST_DIR="${REMOTE}/full/${SNAPSHOT}"
TAR_DIR="${REMOTE}/tar"
TMP_TAR="/tmp/funkbr_full_${SNAPSHOT}.tar.gz"

echo "[1/4] Gerando TAR completo (sem exclusões): $TMP_TAR"
tar -czf "$TMP_TAR" -C "$PROJECT_DIR" .

echo "[2/4] Subindo TAR para o Drive: ${TAR_DIR}"
rclone copy "$TMP_TAR" "$TAR_DIR" \
  --progress --checkers 8 --transfers 4 --drive-chunk-size 64M --retries 5

echo "[3/4] Espelhando árvore completa no Drive: ${DEST_DIR}"
# cópia 1:1 da árvore (inclui arquivos ocultos, .env, venv, data, logs, etc.)
rclone sync "$PROJECT_DIR" "$DEST_DIR" \
  --progress --checkers 8 --transfers 8 --fast-list --metadata \
  --drive-chunk-size 64M --retries 5

# manifestos de verificação (úteis p/ auditoria/restauração)
echo "[4/4] Gravando manifestos de integridade"
( cd "$PROJECT_DIR" && find . -type f -print0 | xargs -0 sha256sum ) > "/tmp/sha256_${SNAPSHOT}.txt"
rclone copy "/tmp/sha256_${SNAPSHOT}.txt" "${DEST_DIR}/" --progress

echo "✅ Backup completo concluído."
echo "• TAR:     ${TAR_DIR}/funkbr_full_${SNAPSHOT}.tar.gz"
echo "• Mirror:  ${DEST_DIR}/"
echo "• SHA256:  ${DEST_DIR}/sha256_${SNAPSHOT}.txt"
