#!/usr/bin/env bash
set -euo pipefail
LOGDIR="${1:-logs}"
grep -Ehi "warn|warning" "$LOGDIR"/*.log 2>/dev/null | tail -n 200 || echo "sem warnings"
