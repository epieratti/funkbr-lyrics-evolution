#!/usr/bin/env bash
set -euo pipefail
FILE="${1:?informe o caminho do snapshot}"
DRIVE_PATH="${2:-}"  # ex.: gdrive:Backups/funkbr-lyrics-evolution/arquivo.jsonl
SHA="$(sha256sum "$FILE" | awk '{print $1}')"
{
  echo "- Snapshot: $FILE"
  echo "  - SHA256: $SHA"
  [[ -n "$DRIVE_PATH" ]] && echo "  - Drive:  $DRIVE_PATH"
  echo
} >> CHANGELOG.md
echo "[OK] Registrado no CHANGELOG: $FILE"
