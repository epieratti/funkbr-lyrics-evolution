#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="/root/funkbr-lyrics-evolution"
LOG_DIR="$PROJECT_DIR/logs"
LOCK="/tmp/funkbr_backup.lock"
mkdir -p "$LOG_DIR"

# snapshot padrão (sobrescreva via env SNAPSHOT=...)
SNAPSHOT="${SNAPSHOT:-$(date +%Y%m%d)_SPOTIFY}"
REMOTE="${REMOTE:-gdrive:Backups/funkbr-lyrics-evolution}"

# roda do diretório do projeto e carrega .env (se existir)
cd "$PROJECT_DIR"
set -a; [ -f .env ] && . ./.env; set +a

# guarda no log do dia
LOG="$LOG_DIR/backup_$(date +%F).log"
{
  echo "[$(date -Is)] starting backup_all (SNAPSHOT=$SNAPSHOT, REMOTE=$REMOTE)"
  flock -n "$LOCK" bash -lc 'SNAPSHOT='"$SNAPSHOT"' REMOTE='"$REMOTE"' make backup_all'
  RC=$?
  echo "[$(date -Is)] finished with code=$RC"
  exit $RC
} | tee -a "$LOG"
