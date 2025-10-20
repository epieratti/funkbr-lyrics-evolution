#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

fail=0
pass(){ printf "✅ %s\n" "$*"; }
warn(){ printf "⚠️  %s\n" "$*"; }
die(){  printf "❌ %s\n" "$*"; fail=$((fail+1)); }

# carregar .env
[ -f .env ] && set -a && . ./.env && set +a
: "${MARKET:=BR}"

echo "== Verificando secrets do Spotify =="
if [[ -z "${SPOTIPY_CLIENT_ID:-}" || -z "${SPOTIPY_CLIENT_SECRET:-}" ]]; then
  die "SPOTIPY_CLIENT_ID/SECRET ausentes (.env)."
else
  pass "SPOTIPY_CLIENT_ID/SECRET encontrados."
fi
[[ -n "${SPOTIFY_REFRESH_TOKEN:-}" ]] && pass "REFRESH_TOKEN presente (escopos de usuário prontos)." || warn "Sem REFRESH_TOKEN (modo client credentials)."

echo "== Checando dependências Python =="
if ./venv/bin/python - <<'PY' 2>/dev/null
import spotipy
print("spotipy import OK")
PY
then pass "spotipy import OK"
else die "spotipy ausente. Rode: source venv/bin/activate && pip install spotipy"
fi

echo "== Testando token client_credentials =="
if out=$(curl -sS -X POST "https://accounts.spotify.com/api/token" \
  -u "${SPOTIPY_CLIENT_ID}:${SPOTIPY_CLIENT_SECRET}" \
  -d grant_type=client_credentials); then
  tok=$(printf '%s' "$out" | grep -o '"access_token":"[^"]*"' | cut -d':' -f2- | tr -d '"')
  if [[ -n "$tok" ]]; then
    pass "Token obtido."
    # ping simples numa API pública
    code=$(curl -sS -o /dev/null -w "%{http_code}" -H "Authorization: Bearer $tok" \
      "https://api.spotify.com/v1/search?q=Anitta&type=artist&market=${MARKET}&limit=1")
    [[ "$code" == "200" ]] && pass "API v1 OK (search 200)" || die "API search falhou (HTTP $code)"
  else
    die "Falha ao obter token (sem access_token)."
  fi
else
  die "Falha HTTP na obtenção do token."
fi

echo "== Verificando hook anti-JSONL vazio =="
if ./venv/bin/python - <<'PY'
import os, usercustomize
p="data/raw/_spotify_check.jsonl"
open(p,"w").close()
ok1 = not os.path.exists(p)
with open(p,"w") as f: f.write('{"ok":true}\\n')
ok2 = os.path.getsize(p) > 0
print("ok", ok1 and ok2)
PY
then pass "Hook usercustomize ativo."
else die "Hook usercustomize com problema."
fi

echo "== Sanidade de diretórios =="
mkdir -p data/raw reports/sanity logs /mnt/backup/raw /mnt/backup/processed
pass "Estrutura garantida."

[[ $fail -eq 0 ]] && { echo "✓ Checklist Spotify READY"; exit 0; } || { echo "✗ Checklist encontrou $fail problema(s)"; exit 1; }
