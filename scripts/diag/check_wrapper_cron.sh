#!/usr/bin/env bash
set -euo pipefail
test -f /etc/cron.d/funkbr_logrotate && echo "cron wrapper presente" || echo "cron wrapper ausente"
tail -n 50 /var/log/funkbr_logrotate.cron.log 2>/dev/null || echo "sem log do wrapper ainda"
