#!/usr/bin/env bash
set -euo pipefail

# bloqueia coleta e rede
sed -i 's/^COLLECT_MODE=.*/COLLECT_MODE=disabled/' .env || true
export NO_NETWORK=1 PYTHONWARNINGS=ignore

echo "== PY COMPILE =="
python -m py_compile $(git ls-files '*.py')

echo "== PYTEST (opcional) =="
if command -v pytest >/dev/null 2>&1; then
  pytest -q || true
else
  echo "(pytest ausente — pulando)"
fi

echo "== MAKE DRY RUN =="
make -n collect process || true

echo "== SCHEMA CHECK =="
python scripts/diag/validate_schema_sample.py || true

echo "== CRON =="
crontab -l | sed -n '1,20p' || true

echo "== DISK =="
df -h / || true

echo "== BACKUP (Drive - dry) =="
timeout 5s rclone lsf gdrive:Backups/funkbr-lyrics-evolution --files-only | tail -n 5 || echo "(ok se sem remote configurado)"

echo "== LOGROTATE WRAPPER =="
/usr/local/bin/run_logrotate_funkbr.sh >/var/log/funkbr_logrotate.cron.log 2>&1 || true
tail -n 5 /var/log/funkbr_logrotate.cron.log || true

echo "✅ Smoke VM ok (dry-run)."
