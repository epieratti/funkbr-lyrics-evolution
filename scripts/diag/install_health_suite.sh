#!/usr/bin/env bash
set -euo pipefail
ROOT="${1:-$PWD}"
mkdir -p "$ROOT/scripts/diag"

# 1.1 health_diag principal
cat > "$ROOT/scripts/diag/health_diag.sh" <<'EOT'
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
EOT

# 1.2 grep rápido
cat > "$ROOT/scripts/diag/grep_errors.sh" <<'EOT'
#!/usr/bin/env bash
set -euo pipefail
LOGDIR="${1:-logs}"
grep -Ehi "(error|failed|exception|traceback)" "$LOGDIR"/*.log 2>/dev/null | tail -n 200 || echo "ok sem erros"
EOT

cat > "$ROOT/scripts/diag/grep_warnings.sh" <<'EOT'
#!/usr/bin/env bash
set -euo pipefail
LOGDIR="${1:-logs}"
grep -Ehi "warn|warning" "$LOGDIR"/*.log 2>/dev/null | tail -n 200 || echo "sem warnings"
EOT

# 1.3 ver últimos logs
cat > "$ROOT/scripts/diag/tail_follow.sh" <<'EOT'
#!/usr/bin/env bash
set -euo pipefail
tail -n 100 -F logs/*.log
EOT

# 1.4 valida corpus PT contra espanhol
cat > "$ROOT/scripts/diag/check_pt_vs_es.sh" <<'EOT'
#!/usr/bin/env bash
set -euo pipefail
F="processed_brcorpus/brcorpus_$(date +%F)_pt.jsonl"
[ -f "$F" ] || { echo "faltando $F"; exit 1; }
echo "busca pistas espanhol forte"
grep -Ei ' cómo | canción | corazón | mañana ' "$F" | head || echo "ok sem espanhol forte"
EOT

# 1.5 sumariza corpus
cat > "$ROOT/scripts/diag/summarize_corpus.sh" <<'EOT'
#!/usr/bin/env bash
set -euo pipefail
FULL="processed_brcorpus/brcorpus_$(date +%F).jsonl"
PT="processed_brcorpus/brcorpus_$(date +%F)_pt.jsonl"
[ -f "$FULL" ] && echo -n "full " && wc -l "$FULL" || echo "faltando $FULL"
[ -f "$PT" ]   && echo -n "pt   " && wc -l "$PT"   || echo "faltando $PT"
if [ -f "$FULL" ] && [ -f "$PT" ]; then
  diff <(sed 's/.*"track_id":"\([^"]*\)".*/\1/' "$FULL" | sort) <(sed 's/.*"track_id":"\([^"]*\)".*/\1/' "$PT" | sort) | head -n 50 || true
fi
EOT

# 1.6 sanity coleta dia
cat > "$ROOT/scripts/diag/check_coleta_dia.sh" <<'EOT'
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
EOT

# 1.7 ver status do logrotate
cat > "$ROOT/scripts/diag/logrotate_status.sh" <<'EOT'
#!/usr/bin/env bash
set -euo pipefail
grep -E '/root/funkbr-lyrics-evolution/logs/.*\.log' /var/lib/logrotate/status || echo "sem entradas específicas no status"
ls -lah /root/funkbr-lyrics-evolution/logs | sed -n '1,120p'
EOT

# 1.8 checagem de cron do wrapper
cat > "$ROOT/scripts/diag/check_wrapper_cron.sh" <<'EOT'
#!/usr/bin/env bash
set -euo pipefail
test -f /etc/cron.d/funkbr_logrotate && echo "cron wrapper presente" || echo "cron wrapper ausente"
tail -n 50 /var/log/funkbr_logrotate.cron.log 2>/dev/null || echo "sem log do wrapper ainda"
EOT

# 1.9 runner único de health
cat > "$ROOT/scripts/diag/run_full_health.sh" <<'EOT'
#!/usr/bin/env bash
set -euo pipefail
ROOT="${1:-$PWD}"
bash "$ROOT/scripts/diag/health_diag.sh" "$ROOT"
bash "$ROOT/scripts/diag/check_pt_vs_es.sh"
bash "$ROOT/scripts/diag/summarize_corpus.sh"
bash "$ROOT/scripts/diag/check_coleta_dia.sh"
bash "$ROOT/scripts/diag/logrotate_status.sh"
bash "$ROOT/scripts/diag/check_wrapper_cron.sh"
EOT

chmod +x "$ROOT"/scripts/diag/*.sh
echo "OK toolkit instalado em $ROOT/scripts/diag"
EOT

echo "Instalador criado em scripts/diag/install_health_suite.sh"
