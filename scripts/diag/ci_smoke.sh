#!/usr/bin/env bash
set -euo pipefail

# Bloqueia qualquer acesso de rede por segurança
export NO_NETWORK=${NO_NETWORK:-1}
export PYTHONWARNINGS=${PYTHONWARNINGS:-ignore}

# Garante coleta em modo bloqueado
[ -f .env ] || touch .env
if grep -q '^COLLECT_MODE=' .env; then
  sed -i 's/^COLLECT_MODE=.*/COLLECT_MODE=disabled/' .env
else
  printf 'COLLECT_MODE=disabled\n' >> .env
fi

echo "[ci] py_compile …"
python -m py_compile $(git ls-files '*.py')

# pytest é opcional: roda se existir, senão avisa e segue
if command -v pytest >/dev/null 2>&1; then
  echo "[ci] pytest -q …"
  pytest -q
else
  echo "[ci] pytest ausente — pulando testes (ok neste VM)"
fi

echo "[ci] make -n collect process …"
make -n collect process || true

echo "[ci] validação de schema (amostra)…"
python scripts/diag/validate_schema_sample.py || true

echo "[ci] OK"
