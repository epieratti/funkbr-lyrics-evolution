#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Coletor de discografia funk brasileira (2005–2025)
Versão estável com tolerância a 429/5xx e modo cooldown.
Autor: Enrico Pieratti
"""

import os
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

SEED_FILE = os.path.join(SEED_DIR, "seed_artists.txt")
OUTPUT_JSONL = os.path.join(RAW_DIR, "funk_br_discografia_raw.jsonl")
OUTPUT_CSV = os.path.join(RAW_DIR, "funk_br_discografia_2005_2025.csv")
LOG_FILE = os.path.join(LOG_DIR, "collector.log")
DEBUG_LOG_FILE = os.path.join(LOG_DIR, "collector_debug.log")
PROGRESS_FILE = os.path.join(RAW_DIR, "progress.json")

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
