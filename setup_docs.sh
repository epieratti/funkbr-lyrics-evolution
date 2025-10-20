#!/usr/bin/env bash
set -euo pipefail
PROJECT_ROOT="${1:-$PWD}"
cd "$PROJECT_ROOT"
mkdir -p docs reports/health

# corrigir citação do README se existir
if [[ -f README.md ]]; then
  sed -i 's#github\.com/seuusuario/funkbr-lyrics-evolution#github.com/epieratti/funkbr-lyrics-evolution#g' README.md || true
fi

echo "Governança criada/atualizada. Arquivos em $(pwd)."
