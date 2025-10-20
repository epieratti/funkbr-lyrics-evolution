#!/usr/bin/env bash
set -euo pipefail
ROOT="${1:-$PWD}"
bash "$ROOT/scripts/diag/health_diag.sh" "$ROOT"
bash "$ROOT/scripts/diag/check_pt_vs_es.sh"
bash "$ROOT/scripts/diag/summarize_corpus.sh"
bash "$ROOT/scripts/diag/check_coleta_dia.sh"
bash "$ROOT/scripts/diag/logrotate_status.sh"
bash "$ROOT/scripts/diag/check_wrapper_cron.sh"
