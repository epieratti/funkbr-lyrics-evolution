#!/usr/bin/env bash
set -euo pipefail
D=$(date +%Y%m%d)
echo "JSONL do dia"
find data -type f -name "*${D}*.jsonl" -printf "%9s %p\n" | sort -h | tail -n 40
Z=$(find data -type f -name "*${D}*.jsonl" -size 0 -print | wc -l)
if [ "$Z" -gt 0 ]; then
  echo "WARNING existem $Z jsonl zerados do dia"
else
  echo "OK sem jsonl zerados do dia"
fi
