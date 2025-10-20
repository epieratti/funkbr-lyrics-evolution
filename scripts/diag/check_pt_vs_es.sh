#!/usr/bin/env bash
set -euo pipefail
F="processed_brcorpus/brcorpus_$(date +%F)_pt.jsonl"
[ -f "$F" ] || { echo "faltando $F"; exit 1; }
echo "busca pistas espanhol forte"
grep -Ei ' cómo | canción | corazón | mañana ' "$F" | head || echo "ok sem espanhol forte"
