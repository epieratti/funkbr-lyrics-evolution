#!/usr/bin/env bash
# Acquire an exclusive lock and execute the given command.
set -euo pipefail

if [ $# -lt 3 ]; then
  echo "usage: $0 <lock_file> -- <command> [args...]" >&2
  exit 64
fi

LOCK_FILE="$1"
shift
if [ "$1" != "--" ]; then
  echo "usage: $0 <lock_file> -- <command> [args...]" >&2
  exit 64
fi
shift

LOCK_WAIT_SECS="${LOCK_WAIT_SECS:-5}"
mkdir -p "$(dirname "$LOCK_FILE")"
exec 9>"$LOCK_FILE"

if [ "$LOCK_WAIT_SECS" = "0" ]; then
  if ! flock -n 9; then
    echo "[lock] busy: $LOCK_FILE" >&2
    exit 75
  fi
elif ! flock -w "$LOCK_WAIT_SECS" 9; then
  echo "[lock] busy: $LOCK_FILE" >&2
  exit 75
fi

echo "[lock] acquired: $LOCK_FILE" >&2
trap 'flock -u 9' EXIT
"$@"
