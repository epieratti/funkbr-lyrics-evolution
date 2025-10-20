import os, sys, re
from urllib.parse import urlparse, parse_qs
from dotenv import load_dotenv
import spotipy
from spotipy.oauth2 import SpotifyOAuth

load_dotenv()
cid  = os.getenv("SPOTIFY_CLIENT_ID") or os.getenv("SPOTIPY_CLIENT_ID")
csec = os.getenv("SPOTIFY_CLIENT_SECRET") or os.getenv("SPOTIPY_CLIENT_SECRET")
if not cid or not csec:
    print("Faltam SPOTIFY_CLIENT_ID/SECRET no .env", file=sys.stderr)
    sys.exit(1)

scopes = sys.argv[1] if len(sys.argv) > 1 else "user-library-read,user-read-email,user-read-private"
redirect_uri = "http://127.0.0.1:8080/callback"

oauth = SpotifyOAuth(
    client_id=cid,
    client_secret=csec,
    redirect_uri=redirect_uri,
    scope=scopes,
    open_browser=False,   # não tenta abrir browser na VM
    cache_path=None
)

auth_url = oauth.get_authorize_url()
print("\nAbra esta URL no seu navegador, faça login e autorize o app:\n")
print(auth_url, "\n")
redir = input("Cole aqui a URL COMPLETA de redirecionamento (que começa com http://127.0.0.1:8080/callback?...):\n").strip()

# extrai o ?code=...
code = parse_qs(urlparse(redir).query).get("code", [None])[0]
if not code:
    print("Não achei o parâmetro 'code' na URL colada.", file=sys.stderr)
    sys.exit(2)

# troca pelo token
tok = oauth.get_access_token(code, as_dict=True)
if not tok or "refresh_token" not in tok:
    print("Não recebi refresh_token do Spotify.", file=sys.stderr)
    sys.exit(3)

rt = tok["refresh_token"]
print("\nACCESS TOKEN (curto prazo):", tok.get("access_token","<oculto>")[:20]+"...")
print("REFRESH TOKEN (longo prazo):", rt)

# persiste no .env (idempotente)
envp = ".env"
try:
    if os.path.exists(envp):
        with open(envp, "r", encoding="utf-8") as f:
            lines = f.read().splitlines()
    else:
        lines = []
    wrote = False
    for i, line in enumerate(lines):
        if line.startswith("SPOTIFY_REFRESH_TOKEN="):
            lines[i] = f"SPOTIFY_REFRESH_TOKEN={rt}"
            wrote = True
            break
    if not wrote:
        lines.append(f"SPOTIFY_REFRESH_TOKEN={rt}")
    with open(envp, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"\n✓ Gravado no {envp}: SPOTIFY_REFRESH_TOKEN=... (oculto)")
except Exception as e:
    print(f"Aviso: não consegui gravar no {envp}: {e}", file=sys.stderr)
    print("Copie manualmente o refresh token acima para o .env.")

print("\nPronto! Você já pode usar endpoints que exigem usuário.")
