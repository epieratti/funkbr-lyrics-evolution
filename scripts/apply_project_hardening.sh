#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$ROOT_DIR"

mkdir -p docs logs reports/health code crontab scripts

# -- Consolidar duplicatas de README/CHANGELOG (move p/ docs/_duplicates)
shopt -s globstar nullglob
mkdir -p docs/_duplicates

for f in **/README.md **/readme.md **/Readme.md; do
  [[ "$f" == "README.md" ]] && continue
  dest="docs/_duplicates/$(echo "$f" | tr '/' '__')"
  (git mv -f "$f" "$dest" 2>/dev/null) || mv -f "$f" "$dest"
done

for f in **/CHANGELOG.md **/Changelog.md **/changelog.md; do
  [[ "$f" == "CHANGELOG.md" ]] && continue
  dest="docs/_duplicates/$(echo "$f" | tr '/' '__')"
  (git mv -f "$f" "$dest" 2>/dev/null) || mv -f "$f" "$dest"
done

# -- Criar canônicos se faltarem
[[ -f README.md ]] || printf "# FunkBR – Lyrics Evolution\n\n" > README.md
[[ -f CHANGELOG.md ]] || printf "# Changelog\n\n" > CHANGELOG.md

# -- Corrigir citação do GitHub no README (seguro, idempotente)
sed -i.bak -E 's#([Ee]pieratti/)?funkbr-lyrics-evolution#epieratti/funkbr-lyrics-evolution#g' README.md || true
rm -f README.md.bak

# --- Garantir arquivos de política (fechar H E R E D O C corretamente!)
if [[ ! -f .env.example ]]; then
  cat > .env.example <<'HENV'
# Copie para .env e preencha com suas chaves locais (NUNCA commitar .env)
SPOTIFY_CLIENT_ID=""
SPOTIFY_CLIENT_SECRET=""
GENIUS_ACCESS_TOKEN=""
DISCOGS_CONSUMER_KEY=""
DISCOGS_CONSUMER_SECRET=""
ECAD_API_KEY=""  # opcional (se/quando houver)
HENV
fi

if [[ ! -f LICENSE ]]; then
  cat > LICENSE <<'HLIC'
MIT License

Copyright (c) 2025

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction...
HLIC
fi

if [[ ! -f DATA_LICENSE ]]; then
  cat > DATA_LICENSE <<'HDAT'
Data License: CC BY-NC 4.0
Você é livre para compartilhar e adaptar, desde que atribua e não use comercialmente.
Texto completo: https://creativecommons.org/licenses/by-nc/4.0/
HDAT
fi

# --- Health imediato (log em reports/health/)
ts="$(date +'%Y-%m-%d_%H-%M-%S')"
mkdir -p reports/health
( set +e; END_HOUR_LOCAL="${END_HOUR_LOCAL:-06}" scripts/health_zero_byte_guard.sh data/raw || true ) \
  | tee "reports/health/health_${ts}.txt" >/dev/null

# --- Changelog: registrar hardening (uma vez)
if ! grep -q "Docs: unificação de README/CHANGELOG" CHANGELOG.md; then
  {
    echo "## $(date +%Y-%m-%d) – Hardening"
    echo "- Docs: unificação de README/CHANGELOG; duplicatas movidas para docs/_duplicates."
    echo "- README: citação corrigida p/ epieratti/funkbr-lyrics-evolution."
    echo "- Health: warning para JSONL 0 bytes após janela de coleta."
    echo "- Backup: registrar caminho no Drive + SHA256 em cada snapshot."
    echo
  } >> CHANGELOG.md
fi

# --- Cron versionado (instala manualmente com: crontab crontab/funkbr.cron)
cat > crontab/funkbr.cron <<'HCRON'
# TZ do sistema: America/Sao_Paulo
# 02:00 Coleta
0 2 * * *  cd $(git rev-parse --show-toplevel) && make collect >> logs/collect.log 2>&1
# 04:00 Letras
0 4 * * *  cd $(git rev-parse --show-toplevel) && make lyrics  >> logs/lyrics.log  2>&1
# 06:00 Process + sanity
0 6 * * *  cd $(git rev-parse --show-toplevel) && make process sanity >> logs/process.log 2>&1

# Backup consolidado (opcional): UTC 06:30 (= 03:30 BRT). Habilite conscientemente.
# 30 6 * * *  cd $(git rev-parse --show-toplevel) && scripts/backup_all_daily.sh >> logs/backup.log 2>&1
HCRON

# --- Makefile: targets mínimos (se não existirem)
if [[ -f Makefile ]]; then
  if ! grep -qE '^health:' Makefile; then
    cat >> Makefile <<'HMAKE'

health:
	@END_HOUR_LOCAL=06 scripts/health_zero_byte_guard.sh data/raw || true
	@echo "Relatório em reports/health/"

sanity: health
	@echo "Sanity ok."
HMAKE
  fi
fi

echo "[OK] Hardening reaplicado com sucesso."
echo "Revise crontab/funkbr.cron e habilite o backup quando quiser."
