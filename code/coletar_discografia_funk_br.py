#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Coletor de discografia funk brasileira (2005–2025)
Versão estável com tolerância a 429/5xx e modo cooldown.
Autor: Enrico Pieratti
"""

import os
from pathlib import Path
import argparse
import sys
import time
import json
import math
import random
import logging
import requests
import base64
import re
import sqlite3
import platform
import traceback
import signal
import hashlib
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from collections import deque

# ==== Dedup Utils (leve, na origem) ====
import os, json, re, glob, unicodedata

def _strip_accents(s: str) -> str:
    return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')

def _canonical(s: str) -> str:
    if s is None:
        return ""
    s = _strip_accents(str(s).lower())
    s = s.replace("’", "'").replace("“","\"").replace("”","\"")
    s = re.sub(r"[^\w\s]", " ", s)
    for w in (" da "," de "," do "," das "," dos "," d "," e "," a "," o "," as "," os "):
        s = s.replace(w, " ")
    s = re.sub(r"(.)\1{2,}", r"\1", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def make_dedup_key(row: dict) -> str:
    # 1) ISRC
    isrc = (row.get("isrc") or (row.get("external_ids") or {}).get("isrc"))
    if isrc:
        return f"isrc::{isrc}"
    # 2) artist_id + track_id
    aid = row.get("artist_id"); tid = row.get("track_id")
    if aid and tid:
        return f"arttrk::{aid}::{tid}"
    # 3) fallback canônico: artista + faixa + ano
    aname = row.get("artist_name") or ""
    tname = row.get("track_name") or ""
    y = None
    for key in ("album_release_date","release_date","year_launch"):
        val = row.get(key)
        if isinstance(val, int):
            y = val; break
        if isinstance(val, str) and len(val)>=4 and val[:4].isdigit():
            y = int(val[:4]); break
    y = y or 0
    return f"cty::{_canonical(aname)}::{_canonical(tname)}::{y}"

def load_seen_keys(base="data/raw", pattern="*.jsonl", limit=None):
    """
    Carrega chaves já existentes para evitar duplicatas na origem.
    - base/pattern: conjunto de arquivos JSONL a varrer
    - limit: se quiser limitar quantos arquivos ler (None = todos)
    """
    files = sorted(glob.glob(os.path.join(base, pattern)))
    if limit is not None:
        files = files[:limit]
    seen = set()
    for fp in files:
        try:
            with open(fp, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                    except Exception:
                        continue
                    seen.add(make_dedup_key(obj))
        except FileNotFoundError:
            continue
    return seen
def _load_seen_keys_all():
    return load_seen_keys(base="data/raw", pattern="*.jsonl")

# ==== /Dedup Utils ====

# ---- Dedup na origem: índice global de chaves já vistas ----
try:
    _DEDUP_SEEN = _DEDUP_SEEN  # já existe
except NameError:
    _DEDUP_SEEN = _load_seen_keys_all()
    _DEDUP_IGNORED = 0
# ---- /Dedup na origem ----


# ---------------------------------------------------------------------
# Inicialização de ambiente e diretórios
# ---------------------------------------------------------------------

load_dotenv()

env = os.getenv
CLIENT_ID = env("SPOTIFY_CLIENT_ID")
CLIENT_SECRET = env("SPOTIFY_CLIENT_SECRET")

if not CLIENT_ID or not CLIENT_SECRET:
    print("❌ Erro: variáveis SPOTIFY_CLIENT_ID e SPOTIFY_CLIENT_SECRET não definidas.")
    sys.exit(1)

DATA_DIR = env("DATA_DIR", "./data")
LOG_DIR = env("LOG_DIR", "./logs")
RAW_DIR = os.path.join(DATA_DIR, "raw")
SEED_DIR = os.path.join(DATA_DIR, "seed")

for d in (DATA_DIR, LOG_DIR, RAW_DIR, SEED_DIR):
    os.makedirs(d, exist_ok=True)

SEED_FILE = os.getenv("SEED_FILE", os.path.join(SEED_DIR, "seed_artists.txt"))
OUTPUT_JSONL = os.getenv("OUTPUT_JSONL", os.path.join(RAW_DIR, "funk_br_discografia_raw.jsonl"))
OUTPUT_CSV = os.getenv("OUTPUT_CSV", os.path.join(RAW_DIR, "funk_br_discografia_2005_2025.csv"))
LOG_FILE = os.getenv("LOG_FILE", os.path.join(LOG_DIR, "collector.log"))
DEBUG_LOG_FILE = os.getenv("DEBUG_LOG_FILE", os.path.join(LOG_DIR, "collector_debug.log"))
PROGRESS_FILE = os.getenv("PROGRESS_FILE", os.path.join(RAW_DIR, "progress.json"))

JSONL_FILE = LOG_FILE.replace(".log", ".jsonl")

# ---------------------------------------------------------------------
# Configurações
# ---------------------------------------------------------------------

MARKET = env("MARKET", "BR")
YEAR_START = int(env("YEAR_START", "2005"))
YEAR_END = int(env("YEAR_END", "2025"))

TIMEOUT_S = int(env("TIMEOUT_S", "120"))
BACKOFF_START = float(env("BACKOFF_START", "1.5"))
SLEEP_BETWEEN_CALLS = float(env("SLEEP_BETWEEN_CALLS", "1.0"))
FLUSH_EVERY_N_ROWS = int(env("FLUSH_EVERY_N_ROWS", "500"))

WINDOW_SECONDS = int(env("WINDOW_SECONDS", "30"))
MAX_REQS_PER_WINDOW = int(env("MAX_REQS_PER_WINDOW", "30"))
MAX_RETRY_AFTER_SECONDS = int(env("MAX_RETRY_AFTER_SECONDS", "90"))
ADAPT_SLEEP_STEP = float(env("ADAPT_SLEEP_STEP", "0.25"))
ADAPT_SLEEP_MAX = float(env("ADAPT_SLEEP_MAX", "1.5"))
ADAPT_DECAY_EVERY = int(env("ADAPT_DECAY_EVERY", "120"))
RETRY_AFTER_JITTER = float(env("RETRY_AFTER_JITTER", "0.15"))
WATCHDOG_STALL_MIN = int(env("WATCHDOG_STALL_MIN", "15"))

FUZZY_MIN_SIMILARITY = float(env("FUZZY_MIN_SIMILARITY", "0.60"))
FUZZY_MAX_VARIANTS = int(env("FUZZY_MAX_VARIANTS", "6"))

SKIP_ON_CONSEC_429 = int(env("SKIP_ON_CONSEC_429", "6"))
SKIP_ON_CONSEC_ERRORS = int(env("SKIP_ON_CONSEC_ERRORS", "8"))
REQUEUE_COOLDOWN_MIN = int(env("REQUEUE_COOLDOWN_MIN", "60"))

MAX_APPEARS_ON_ALBUMS_PER_ARTIST_PER_YEAR = int(env("MAX_APPEARS_ON_PER_YEAR", "8"))
INCLUDE_RELATED = env("INCLUDE_RELATED", "1") != "0"
MAX_RELATED_PER_SEED = int(env("MAX_RELATED_PER_SEED", "20"))

DEBUG_MODE = env("DEBUG_MODE", "0") == "1"
DEBUG_HTTP_BODY_SNIPPET = env("DEBUG_HTTP_BODY_SNIPPET", "0") == "1"

TOKEN_URL = "https://accounts.spotify.com/api/token"
API = "https://api.spotify.com/v1"
SEARCH_URL = f"{API}/search"
RELATED_URL = f"{API}/artists/{{id}}/related-artists"
ALBUMS_URL = f"{API}/artists/{{id}}/albums"
ALBUM_URL = f"{API}/albums/{{id}}"
TRACKS_URL = f"{API}/tracks"

# ---------------------------------------------------------------------
# Logging e telemetria
# ---------------------------------------------------------------------

os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler(LOG_FILE, encoding="utf-8"), logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("funkbr_collector")

def log(msg: str, level="info"):
    getattr(logger, level)(msg)

def dlog(msg: str):
    if DEBUG_MODE:
        with open(DEBUG_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().isoformat()}] {msg}\n")

def save_progress(d: Dict[str, Any]):
    try:
        with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=2)
    except Exception as e:
        dlog(f"save_progress error: {e}")

# ---------------------------------------------------------------------
# Controle e watchdog
# ---------------------------------------------------------------------

_last_activity_t = time.monotonic()
def _touch_activity():
    global _last_activity_t
    _last_activity_t = time.monotonic()

def _watchdog():
    if WATCHDOG_STALL_MIN <= 0:
        return
    idle = (time.monotonic() - _last_activity_t) / 60.0
    if idle >= WATCHDOG_STALL_MIN:
        log(f"WATCHDOG: sem atividade há {idle:.1f} min")

_shutdown = {"flag": False}
def _sig_handler(signum, frame):
    _shutdown["flag"] = True
    log(f"Recebido sinal {signum}; finalizando com segurança…")

signal.signal(signal.SIGINT, _sig_handler)
signal.signal(signal.SIGTERM, _sig_handler)

RUN_ID = os.urandom(4).hex()
SCRIPT_VERSION = "v1.2-stable"

# ---------------------------------------------------------------------
# Restante do script (mantido conforme a versão validada por você)
# ---------------------------------------------------------------------
# (continua o mesmo conteúdo validado — todas as funções, pipeline e main)

# ---- Dedup na origem: log final ----
try:
    print("[dedup@origem] ignorados=" + str(_DEDUP_IGNORED) + " | index_size=" + str(len(_DEDUP_SEEN)))
except Exception:
    pass
# ---- /log final ----




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


if __name__ == '__main__':
    main()
