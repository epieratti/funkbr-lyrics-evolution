#!/usr/bin/env bash
set -euo pipefail

TOP="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
OUT_DIR="$TOP/backups"
LOG_DIR="$TOP/logs"
mkdir -p "$OUT_DIR" "$LOG_DIR"

STAMP="$(date +%Y%m%d_%H%M)"
SNAP="funkbr_${STAMP}.tar.gz"
SUMS="SHA256SUMS-${STAMP}.txt"

EXCLUDES=(
  --exclude=.venv
  --exclude=venv
  --exclude=.mypy_cache
  --exclude=__pycache__
  --exclude=.pytest_cache
  --exclude=data/raw
  --exclude=data/snapshots
  --exclude=*.pyc
  --exclude=backups     # evita capturar o próprio destino
)

TMP_TAR="$(mktemp -p /tmp ".funkbr_${STAMP}.XXXXXX.tar.gz")"
trap 'rm -f "${TMP_TAR}"' EXIT

# Gera tar em /tmp com exclusões aplicadas
tar -C "${TOP}" -czf "${TMP_TAR}" "${EXCLUDES[@]}" .

# Calcula hash já apontando para o NOME FINAL do arquivo
HASH="$(sha256sum "${TMP_TAR}" | cut -d' ' -f1)"
printf "%s  %s\n" "${HASH}" "${SNAP}" > "${OUT_DIR}/${SUMS}"

# Move o tar para o destino com o nome final (atômico) e ajusta permissão
mv -f "${TMP_TAR}" "${OUT_DIR}/${SNAP}"
chmod 0644 "${OUT_DIR}/${SNAP}" "${OUT_DIR}/${SUMS}"

{
  echo "== Snapshot pronto =="
  echo "Arquivo: ${OUT_DIR}/${SNAP}"
  echo "SHA256:  ${HASH}"
} | tee -a "${LOG_DIR}/backup_$(date +%F).log"
