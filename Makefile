SNAPSHOT ?= $(shell date +%Y%m%d)
ARGS ?=
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
	python code/coletar_discografia_funk_br.py $(ARGS) --snapshot $(SNAPSHOT)
	@[ -s logs/collector.jsonl ] && cp -f logs/collector.jsonl data/raw/funk_br_discografia_raw_$(SNAPSHOT).jsonl || true

collect:            ## coleta bruta integral
	OUTPUT_JSONL="data/raw/funk_br_discografia_raw_$(SNAPSHOT).jsonl" \
	python code/coletar_discografia_funk_br.py $(ARGS) --snapshot $(SNAPSHOT)
	@[ -s logs/collector.jsonl ] && cp -f logs/collector.jsonl data/raw/funk_br_discografia_raw_$(SNAPSHOT).jsonl || true
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

collect+dedup:      ## coleta e roda dedup global (1 comando)
	./scripts/run_collect_with_dedup.sh $(shell date +%Y%m%d)

pilot_100+dedup:    ## piloto (100) e dedup global
	LIMIT=100 ./scripts/run_pilot_with_dedup.sh $(shell date +%Y%m%d)

health: ## checa cron, logs de hoje, jsonl e backup
	@echo "== CRON lines ==" && crontab -l | sed -n '1,12p'
	@echo "== Cron status ==" && systemctl is-active cron
	@echo "== Logs dir ==" && ls -ld logs || true
	@echo "== Logs de hoje ==" && ls -lh logs/*$$(date +%F)*.log 2>/dev/null || echo "(ainda sem logs de hoje)"
	@echo "== JSONL hoje (0 bytes) ==" && find data/raw -maxdepth 1 -type f -name "*$$(date +%Y%m%d)*.jsonl" -size 0 -printf "%f\n" || true
	@echo "== Backup usage ==" && du -sh /mnt/backup/raw /mnt/backup/processed 2>/dev/null || true
