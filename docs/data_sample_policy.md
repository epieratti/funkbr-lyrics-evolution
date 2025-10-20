# Política de Amostragem de Dados (Samples)

## Objetivo
Disponibilizar um **conjunto mínimo, seguro e representativo** para onboarding,
sem expor dados sensíveis ou volumes que onerem o repositório.

## Escopo
- **Inclui**:
  - Recorte de metadados do corpus final (JSONL) em `processed_brcorpus/` (até 200 linhas).
  - Recorte de **logs textuais** (até 200 linhas; sem linhas vazias).
- **Exclui**:
  - Dados brutos de coletas (`data/raw`, `data/snapshots`).
  - Tokens/segredos (`.env`, credenciais, chaves API).
  - Dumps completos e arquivos grandes.

## Processo (automático)
Gerado por `samples/scripts/make_sample.sh`:
1. Para cada `processed_brcorpus/brcorpus_*.jsonl`: `head -n 200` → `samples/metadata/*.sample.jsonl`
2. Para cada `logs/*.log`: remove linhas vazias e `head -n 200` → `samples/logs/*.sample.log`

## Boas práticas
- Commits de sample devem acompanhar **mudanças de formato de saída**.
- Nunca colocar dados PII, segredos, ou links diretos a credenciais.
