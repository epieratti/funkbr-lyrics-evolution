#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

# --- carregar .env ---
set -a; [ -f .env ] && . ./.env; set +a
: "${MARKET:=BR}"

ARTIST_ID="${ARTIST_ID:-7FNnA9vBm6EKceENgCGRMb}"   # Anitta (ping p/ Retry-After)
LIMIT="${LIMIT:-50}"
SNAP="${SNAP:-}"        # se vazio, vira <YYYYMMDD>_SPOTIFY
EXTRA="${EXTRA:-60}"    # folga extra além do Retry-After
JUST_CHECK=0

usage() {
  echo "uso: $0 [--limit N] [--snap SNAPSHOT] [--extra seg] [--check-only] [--artist-id ID]" >&2
}

# --- parse args robusto ---
while [ $# -gt 0 ]; do
  case "$1" in
    --limit)
      if [ $# -lt 2 ]; then echo "ERRO: --limit requer argumento" >&2; usage; exit 2; fi
      LIMIT="$2"; shift 2;;
    --snap)
      if [ $# -lt 2 ]; then echo "ERRO: --snap requer argumento" >&2; usage; exit 2; fi
      SNAP="$2"; shift 2;;
    --extra)
      if [ $# -lt 2 ]; then echo "ERRO: --extra requer argumento" >&2; usage; exit 2; fi
      EXTRA="$2"; shift 2;;
    --artist-id)
      if [ $# -lt 2 ]; then echo "ERRO: --artist-id requer argumento" >&2; usage; exit 2; fi
      ARTIST_ID="$2"; shift 2;;
    --check-only)
      JUST_CHECK=1; shift;;
    *)
      echo "ERRO: argumento desconhecido: $1" >&2; usage; exit 2;;
  esac
done

# Snapshot default
if [ -z "$SNAP" ]; then
  SNAP="$(date +%Y%m%d)_SPOTIFY"
fi

# --- token de app ---
TOK="$( curl -sS -u "${SPOTIFY_CLIENT_ID}:${SPOTIFY_CLIENT_SECRET}" \
  -d grant_type=client_credentials https://accounts.spotify.com/api/token \
  | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4 )"
if [ -z "${TOK}" ]; then
  echo "❌ Falha ao obter access_token. Verifique SPOTIFY_CLIENT_ID/SECRET no .env" >&2
  exit 1
fi

# --- “ping” endpoint para ler Retry-After (em caso de 429) ---
HDRS="$( curl -sS -D- -o /dev/null \
  -H "Authorization: Bearer ${TOK}" \
  "https://api.spotify.com/v1/artists/${ARTIST_ID}" )"

HTTP="$(printf '%s\n' "$HDRS" | sed -n '1s/.* \([0-9][0-9][0-9]\).*/\1/p')"
RA="$(printf '%s\n' "$HDRS" | awk 'tolower($0) ~ /^retry-after:/ {print $2}' | tr -d "\r" )"
# sanitizar: manter só dígitos
RA_SEC="$(printf '%s' "${RA:-0}" | tr -cd '0-9')"
[ -z "$RA_SEC" ] && RA_SEC=0

if [ "$HTTP" = "429" ] && [ "$RA_SEC" -gt 0 ]; then
  SLEEP=$(( RA_SEC + EXTRA ))
  echo "HTTP=429 retry-after=${RA_SEC}s extra=${EXTRA}s  -> sleep=${SLEEP}s"
else
  SLEEP=0
  echo "HTTP=${HTTP} (sem Retry-After) — sem bloqueio agora."
fi

# ETA local/UTC
if [ "$SLEEP" -gt 0 ]; then
  echo "Acorda (local): $(date -d "now + ${SLEEP} seconds" +"%F %T" 2>/dev/null || date -v+${SLEEP}S +"%F %T")"
  echo "Acorda (UTC):   $(TZ=UTC date -d "now + ${SLEEP} seconds" +"%F %T" 2>/dev/null || TZ=UTC date -v+${SLEEP}S +"%F %T")"
fi

[ "$JUST_CHECK" -eq 1 ] && exit 0

LOG="logs/auto_collect_$(date +%F).log"
mkdir -p logs

CMD=( python -u code/collect_spotify_catalog.py --limit_artists "$LIMIT" --snapshot "$SNAP" )

if [ "$SLEEP" -gt 0 ]; then
  echo "→ Iniciando nohup com sleep=${SLEEP}s (log: $LOG)"
  nohup bash -lc "sleep ${SLEEP}; /root/funkbr-lyrics-evolution/scripts/with_lock.sh /tmp/funkbr_spotify_collect.lock \"${CMD[@]}\" >> '$LOG' 2>&1" >/dev/null 2>&1 &
  echo "PID do nohup: $!"
else
  echo "→ Sem sleep; iniciando agora (log: $LOG)"
  nohup /root/funkbr-lyrics-evolution/scripts/with_lock.sh /tmp/funkbr_spotify_collect.lock "${CMD[@]}" >> "$LOG" 2>&1 &
  echo "PID do nohup: $!"
fi

echo "Dicas:"
echo "  make spoti_ps"
echo "  tail -f '$LOG'"
