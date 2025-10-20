# Samples (sanitizados)

Este diretório contém **recortes mínimos e sanitizados** (até 200 linhas) de
metadados do corpus (`samples/metadata/*.sample.jsonl`) e de logs
(`samples/logs/*.sample.log`) para onboarding, sem IDs sensíveis.

## Como atualizar os samples
Execute:
    samples/scripts/make_sample.sh

## Critérios de sanitização
- Limite de linhas: **200** por arquivo.
- Logs: apenas **linhas não vazias**.
- Corpus: somente JSONL final consolidado de `processed_brcorpus/`.
- Nada de tokens/segredos: `.env`, `rclone.conf` etc. **nunca** entram aqui.
