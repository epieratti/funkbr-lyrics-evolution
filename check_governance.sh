#!/usr/bin/env bash
set -euo pipefail
ok=0; warn=0; fail=0
pass(){ echo "OK   $1"; ok=$((ok+1)); }
note(){ echo "WARN $1"; warn=$((warn+1)); }
err(){ echo "FAIL $1" >&2; fail=$((fail+1)); }
need_file(){ [[ -f "$1" ]] && pass "Arquivo existe  $1" || err "Arquivo ausente  $1"; }
non_empty(){ [[ -s "$1" ]] && pass "Não vazio       $1" || err "Vazio ou 0B     $1"; }
grep_must(){ grep -qE "$1" "$2" && pass "Conteúdo ok $3" || err "Conteúdo faltando $3"; }
grep_must_not(){ grep -qE "$1" "$2" && err "Placeholder $3" || pass "Sem placeholder $3"; }

need_file INDEX.md
need_file CHECKLIST.txt
need_file docs/sanity_checklist.md
need_file docs/backup_policy.md
need_file docs/data_ethics.md
need_file docs/incident_log_revised.md

for f in INDEX.md CHECKLIST.txt docs/*.md; do non_empty "$f"; done
grep_must "^# " INDEX.md "INDEX title"
grep_must "^# ✅ Sanity Checklist|^# Sanity Checklist" docs/sanity_checklist.md "Sanity header"
grep_must "^# Política de Backup|^# Politica de Backup" docs/backup_policy.md "Backup header"
grep_must "^# Política Ética de Dados|^# Politica Ética de Dados" docs/data_ethics.md "Ethics header"
grep_must "^# Incident Log" docs/incident_log_revised.md "Incident header"

if [[ -f README.md ]]; then
  grep_must "github.com/epieratti/funkbr-lyrics-evolution" README.md "Repo URL"
  grep_must_not "github.com/seuusuario/funkbr-lyrics-evolution" README.md "Placeholder"
fi

echo "Resumo OK=$ok WARN=$warn FAIL=$fail"
if [[ $fail -gt 0 ]]; then exit 1; fi
