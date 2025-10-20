#!/usr/bin/env bash
set -euo pipefail

LOG_DIR="${1:-logs}"
DAYS_COMPRESS="${DAYS_COMPRESS:-7}"   # compacta logs .log com mais de 7 dias
DAYS_DELETE="${DAYS_DELETE:-30}"      # remove .log.gz com mais de 30 dias
MAX_SIZE_MB="${MAX_SIZE_MB:-512}"     # teto de espaço total do diretório

mkdir -p "$LOG_DIR"

# 1) Compactar .log mais antigos que DAYS_COMPRESS
#    Apenas arquivos .log (não mexe em .jsonl, .csv etc.)
find "$LOG_DIR" -type f -name '*.log' -mtime +"$DAYS_COMPRESS" -size +0c -print0 \
  | xargs -0 -I{} sh -c 'gzip -f "{}" && echo "[compress] {} -> {}.gz" || true'

# 2) Apagar .log.gz mais antigos que DAYS_DELETE
find "$LOG_DIR" -type f -name '*.log.gz' -mtime +"$DAYS_DELETE" -print0 \
  | xargs -0 -I{} sh -c 'rm -f "{}" && echo "[delete] {}" || true'

# 3) Teto de espaço total
#    Se exceder MAX_SIZE_MB, remove .log.gz mais antigos primeiro
TOTAL_MB="$(du -sm "$LOG_DIR" | awk "{print \$1}")"
if [ "${TOTAL_MB:-0}" -gt "$MAX_SIZE_MB" ]; then
  echo "[cap] $LOG_DIR = ${TOTAL_MB}MB > ${MAX_SIZE_MB}MB, iniciando limpeza por antiguidade"
  # remove em ordem de mais antigo até ficar abaixo do teto
  find "$LOG_DIR" -type f -name '*.log.gz' -printf '%T@ %p\n' \
    | sort -n \
    | awk '{print $2}' \
    | while read -r f; do
        rm -f "$f" && echo "[cap-delete] $f"
        TOTAL_MB="$(du -sm "$LOG_DIR" | awk "{print \$1}")"
        [ "${TOTAL_MB:-0}" -le "$MAX_SIZE_MB" ] && break
      done
fi

echo "[ok] retenção concluída em $LOG_DIR"
