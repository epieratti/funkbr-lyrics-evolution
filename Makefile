# Makefile — FunkBR
# Alvos mínimos e idempotentes

.PHONY: help setup pilot_100 collect sanity clean dedup_raw dedup_file dedup_raw_global

help:               ## lista comandos
	@grep -E '^[a-zA-Z_-]+:.*?##' Makefile | awk 'BEGIN{FS=":.*?## "}; {printf "  %-14s %s\n", $$1, $$2}'

setup:              ## instala deps básicas
	python -m pip install -U pip || true
	[ -f requirements.txt ] && pip install -r requirements.txt || true
	python -m spacy download pt_core_news_sm || true
	@echo "[setup] ok"

pilot_100:          ## piloto rápido (100 artistas)
	python code/coletar_discografia_funk_br.py --limit_artists 100 --snapshot $$(date +%Y%m%d)

collect:            ## coleta bruta integral
	python code/coletar_discografia_funk_br.py --snapshot $$(date +%Y%m%d)

sanity:             ## gera painéis de sanidade
	[ -f code/sanity_dashboard.py ] && python code/sanity_dashboard.py --out reports/sanity || echo "sanity: script ausente, pulando"

clean:              ## remove temporários
	rm -rf .cache __pycache__ tmp */__pycache__ 2>/dev/null || true

dedup_raw:          ## deduplica todos os .jsonl (escopo por arquivo)
	python code/dedup_snapshot.py --path data/raw --pattern "*.jsonl"

dedup_file:         ## deduplica um arquivo específico
	@[ -n "$(FILE)" ] || (echo "uso: make dedup_file FILE=path/para/arquivo.jsonl"; exit 1)
	python code/dedup_snapshot.py --path "$(shell dirname "$(FILE)")" --pattern "$(shell basename "$(FILE)")"

dedup_raw_global:   ## deduplica globalmente (mantém 1ª ocorrência em todo o conjunto)
	python code/dedup_snapshot.py --path data/raw --pattern "*.jsonl" --scope global
