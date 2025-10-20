.PHONY: setup pilot_100 collect sanity clean

PY=python3
CODE=code
SEED=data/seed/seed_artists.txt
SEED_DIR=data/seed
OUT=data/raw
LOG_DIR=logs
DATE:=$(shell date +%Y%m%d_%H%M%S)

# ---------------------------------------------------------------------
# Setup inicial do ambiente
# ---------------------------------------------------------------------
setup:
	@echo "Instalando dependências e preparando diretórios..."
	mkdir -p $(OUT) $(LOG_DIR)
	$(PY) -m pip install -U pip
	@if [ -f requirements.txt ]; then \
		echo "Instalando libs do requirements.txt..."; \
		$(PY) -m pip install -r requirements.txt; \
	else \
		echo "Nenhum requirements.txt encontrado (ok)."; \
	fi
	@echo "Ambiente pronto."

# ---------------------------------------------------------------------
# Piloto rápido - testa 100 artistas (seed_artists.txt)
# ---------------------------------------------------------------------
pilot_100:
	@echo "Rodando piloto (100 artistas de $(SEED))..."
	mkdir -p $(OUT) $(LOG_DIR)
	SEED_FILE=$(SEED) \
	OUTPUT_JSONL=$(OUT)/raw_$(DATE)_pilot.jsonl \
	OUTPUT_CSV=$(OUT)/raw_$(DATE)_pilot.csv \
	LOG_FILE=$(LOG_DIR)/collect_$(DATE)_pilot.log \
	PROGRESS_FILE=$(OUT)/progress_pilot.json \
	YEAR_START=2005 YEAR_END=2025 MARKET=BR \
	FLUSH_EVERY_N_ROWS=200 \
	$(PY) $(CODE)/coletar_discografia_funk_br.py || \
	( echo "❌ Erro no piloto. Veja logs em $(LOG_DIR)/collect_$(DATE)_pilot.log"; exit 1 )

# ---------------------------------------------------------------------
# Coleta completa - percorre todos os seed_part_*.txt (1–12)
# ---------------------------------------------------------------------
collect:
	@echo "Rodando coleta completa (arquivos: $(SEED_DIR)/seed_part_1.txt ... seed_part_12.txt)..."
	mkdir -p $(OUT) $(LOG_DIR)
	cat $(SEED_DIR)/seed_part_*.txt > $(SEED_DIR)/all_seeds.txt
	SEED_FILE=$(SEED_DIR)/all_seeds.txt \
	OUTPUT_JSONL=$(OUT)/raw_$(DATE).jsonl \
	OUTPUT_CSV=$(OUT)/raw_$(DATE).csv \
	LOG_FILE=$(LOG_DIR)/collect_$(DATE).log \
	PROGRESS_FILE=$(OUT)/progress.json \
	YEAR_START=2005 YEAR_END=2025 MARKET=BR \
	FLUSH_EVERY_N_ROWS=500 \
	$(PY) $(CODE)/coletar_discografia_funk_br.py || \
	( echo "❌ Erro na coleta. Veja logs em $(LOG_DIR)/collect_$(DATE).log"; exit 1 )

