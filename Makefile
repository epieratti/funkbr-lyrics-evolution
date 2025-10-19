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
