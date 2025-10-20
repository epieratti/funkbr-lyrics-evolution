#!/usr/bin/env bash
set -euo pipefail
LOCK="${1:-/tmp/funkbr.lock}"
shift || true
exec 9>"$LOCK"
flock -n 9 || { echo "[lock] em execução, saindo"; exit 0; }
"$@"
