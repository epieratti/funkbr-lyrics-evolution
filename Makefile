# FunkBR – Makefile oficial (v1.1)
# ------------------------------------------------------
# Targets principais de coleta e processamento
# Compatível com Python 3.11+, Docker e cron

.PHONY: setup pilot pilot_100 collect validate sample lyrics process model report sanity publish clean

# ------------------------------------------------------
# Setup inicial: instala dependências e modelo spaCy
setup:              ## instala dependências, baixa modelo NLP e valida ambiente
	python -m pip install -U pip
	pip install -r requirements.txt
	python -m spacy download pt_core_news_sm

# ------------------------------------------------------
# Pilotos
pilot:              ## piloto completo com 1000 artistas (valida pipeline inteiro)
	python code/coletar_discografia_funk_br.py --limit_artists 1000 --snapshot $$(date +%Y%m%d)
	python code/process_text.py --stage pilot
	python code/metrics_model.py --stage pilot
	python code/visualization.py --stage pilot

pilot_100:          ## piloto rápido com 100 artistas
	python code/coletar_discografia_funk_br.py --limit_artists 100 --snapshot $$(date +%Y%m%d)

# ------------------------------------------------------
# Coleta e validação
collect:            ## coleta bruta integral (todos artistas/anos)
	python code/coletar_discografia_funk_br.py --snapshot $$(date +%Y%m%d)

validate:           ## reconcilia datas e marca flags de qualidade
	python code/reconcile_dates.py

# ------------------------------------------------------
# Amostragem e coleta de letras
sample:             ## gera amostra anual com cotas e caps
	python code/sampling_module.py --meta_faixas 350 --cap_artista 30

lyrics:             ## coleta de letras com prioridade para estratos deficitários
	python code/collect_lyrics.py --priorizar_deficit true

# ------------------------------------------------------
# Processamento e modelagem
process:            ## limpeza, tokenização e contagens
	python code/process_text.py --dedup_chorus true --unicode_nfc true

model:              ## modelagem estatística: GLM, rupturas, bootstrap, FDR
	python code/stats_model.py --bootstrap 1000 --fdr 0.05

# ------------------------------------------------------
# Relatórios e monitoramento
report:             ## gera gráficos e tabelas finais
	python code/visualization.py --export reports

sanity:             ## painel de cobertura e SLOs
	python code/sanity_dashboard.py --out reports/sanity

publish:            ## empacota artefatos derivados
	python code/publish_artifacts.py --dataset_card docs/DATASET_CARD.md

# ------------------------------------------------------
# Limpeza
clean:              ## remove caches, temporários e artefatos intermediários
	rm -rf .cache __pycache__ tmp *.log
	find data -type f -name "*.tmp" -delete
