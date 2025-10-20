#!/usr/bin/env bash
set -euo pipefail

# 1) Coleta limitada (100 artistas) via variável de ambiente
echo "[full] coletando primeiro lote (100 artistas)…"
COLLECT_MODE="enabled" LIMIT_ARTISTS=100 make collect_spotify

# 2) Descobrir JSONL bruto mais recente
LATEST_JSONL="$(ls -t data/raw/funk_br_discografia_raw_*.jsonl 2>/dev/null | head -n1 || true)"
if [ -z "${LATEST_JSONL:-}" ]; then
  echo "[full] ERRO: nenhum JSONL encontrado em data/raw/"
  exit 2
fi

# 3) Verificar se gravou >=100 linhas
LINES="$(wc -l < "$LATEST_JSONL" || echo 0)"
echo "[full] arquivo: $LATEST_JSONL | linhas: $LINES"
if [ "$LINES" -ge 100 ]; then
  echo "[full] OK (>=100). Coletando restante sem limite…"
  COLLECT_MODE="enabled" LIMIT_ARTISTS=0 make collect_spotify
  echo "[full] rodada completa — executando process/sanity…"
  make process sanity || true
else
  echo "[full] FALHA: menos de 100 linhas. Abortando coleta total."
  exit 3
fi
