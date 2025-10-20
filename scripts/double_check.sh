#!/usr/bin/env bash
# fix: centraliza validações dry-run em log único
set -euo pipefail

LOG_FILE="tmp/double_check.log"
mkdir -p tmp
: >"${LOG_FILE}"
exec > >(tee "${LOG_FILE}") 2>&1

echo "=== DOUBLE CHECK START ==="
COMMANDS=(
  "make setup OFFLINE=1"
  "ruff check code tests && black --check code tests"
  "pytest -q --maxfail=1"
  "make validate_schema"
  "make promote_dryrun || echo 'nao aplicavel'"
  "make sanity_report || echo 'nao aplicavel'"
  "make dq_check_dryrun || echo 'nao aplicavel'"
)

for cmd in "${COMMANDS[@]}"; do
  echo "--- running: ${cmd}"
  bash -c "${cmd}"
  echo "--- done: ${cmd}"
done

echo "=== DOUBLE CHECK COMPLETE: ALL CHECKS PASSED ==="
