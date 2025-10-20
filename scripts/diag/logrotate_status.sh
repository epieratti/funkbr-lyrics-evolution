#!/usr/bin/env bash
set -euo pipefail
grep -E '/root/funkbr-lyrics-evolution/logs/.*\.log' /var/lib/logrotate/status || echo "sem entradas específicas no status"
ls -lah /root/funkbr-lyrics-evolution/logs | sed -n '1,120p'
