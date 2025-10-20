import re, sys, pathlib, json
p = pathlib.Path("code/coletar_discografia_funk_br.py")
s = p.read_text(encoding="utf-8")

# Idempotência: se já tem Verbose, não aplica de novo
if re.search(r'\bclass\s+Verbose\b', s):
    print("Patch já aplicado (classe Verbose encontrada). Saindo.")
    sys.exit(0)

# 1) IMPORTS (garante presença, injeta se faltar)
need_imports = [
    "import argparse",
    "import json",
    "import os",
    "import sys",
    "from datetime import datetime",
    "from pathlib import Path",
]
head = s
for imp in need_imports:
    if imp not in head:
        # insere logo após a primeira linha de imports existentes
        m = re.search(r'^(?:from\s+\S+\s+import\s+.*|import\s+.*)(?:\r?\n)+', head, flags=re.M)
        if m:
            idx = m.end()
            head = head[:idx] + imp + "\n" + head[idx:]
        else:
            head = imp + "\n" + head

s = head

# 2) Utilitários Verbose/Progress (injeta antes do if __main__)
utils_block = r'''
def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

class Verbose:
    def __init__(self, enabled: bool = True, level: int = 1, log_file: str | None = None):
        self.enabled = enabled
        self.level = level
        self.log_file = log_file
        self._fh = open(log_file, "a", encoding="utf-8") if log_file else None
        if self._fh:
            self._fh.write(f"[{_now()}] :: verbose start level={level}\n")
            self._fh.flush()

    def close(self):
        if self._fh:
            self._fh.close()

    def _write(self, line: str):
        print(line, flush=True)
        if self._fh:
            self._fh.write(line + "\n")
            self._fh.flush()

    def v(self, line: str, min_level: int = 1):
        if self.enabled and self.level >= min_level:
            self._write(line)

class ProgressRecorder:
    def __init__(self, path: str = "logs/collector_progress.json"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def save(self, **kwargs):
        data = {}
        if self.path.exists():
            try:
                data = json.loads(self.path.read_text(encoding="utf-8"))
            except Exception:
                data = {}
        data.update(kwargs)
        self.path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def load(self) -> dict:
        if self.path.exists():
            try:
                return json.loads(self.path.read_text(encoding="utf-8"))
            except Exception:
                return {}
        return {}
'''

if re.search(r'if\s+__name__\s*==\s*[\'"]__main__[\'"]\s*:', s):
    s = re.sub(r'(if\s+__name__\s*==\s*[\'"]__main__[\'"]\s*:)', utils_block + r'\n\1', s, count=1)
else:
    s += "\n\n" + utils_block + "\n"

# 3) Parser + main (se não existir, cria bloco completo; se existir, ajusta)
parser_sig = r'def\s+_build_parser\s*\('
main_sig   = r'def\s+main\s*\('

need_parser = not re.search(parser_sig, s)
need_main   = not re.search(main_sig, s)

parser_block = r'''
def _build_parser():
    p = argparse.ArgumentParser(description="Coleta discografia de artistas BR (Spotify).")
    p.add_argument("--snapshot", type=str, default=None, help="Rótulo do snapshot AAAAMMDD.")
    p.add_argument("--limit_artists", type=int, default=None, help="Limite de artistas para esta corrida.")
    p.add_argument("--offset_artists", type=int, default=0, help="Offset da lista de artistas.")
    p.add_argument("--resume", action="store_true", help="Tenta retomar a partir do progresso salvo.")
    p.add_argument("--quiet", action="store_true", help="Silencia prints no terminal.")
    p.add_argument("--verbose-level", type=int, default=1, choices=[1,2], help="1 contagens, 2 detalha faixas.")
    p.add_argument("--log-file", type=str, default=None, help="Também escreve as mensagens nesse arquivo.")
    p.add_argument("--progress-file", type=str, default="logs/collector_progress.json", help="JSON de progresso.")
    return p
'''

main_block = r'''
def main():
    parser = _build_parser()
    args = parser.parse_args()

    verbose = Verbose(enabled=not args.quiet, level=args.verbose_level, log_file=args.log_file)
    progress = ProgressRecorder(args.progress_file)

    try:
        snapshot = args.snapshot or datetime.now().strftime("%Y%m%d")
        verbose.v(f"→ início {_now()} snapshot {snapshot}")

        # As funções abaixo devem existir no seu script original:
        artists = load_seed_artists()
        total = len(artists)

        start_idx = args.offset_artists
        if args.resume:
            prev = progress.load()
            if "artist_index" in prev:
                start_idx = max(start_idx, int(prev["artist_index"]))
                verbose.v(f"→ retomando a partir do artista {start_idx+1}/{total}")

        end_idx = (min(start_idx + args.limit_artists, total)
                   if args.limit_artists is not None else total)

        for i in range(start_idx, end_idx):
            artist = artists[i]
            artist_name = artist.get("name") if isinstance(artist, dict) else str(artist)

            progress.save(stage="artist", artist_index=i, artist_total=total, artist_name=artist_name, snapshot=snapshot)
            verbose.v(f"→ artista {i+1}/{total} {artist_name}")

            progress.save(stage="albums")
            albums = fetch_albums_for_artist(artist)
            verbose.v(f"   ↳ álbuns encontrados {len(albums)}")

            tracks_total = 0
            new_tracks_total = 0

            for a_idx, album in enumerate(albums, start=1):
                album_name = album.get("name")
                progress.save(stage="tracks", album_name=album_name, album_index=a_idx, album_total=len(albums))

                tracks = fetch_tracks_for_album(album)
                tracks_total += len(tracks)

                new_tracks = persist_tracks_if_new(tracks, snapshot=snapshot)
                new_tracks_total += new_tracks

                verbose.v(f"   ↳ álbum {a_idx}/{len(albums)} {album_name} faixas {len(tracks)} novas {new_tracks}", min_level=1)

                if verbose.level >= 2:
                    for t in tracks:
                        verbose.v(f"      • {t.get('track_name')} [{t.get('track_id')}]")

            verbose.v(f"   ↳ total de faixas {tracks_total} novas {new_tracks_total}")

        verbose.v("✓ coleta finalizada")
        progress.save(stage="done", finished_at=_now())

    except Exception as e:
        progress.save(stage="error", error=str(e), when=_now())
        verbose.v(f"✗ erro: {e}")
        raise
    finally:
        verbose.close()
'''

if need_parser:
    s += "\n" + parser_block + "\n"
if need_main:
    s += "\n" + main_block + "\n"

# 4) Garante o guard __main__
if not re.search(r'if\s+__name__\s*==\s*[\'"]__main__[\'"]\s*:', s):
    s += "\nif __name__ == '__main__':\n    main()\n"

p.write_text(s, encoding="utf-8")
print("Patch aplicado com sucesso.")
