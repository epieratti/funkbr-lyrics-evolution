#!/usr/bin/env bash
# Verify that all required commands exist in PATH.
set -euo pipefail

if [ $# -lt 1 ]; then
  echo "usage: $0 <cmd> [cmd...]" >&2
  exit 64
fi

missing=0
for cmd in "$@"; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "[require_cmd] missing dependency: $cmd" >&2
    missing=1
  fi
done

if [ "$missing" -eq 1 ]; then
  exit 127
fi
