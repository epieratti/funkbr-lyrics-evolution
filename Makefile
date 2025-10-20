# Makefile — FunkBR
# Alvos mínimos, idempotentes e seguros

.PHONY: help setup pilot_100 collect sanity clean

help:               ## lista comandos
	@grep -E '^[a-zA-Z_-]+:.*?##' Makefile | awk 'BEGIN{FS=":.*?## "}; {printf "  %-14s %s\n", $$1, $$2}'

setup:              ## instala deps básicas (ignora falta de arquivo)
	python -m pip install -U pip || true
	[ -f requirements.txt ] && pip install -r requirements.txt || true
	python - <<'PY' || true
try:
	import spacy, sys
except Exception:
	sys.exit(0)
PY
	python -m spacy download pt_core_news_sm || true
	@echo "[setup] ok"

pilot_100:          ## piloto rápido (100 artistas) com snapshot datado
	python code/coletar_discografia_funk_br.py --limit_artists 100 --snapshot $$(date +%Y%m%d)

collect:            ## coleta bruta integral com snapshot datado
	python code/coletar_discografia_funk_br.py --snapshot $$(date +%Y%m%d)

sanity:             ## gera painéis de sanidade se existir script
	[ -f code/sanity_dashboard.py ] && python code/sanity_dashboard.py --out reports/sanity || echo "sanity: script ausente, pulando"

clean:              ## remove temporários locais
	rm -rf .cache __pycache__ tmp */__pycache__ 2>/dev/null || true
