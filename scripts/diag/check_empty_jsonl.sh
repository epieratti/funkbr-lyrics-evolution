#!/usr/bin/env bash
set -euo pipefail
n=$(find data/raw data/snapshots -type f -name '*.jsonl' -size 0 | wc -l)
if [ "$n" -gt 0 ]; then
  echo "❌ JSONL vazios: $n"
  find data/raw data/snapshots -type f -name '*.jsonl' -size 0
  exit 2
fi
echo "✅ sem JSONL vazios"
