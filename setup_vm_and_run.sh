#!/usr/bin/env bash
set -euo pipefail

# =========[ CONFIG ]=========
PROJECT_DIR="${PROJECT_DIR:-$HOME/funkbr-lyrics-evolution}"
VENV_DIR="${VENV_DIR:-$PROJECT_DIR/venv}"
PYBIN="${PYBIN:-$VENV_DIR/bin/python}"
PIPBIN="${PIPBIN:-$VENV_DIR/bin/pip}"
MAKEBIN="${MAKEBIN:-/usr/bin/make}"
SWAPFILE="${SWAPFILE:-/swapfile}"
SWAP_SIZE_GB="${SWAP_SIZE_GB:-4}"
LOGROTATE_FILE="/etc/logrotate.d/funkbr"
LOCK_SCRIPT="$PROJECT_DIR/scripts/with_lock.sh"
CRON_TMP="$(mktemp)"
# ============================

say() { echo -e "\033[1;32m[setup]\033[0m $*"; }
warn() { echo -e "\033[1;33m[warn]\033[0m  $*"; }
err() { echo -e "\033[1;31m[err]\033[0m   $*"; }

require_root() {
  if [[ "$(id -u)" -ne 0 ]]; then
    err "rode como root (sudo)."
    exit 1
  fi
}

ensure_dirs() {
  say "criando estrutura de pastas…"
  mkdir -p "$PROJECT_DIR"
  mkdir -p "$PROJECT_DIR"/{data/{raw,clean,sample,enriched,processed},reports/{figures,tables,sanity},logs,docs/anexos/incidents,manifests,scripts,code/utils}
}

ensure_swap() {
  if ! swapon --show | grep -q "$SWAPFILE"; then
    say "ativando swap ${SWAP_SIZE_GB}G em $SWAPFILE…"
    fallocate -l "${SWAP_SIZE_GB}G" "$SWAPFILE" || dd if=/dev/zero of="$SWAPFILE" bs=1G count="$SWAP_SIZE_GB"
    chmod 600 "$SWAPFILE"
    mkswap "$SWAPFILE"
    swapon "$SWAPFILE"
    if ! grep -qF "$SWAPFILE none swap sw 0 0" /etc/fstab; then
      echo "$SWAPFILE none swap sw 0 0" >> /etc/fstab
    fi
  else
    say "swap já ativo."
  fi
}

ensure_venv() {
  if [[ ! -d "$VENV_DIR" ]]; then
    say "criando venv em $VENV_DIR…"
    python3 -m venv "$VENV_DIR"
  fi
  # ativa venv nesta shell
  # shellcheck disable=SC1091
  source "$VENV_DIR/bin/activate"
  "$PIPBIN" install -U pip
  if [[ -f "$PROJECT_DIR/requirements.txt" ]]; then
    say "instalando requirements.txt…"
    "$PIPBIN" install -r "$PROJECT_DIR/requirements.txt"
  fi
  say "instalando spaCy PT…"
  "$PYBIN" -m spacy download pt_core_news_sm || true
}

ensure_env() {
  if [[ ! -f "$PROJECT_DIR/.env" ]]; then
    warn "faltando $PROJECT_DIR/.env — crie e preencha suas chaves (Spotify/Discogs/Genius)."
  else
    say ".env presente."
  fi
}

install_lock_script() {
  if [[ ! -x "$LOCK_SCRIPT" ]]; then
    say "instalando script de lock…"
    cat > "$LOCK_SCRIPT" << 'SH'
#!/usr/bin/env bash
set -euo pipefail
LOCK="${1:-/tmp/funkbr.lock}"; shift || true
exec 9>"$LOCK"
flock -n 9 || { echo "[lock] em execução, saindo"; exit 0; }
"$@"
SH
    chmod +x "$LOCK_SCRIPT"
  fi
}

install_usercustomize() {
  local UFILE="$PROJECT_DIR/usercustomize.py"
  say "configurando usercustomize.py anti-.jsonl vazio…"
  cat > "$UFILE" << 'PY'
import os, tempfile, builtins
_ORIG_OPEN = builtins.open
class _AtomicJsonlWriter:
    def __init__(self, path, *_, **__):
        self._path = path; self._buf = []
    def __enter__(self):
        class _W:
            def __init__(self,o): self._o=o
            def write(self,s): self._o._buf.append(s); return len(s)
            def flush(self): pass
        return _W(self)
    def __exit__(self, exc_type, exc, tb):
        if exc_type: return False
        data = "".join(self._buf)
        if not data.strip(): return False
        d = os.path.dirname(self._path) or "."
        os.makedirs(d, exist_ok=True)
        fd, tmp = tempfile.mkstemp(prefix=".tmp_", dir=d, suffix=".jsonl")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(data)
        os.replace(tmp, self._path)
        return False
def _open_wrapper(file, mode="r", *args, **kwargs):
    try:
        if isinstance(file, str) and file.endswith(".jsonl") and (("w" in mode) or ("x" in mode)):
            return _AtomicJsonlWriter(file, *args, **kwargs)
    except Exception:
        pass
    return _ORIG_OPEN(file, mode, *args, **kwargs)
builtins.open = _open_wrapper
PY
}

