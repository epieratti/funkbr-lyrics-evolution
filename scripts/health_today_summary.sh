#!/usr/bin/env bash
set -euo pipefail
END_HOUR_LOCAL="${END_HOUR_LOCAL:-06}"
scripts/health_zero_byte_guard.sh data/raw || true
