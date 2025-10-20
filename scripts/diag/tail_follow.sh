#!/usr/bin/env bash
set -euo pipefail
tail -n 100 -F logs/*.log