install_sanity_script() {
  local SFILE="$PROJECT_DIR/code/sanity_dashboard.py"
  say "instalando sanity_dashboard.py…"
  cat > "$SFILE" << 'PY'
import os, glob, csv, time, statistics as st, argparse
p=argparse.ArgumentParser(); p.add_argument("--out", default="reports/sanity"); a=p.parse_args()
os.makedirs(a.out, exist_ok=True)
rows=[]; sizes=[]; today=time.strftime("%Y%m%d")
for fn in sorted(glob.glob("data/raw/*")):
    sz=os.path.getsize(fn); m=time.strftime("%F %T", time.localtime(os.path.getmtime(fn)))
    rows.append({"arquivo":os.path.basename(fn),"bytes":sz,"data_mod":m,"hoje":"SIM" if today in fn else "NAO"})
    if today in fn and fn.endswith(".jsonl"): sizes.append(sz)
out=os.path.join(a.out,"sanity_min_raw.csv")
with open(out,"w",newline="") as f:
    w=csv.DictWriter(f,fieldnames=["arquivo","bytes","data_mod","hoje"]); w.writeheader(); w.writerows(rows)
open(os.path.join(a.out,"README.txt"),"w").write(
    f"jsonl_hoje={len(sizes)}, zerados={sum(1 for s in sizes if s==0)}, media_bytes={round(st.mean(sizes),1) if sizes else 0}\n"
)
print("ok:", out)
PY
}

install_logrotate() {
  say "configurando logrotate em $LOGROTATE_FILE…"
  cat > "$LOGROTATE_FILE" <<EOF
$PROJECT_DIR/logs/*.log {
  weekly
  rotate 8
  compress
  missingok
  notifempty
  copytruncate
}
EOF
  logrotate -d /etc/logrotate.conf >/dev/null || true
}

install_cron_jobs() {
  say "configurando crons com lock…"
  crontab -l 2>/dev/null | sed "/funkbr-lyrics-evolution/d" | sed "/scripts\/with_lock\.sh/d" > "$CRON_TMP" || true
  {
    echo "0 2 * * * cd $PROJECT_DIR && $LOCK_SCRIPT /tmp/funkbr_collect.lock $MAKEBIN collect >> logs/collect_\$(date +\%F).log 2>&1"
    echo "0 4 * * * cd $PROJECT_DIR && $LOCK_SCRIPT /tmp/funkbr_lyrics.lock  $MAKEBIN lyrics  >> logs/lyrics_\$(date +\%F).log 2>&1"
    echo "0 6 * * * cd $PROJECT_DIR && $LOCK_SCRIPT /tmp/funkbr_process.lock $MAKEBIN process sanity >> logs/process_\$(date +\%F).log 2>&1"
    echo "30 1 * * * rsync -a --delete $PROJECT_DIR/data/raw/ $PROJECT_DIR/../mnt/backup/raw/ 2>/dev/null || rsync -a --delete $PROJECT_DIR/data/raw/ /mnt/backup/raw/"
    echo "30 3 * * 1 rsync -a --delete $PROJECT_DIR/data/processed/ $PROJECT_DIR/../mnt/backup/processed/ 2>/dev/null || rsync -a --delete $PROJECT_DIR/data/processed/ /mnt/backup/processed/"
  } >> "$CRON_TMP"
  crontab "$CRON_TMP"
  rm -f "$CRON_TMP"
  say "crontab instalado:"
  crontab -l
}

run_make_targets() {
  # ativa venv nesta shell
  # shellcheck disable=SC1091
  source "$VENV_DIR/bin/activate"
  if [[ -f "$PROJECT_DIR/Makefile" ]]; then
    say "rodando make setup (idempotente)…"
    (cd "$PROJECT_DIR" && $MAKEBIN setup || true)
  fi
  say "sanity mínimo…"
  (cd "$PROJECT_DIR" && $PYBIN code/sanity_dashboard.py --out reports/sanity || true)
}

final_checks() {
  say "checando usercustomize…"
  "$PYBIN" - <<'PY'
import usercustomize, os
print("usercustomize:", usercustomize.__file__)
# teste rápido anti-vazio
p1="data/raw/_test_empty.jsonl"; 
try:
    with open(p1,"w") as f: pass
except Exception as e:
    print("erro:", e)
print("criou_vazio?", os.path.exists(p1))
p2="data/raw/_test_nonempty.jsonl"
with open(p2,"w") as f: f.write('{"ok":true}\\n')
print("nonempty_size:", os.path.getsize(p2))
PY
  say "logrotate (debug)…"
  logrotate -d /etc/logrotate.conf | tail -n 10 || true
}

main() {
  require_root
  ensure_dirs
  ensure_swap
  ensure_venv
  ensure_env
  install_lock_script
  install_usercustomize
  install_sanity_script
  install_logrotate
  install_cron_jobs
  run_make_targets
  final_checks
  say "✔ pronto! pipeline agendado (02h/04h/06h), backups (01h30/seg 03h30), logs rotacionando e JSONL blindado."
}

main "$@"
