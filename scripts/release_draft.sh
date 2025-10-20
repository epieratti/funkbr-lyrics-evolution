#!/usr/bin/env bash
set -euo pipefail

VERSION="${VERSION:-${1:-}}"
if [[ -z "${VERSION}" ]]; then
  echo "Uso: VERSION=vX.Y.Z $0  (ou)  $0 vX.Y.Z" >&2
  exit 1
fi

NOTES="RELEASE_NOTES_${VERSION}_draft.md"
if [[ ! -f "$NOTES" ]]; then
  echo "Arquivo $NOTES não encontrado." >&2
  exit 1
fi

echo "== Criando/atualizando release ${VERSION} no GitHub =="
if gh release view "${VERSION}" >/dev/null 2>&1; then
  gh release edit "${VERSION}" --draft --title "${VERSION} — em desenvolvimento" --notes-file "${NOTES}"
else
  gh release create "${VERSION}" --draft --title "${VERSION} — em desenvolvimento" --notes-file "${NOTES}"
fi

echo "== Selecionando artefatos recentes =="
RAW_LATEST=$(ls -t data/raw/*.jsonl 2>/dev/null | head -n 3 || true)
SANITY_LATEST=$(ls -t reports/sanity/*.csv 2>/dev/null | head -n 3 || true)
SNAP=$(date +%Y%m%d_%H%M)
TMP=$(mktemp -d)

if [[ -n "${RAW_LATEST}${SANITY_LATEST}" ]]; then
  echo "Staging em ${TMP} (prefixo: ${SNAP}_)"
  for f in ${RAW_LATEST} ${SANITY_LATEST}; do
    [[ -f "$f" ]] || continue
    cp "$f" "${TMP}/${SNAP}_$(basename "$f")"
  done

  if compgen -G "${TMP}/*" >/dev/null; then
    echo "== Enviando assets prefixados =="
    gh release upload "${VERSION}" "${TMP}"/* --clobber
  else
    echo "(nenhum arquivo para anexar)"
  fi
else
  echo "(nenhum .jsonl/.csv recente encontrado)"
fi

rm -rf "${TMP}"

URL=$(gh release view "${VERSION}" --json url -q .url || true)
echo "✓ Release draft atualizada: ${VERSION}"
[[ -n "$URL" ]] && echo "URL: $URL"
