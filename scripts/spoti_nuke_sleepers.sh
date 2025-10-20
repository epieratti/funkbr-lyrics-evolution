#!/usr/bin/env bash
set -euo pipefail

echo "== varrendo sleepers ligados ao coletor/helper =="

killed=0
# pega PIDs cujo comando base é 'sleep NNNN'
while read -r PID ELAPSED CMD ARG; do
  # segurança: precisa ter 'sleep <numero>'
  [[ "$CMD" != "sleep" ]] && continue
  [[ "$ARG" =~ ^[0-9]+$ ]] || continue

  # pai e avo
  PPID=$(ps -o ppid= -p "$PID" | tr -d ' ')
  GPPID=$(ps -o ppid= -p "$PPID" | tr -d ' ')

  # cmdlines completos (binários separados por \0 em /proc)
  cmd_pid="$(tr '\0' ' ' < /proc/$PID/cmdline 2>/dev/null || true)"
  cmd_ppid="$(tr '\0' ' ' < /proc/$PPID/cmdline 2>/dev/null || true)"
  cmd_gppid="$(tr '\0' ' ' < /proc/$GPPID/cmdline 2>/dev/null || true)"

  chain="$cmd_pid | $cmd_ppid | $cmd_gppid"

  # heurística: qualquer nível contendo nosso helper ou o coletor
  if echo "$chain" | grep -Eiq 'spoti_wait_run\.sh|collect_spotify_catalog\.py|with_lock\.sh'; then
    PGID=$(ps -o pgid= -p "$PID" | tr -d ' ')
    echo "→ matando grupo PGID=$PGID  (PID=$PID) :: $chain"
    # mata o grupo inteiro: primeiro TERM, depois KILL se necessário
    kill -TERM -"${PGID}" 2>/dev/null || true
    sleep 0.5
    kill -KILL -"${PGID}" 2>/dev/null || true
    killed=$((killed+1))
  fi
done < <(ps -eo pid,etimes,comm,args | awk '$3=="sleep" && $4 ~ /^[0-9]+$/ {print $1, $2, $3, $4}')

echo "[ok] sleepers eliminados: $killed"
exit 0
