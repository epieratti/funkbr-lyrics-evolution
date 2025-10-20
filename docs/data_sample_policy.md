# Política de Amostragem de Dados (samples/)
Esta amostra serve **exclusivamente** para onboarding e testes rápidos.

## Conteúdo
- `samples/metadata/`: subconjunto dos JSONL consolidados públicos do projeto.
- `samples/logs/`: log sintético/minimizado sem dados sensíveis.

## Sanitização
- Remoção de identificadores sensíveis de faixas/álbuns/ISRC/UPC.
- Campos permitidos: `artist_name`, `track_name`, `market`, `pt_hint`,
  `seed_match`, `accept_in_brcorpus`, e metadados agregados não sensíveis.
- Campos removidos: `artist_id`, `album_id`, `track_id`, `isrc`, `album_upc`,
  e quaisquer outros IDs/códigos proprietários.

## Tamanho-alvo
- Até ~200 linhas por arquivo de amostra.

## Limitações
- A amostra não substitui o conjunto completo de dados.
- Logs são demonstrativos e podem não refletir 100% do ambiente real.
