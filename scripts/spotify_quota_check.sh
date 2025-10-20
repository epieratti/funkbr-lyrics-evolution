#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
[ -f .env ] && set -a && . ./.env && set +a
CID="${SPOTIFY_CLIENT_ID:-}"; SEC="${SPOTIFY_CLIENT_SECRET:-}"
test -n "$CID" && test -n "$SEC" || { echo "❌ faltam SPOTIFY_CLIENT_ID/SECRET no .env"; exit 1; }

# token app
TOK=$(curl -sS -u "$CID:$SEC" -d grant_type=client_credentials https://accounts.spotify.com/api/token \
      | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)

# consulta um artist e lê Retry-After se rate-limited
HDR=$(curl -sSI -H "Authorization: Bearer $TOK" https://api.spotify.com/v1/artists/7FNnA9vBm6EKceENgCGRMb | tr -d '\r')
RA=$(printf "%s\n" "$HDR" | awk -F': ' '/^Retry-After:/{print $2; exit}')
DATE=$(printf "%s\n" "$HDR" | awk -F': ' '/^date:/{print $2; exit}')
echo "date: $DATE"
if [ -n "${RA:-}" ]; then
  NOWUTC=$(date -u +%s); UNLOCK=$((NOWUTC + RA))
  echo "Retry-After: ${RA}s"
  echo -n "Libera (UTC):               "; date -u -d "@$UNLOCK"
  echo -n "Libera (America/Sao_Paulo): "; TZ=America/Sao_Paulo date -d "@$UNLOCK"
  exit 2
else
  echo "Sem Retry-After — sem bloqueio no momento."
fi
