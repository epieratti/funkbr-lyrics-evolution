#!/usr/bin/env bash
set -euo pipefail
ROOT="${1:-$PWD}"
cd "$ROOT"

echo "[1] Data check"
find data -type f -name "*.jsonl" -printf "%TY-%Tm-%Td %TH:%TM %s %p\n" | sort -k1,2 | tail -n 20 || true
echo

echo "[2] Zero-bytes hoje"
TODAY="$(date +%Y-%m-%d)"
FOUND=0
while IFS= read -r -d '' f; do
  sz=$(stat -c%s "$f" 2>/dev/null || echo 0)
  if [ "$sz" -eq 0 ]; then
    echo "ZERO $f"
    FOUND=1
  fi
done < <(find data -type f -name "*$(date +%Y%m%d)*.jsonl" -print0 2>/dev/null || true)
[ "$FOUND" -eq 0 ] && echo "ok sem zero-bytes de hoje" || true
echo

echo "[3] Corpus BR e PT sizes"
b="processed_brcorpus/brcorpus_$(date +%F).jsonl"
p="processed_brcorpus/brcorpus_$(date +%F)_pt.jsonl"
[ -f "$b" ] && echo -n "$b " && wc -l "$b" || echo "faltando $b"
[ -f "$p" ] && echo -n "$p " && wc -l "$p" || echo "faltando $p"
echo

echo "[4] Grep erros e warnings de hoje"
grep -Ehi "(error|failed|exception|traceback)" logs/*$(date +%Y-%m-%d)*.log 2>/dev/null | tail -n 50 || echo "ok sem erros em logs de hoje"
grep -Ehi "warn|warning" logs/*$(date +%Y-%m-%d)*.log 2>/dev/null | tail -n 50 || echo "sem warnings relevantes"
echo

echo "[5] Cron hints"
crontab -l 2>/dev/null || echo "sem crontab user"
ls -lah /etc/cron.d | sed -n '1,80p' || true
echo

echo "[6] Espaço em disco"
df -h | sed -n '1,200p'
echo

echo "[7] Drive sync dry-run"
if command -v rclone >/dev/null 2>&1; then
  ./sync_drive.sh --dry-run || echo "sync dry-run falhou"
else
  echo "rclone não encontrado"
fi
echo

echo "[8] Git status"
git status -sb || true
