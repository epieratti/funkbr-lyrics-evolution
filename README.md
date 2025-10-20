# FunkBR-Lyrics-Evolution

**Longitudinal corpus and analysis of Brazilian funk lyrics (2005–2025)**  
Measuring lexical and syntactic change in verbs of command, agency, and everyday narratives.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11%2B-blue.svg)]()
[![Reproducible](https://img.shields.io/badge/Reproducibility-100%25-green.svg)]()
[![Data Ethics](https://img.shields.io/badge/Data%20Policy-Aggregated%20only-orange.svg)]()

---

## Descrição
Pipeline científico e reprodutível para coleta, processamento e análise lexical das letras de funk brasileiro (2005–2025).  
Inclui módulos para coleta via Spotify, Discogs, Genius e Vagalume, amostragem estratificada, tokenização com spaCy e modelagem estatística (GLM binomial negativa e detecção de rupturas temporais).

---

## Estrutura
```
code/                 # scripts Python (coleta, limpeza, modelagem, visualização)
data/                 # diretórios locais (raw, clean, sample, enriched, processed)
docs/                 # protocolo e anexos (metodologia, ADRs, incident logs)
.env.example          # modelo de credenciais de API (não versionar .env real)
Makefile              # comandos principais para operação e reprodutibilidade
```

---

## Quickstart
```bash
# 1. Instalar dependências e modelo NLP
make setup

# 2. Rodar piloto com 100 artistas
make pilot_100

# 3. Iniciar coleta integral
make collect

# 4. Conferir painel de sanidade
make sanity
```

---

## Licença
- Código: MIT License (`LICENSE`)  
- Dados derivados: Creative Commons BY-NC (`DATA_LICENSE`)  
- Letras integrais: não redistribuídas (uso apenas interno para análise)

---

## Citação
Se utilizar este repositório em pesquisa, cite como:

```
Pieratti, E. (2025). FunkBR-Lyrics-Evolution: Longitudinal analysis of Brazilian funk lyrics (2005–2025). GitHub repository. https://github.com/epieratti/funkbr-lyrics-evolution
```

---

## Contato
Para dúvidas ou colaborações: epieratti@gmail.com

---

## Observações
- `.env` não deve ser versionado.  
- Logs e snapshots brutos são datados e salvos localmente.  
- Projeto modular e compatível com execução em VM (Ubuntu + Docker + cron).  
- Mais detalhes em `docs/protocolo.md`.

---

© 2025 Enrico Pieratti — Projeto FunkBR-Lyrics-Evolution
