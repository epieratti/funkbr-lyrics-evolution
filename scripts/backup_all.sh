#!/usr/bin/env bash
set -euo pipefail

# --- Parâmetros/Defaults ---
REMOTE="${REMOTE:-gdrive:Backups/funkbr-lyrics-evolution}"   # rclone remoto
STAMP="${STAMP:-$(date +%F_%H%M)}"
TAR="/tmp/funkbr_${STAMP}.tar.gz"
SNAP="${SNAPSHOT:-}"                                         # só para mensagem de commit
GIT_REMOTE="${GIT_REMOTE:-origin}"
GIT_BRANCH="${GIT_BRANCH:-main}"

echo "[1/3] TAR local -> $TAR"
# compacta tudo exceto venv, dados crus e logs
tar \
  --exclude='venv' \
  --exclude='logs' \
  --exclude='data/raw' \
  --exclude='data/tmp' \
  --exclude='*.tar.gz' \
  -czf "$TAR" .

echo "[2/3] Upload p/ Google Drive -> $REMOTE"
# requer rclone com remoto 'gdrive' configurado
rclone copy "$TAR" "$REMOTE" \
  --checkers 8 --transfers 4 --drive-chunk-size 64M --retries 5 --progress

echo "[3/3] Git push do código (sem dados/segredos)"
# garante user.name/email mínimos p/ commit (sem sobrescrever se já definidos)
git config user.name  >/dev/null 2>&1 || git config user.name "funkbr-bot"
git config user.email >/dev/null 2>&1 || git config user.email "funkbr-bot@local"

# verifica que o remoto existe
if ! git remote get-url "$GIT_REMOTE" >/dev/null 2>&1; then
  echo "⚠️  Remoto '$GIT_REMOTE' não existe. Pulei o push."
  exit 0
fi

# adiciona/commita apenas o que não está ignorado
git add -A
if git diff --cached --quiet; then
  echo "ℹ️  Nada para commitar (workspace limpo)."
else
  MSG="backup: code snapshot ${STAMP}"
  [ -n "$SNAP" ] && MSG="$MSG (snapshot=$SNAP)"
  git commit -m "$MSG"
  # garante branch atual
  CUR=$(git rev-parse --abbrev-ref HEAD)
  [ "$CUR" = "HEAD" ] && CUR="$GIT_BRANCH"
  git push "$GIT_REMOTE" "$CUR":"$GIT_BRANCH"
  echo "✅ push OK -> $GIT_REMOTE/$GIT_BRANCH"
fi

echo "[ok] Backup local, Drive e Git finalizados."
