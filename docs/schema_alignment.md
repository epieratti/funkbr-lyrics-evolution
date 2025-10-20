## Alinhamento de schema com corpus atual

Este PR tem escopo limitado ao alinhamento entre o `schema.json` e os campos efetivamente emitidos pelo corpus processado.  

### Incluído
- Atualização de `schema.json` com colunas reais (campos obrigatórios e opcionais).
- Adição de `scripts/diag/validate_schema_sample.py` para validação de amostras.
- Alvo opcional `make sanity_schema` no Makefile.
- Documentação mínima sobre processo de alinhamento.

### Não incluído
- Nenhuma mudança em collectors, backup ou cron jobs.
- Nenhum impacto operacional em produção.

### Motivação
Evitar que pipelines que validam contra schema quebrem ao consumir novos snapshots, garantindo consistência de dados e capacidade de validação manual antes de publicações.
