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
	set -a; [ -f .env ] && . ./.env; set +a
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

# Cria/atualiza rascunho de release no GitHub
# Uso:
#   make release_draft VERSION=v0.2.0

# Cria/atualiza rascunho de release no GitHub
# Uso:
#   make release_draft VERSION=v0.2.0
# Anexa automaticamente os arquivos mais recentes de dados e sanity (se existirem)
# Cria/atualiza rascunho de release no GitHub
#   make release_draft VERSION=v0.2.0
# - Exige RELEASE_NOTES_<VERSION>_draft.md
# - Coleta até 3 .jsonl (data/raw) e 3 .csv (reports/sanity)
# - Prefixa cada arquivo com snapshot YYYYMMDD_HHMM_ antes de enviar
release_draft: ## cria ou atualiza release draft com prefixo de snapshot
	@if [ -z "$(VERSION)" ]; then echo "Uso: make release_draft VERSION=vX.Y.Z"; exit 1; fi
	@if [ ! -f "RELEASE_NOTES_$(VERSION)_draft.md" ]; then echo "Arquivo RELEASE_NOTES_$(VERSION)_draft.md não encontrado."; exit 1; fi
	@echo "== Criando/atualizando release $(VERSION) no GitHub =="
	@gh release create $(VERSION) --draft --title "$(VERSION) — em desenvolvimento" --notes-file RELEASE_NOTES_$(VERSION)_draft.md 2>/dev/null \
	 || gh release edit $(VERSION) --draft --title "$(VERSION) — em desenvolvimento" --notes-file RELEASE_NOTES_$(VERSION)_draft.md
	@echo "== Selecionando artefatos recentes =="
	@RAW_LATEST=$$(ls -t data/raw/*.jsonl 2>/dev/null | head -n 3); \
	SANITY_LATEST=$$(ls -t reports/sanity/*.csv 2>/dev/null | head -n 3); \
	SNAP=$$(date +%Y%m%d_%H%M); \
	TMP=$$(mktemp -d); \
	if [ -n "$$RAW_LATEST$$SANITY_LATEST" ]; then \
		echo "Staging em $$TMP (prefixo: $$SNAP_)"; \
		for f in $$RAW_LATEST $$SANITY_LATEST; do \
			[ -f "$$f" ] || continue; \
			bn=$$(basename "$$f"); \
			cp "$$f" "$$TMP/$$SNAP"_$$bn; \
		done; \
		if compgen -G "$$TMP/*" > /dev/null; then \
			echo "== Enviando assets prefixados =="; \
			gh release upload $(VERSION) $$TMP/* --clobber; \
		else \
		fi; \
		rm -rf "$$TMP"; \
	else \
		echo "(nenhum .jsonl/.csv recente encontrado)"; \
	fi
	@echo "✓ Release draft atualizada: $(VERSION)"
spotify_ready: ## checklist automatizado p/ pipeline Spotify
	@./scripts/spotify_ready.sh
.PHONY: lyrics
lyrics: ## baixa/atualiza letras (se script existir)
	@set -e; set -a; [ -f .env ] && . ./.env; set +a; \
	if [ -f code/run_lyrics.py ]; then \
		echo "[lyrics] rodando code/run_lyrics.py …"; \
		OUTPUT_JSONL="data/raw/funk_br_discografia_raw_$(SNAPSHOT).jsonl" \
		python code/run_lyrics.py $(ARGS) --snapshot $(SNAPSHOT); \
	elif [ -f code/lyrics_pipeline.py ]; then \
		echo "[lyrics] rodando code/lyrics_pipeline.py …"; \
		OUTPUT_JSONL="data/raw/funk_br_discografia_raw_$(SNAPSHOT).jsonl" \
		python code/lyrics_pipeline.py $(ARGS) --snapshot $(SNAPSHOT); \
	else \
		echo "[lyrics] nenhum script encontrado (code/run_lyrics.py ou code/lyrics_pipeline.py)."; \
		exit 2; \
	fi
.PHONY: process
process: ## processamento + sanity
	@set -e; set -a; [ -f .env ] && . ./.env; set +a; \
	if grep -q '^sanity:' Makefile; then \
		echo "[process] chamando sanity …"; \
		$(MAKE) sanity; \
	else \
		echo "[process] alvo sanity não encontrado no Makefile."; \
		exit 2; \
	fi