# ---------------------------------------------------------------------
# Sanidade básica - conta arquivos brutos coletados
# ---------------------------------------------------------------------
sanity:
	@echo "Contando arquivos brutos em $(OUT)..."
	@find $(OUT) -type f -name '*.jsonl' | wc -l
	@echo "Linhas em CSVs gerados:"
	@ls -1t $(OUT)/*.csv 2>/dev/null | head -n1 | xargs -I{} bash -c 'echo {}; wc -l {}'

# ---------------------------------------------------------------------
# Limpeza de logs e temporários
# ---------------------------------------------------------------------
clean:
	@echo "Removendo arquivos temporários e logs..."
	rm -rf $(LOG_DIR)/*.log $(OUT)/*.jsonl $(OUT)/*.csv $(OUT)/*.json
	@echo "Limpeza concluída."
# --- FUNK: deduplicação do último enriched gerado ---
.PHONY: dedupe_latest
dedupe_latest:
	@echo "Deduplicando o arquivo enriched mais recente em data/raw/..."
	@python code/dedupe_albums_tracks.py
	@echo
	@ls -1t data/raw/*_dedup.csv | head -n1 | xargs -I{} sh -c 'echo "Saída: {}"; wc -l {};'

# --- FUNK: coleta completa de um artista (álbuns + faixas) ---
.PHONY: one_artist_full
one_artist_full:
	@if [ -z "$(ARTIST_NAME)" ]; then \
		echo "❌ Uso: make one_artist_full ARTIST_NAME=\"Anitta\""; \
		exit 1; \
	fi
	@echo "🎧 Coletando álbuns e faixas de: $(ARTIST_NAME)"
	@TS=$$(date +%Y%m%d_%H%M%S); \
	SAFE=$$(printf "%s" "$(ARTIST_NAME)" | tr ' /' '__'); \
	OUTJ="data/raw/one_$${TS}_$${SAFE}_albums_tracks.jsonl"; \
	OUTC="data/raw/one_$${TS}_$${SAFE}_albums_tracks.csv"; \
	LOGF="logs/collect_$${TS}_$${SAFE}.log"; \
	YEAR_START=2005 YEAR_END=2025 MARKET=BR FLUSH_EVERY_N_ROWS=50; \
	PYTHONUNBUFFERED=1 OUTPUT_JSONL=$$OUTJ OUTPUT_CSV=$$OUTC LOG_FILE=$$LOGF \
	YEAR_START=$$YEAR_START YEAR_END=$$YEAR_END MARKET=$$MARKET ARTIST_NAME="$(ARTIST_NAME)" \
	python code/run_one_artist_full.py | tee -a $$LOGF; \
	echo; echo "✅ Gerados:"; ls -lh $$OUTC $$OUTJ

# --- FUNK: enriquecer último CSV com ISRC e track_popularity ---
.PHONY: enrich_latest
enrich_latest:
	@echo "✨ Enriquecendo o último *_albums_tracks.csv em data/raw/..."
	@python code/enrich_latest.py
	@echo
	@ls -1t data/raw/*_enriched.csv | head -n1 | xargs -I{} sh -c 'echo "Saída: {}"; wc -l {};'

# --- FUNK: deduplicação do último enriched gerado ---
.PHONY: dedupe_latest
dedupe_latest:
	@echo "🔍 Deduplicando o arquivo enriched mais recente em data/raw/..."
	@python code/dedupe_albums_tracks.py
	@echo
	@ls -1t data/raw/*_dedup.csv | head -n1 | xargs -I{} sh -c 'echo "Saída: {}"; wc -l {};'
# === FUNK targets (sem TAB; usa '>' como prefixo de receita) ===
.RECIPEPREFIX := >

.PHONY: one_artist_full
one_artist_full:
> if [ -z "$(ARTIST_NAME)" ]; then \
>   echo "❌ Uso: make one_artist_full ARTIST_NAME=\"Anitta\""; \
>   exit 1; \
> fi
> echo "🎧 Coletando álbuns e faixas de: $(ARTIST_NAME)"
> TS=$$(date +%Y%m%d_%H%M%S); \
> SAFE=$$(printf "%s" "$(ARTIST_NAME)" | tr ' /' '__'); \
> OUTJ="data/raw/one_$${TS}_$${SAFE}_albums_tracks.jsonl"; \
> OUTC="data/raw/one_$${TS}_$${SAFE}_albums_tracks.csv"; \
> LOGF="logs/collect_$${TS}_$${SAFE}.log"; \
> YEAR_START=2005 YEAR_END=2025 MARKET=BR FLUSH_EVERY_N_ROWS=50; \
> PYTHONUNBUFFERED=1 OUTPUT_JSONL=$$OUTJ OUTPUT_CSV=$$OUTC LOG_FILE=$$LOGF \
> YEAR_START=$$YEAR_START YEAR_END=$$YEAR_END MARKET=$$MARKET ARTIST_NAME="$(ARTIST_NAME)" \
> python code/run_one_artist_full.py | tee -a $$LOGF; \
> echo; echo "✅ Gerados:"; ls -lh $$OUTC $$OUTJ

.PHONY: enrich_latest
enrich_latest:
> echo "✨ Enriquecendo o último *_albums_tracks.csv em data/raw/..."
> python code/enrich_latest.py
> echo
> ls -1t data/raw/*_enriched.csv | head -n1 | xargs -I{} sh -c 'echo "Saída: {}"; wc -l {};'

.PHONY: dedupe_latest
dedupe_latest:
> echo "🔍 Deduplicando o arquivo enriched mais recente em data/raw/..."
> python code/dedupe_albums_tracks.py
> echo
> ls -1t data/raw/*_dedup.csv | head -n1 | xargs -I{} sh -c 'echo "Saída: {}"; wc -l {};'
