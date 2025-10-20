#!/usr/bin/env python3
from pathlib import Path
import shutil

TARGET = Path("code/coletar_discografia_funk_br.py")
BACKUP = TARGET.with_suffix(".py.bak_textpatch")

UTILS_MARK = "==== Dedup Utils (leve, na origem) ===="
UTILS_BLOCK = """# ==== Dedup Utils (leve, na origem) ====
import os, json, re as _re_dedup, glob, unicodedata

def _strip_accents(s: str) -> str:
    return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')

def _canonical(s: str) -> str:
    if s is None:
        return ""
    s = _strip_accents(str(s).lower())
    s = s.replace("’", "'").replace("“","\\\"").replace("”","\\\"")
    s = _re_dedup.sub(r"[^\\w\\s]", " ", s)
    for w in (" da "," de "," do "," das "," dos "," d "," e "," a "," o "," as "," os "):
        s = s.replace(w, " ")
    s = _re_dedup.sub(r"(.)\\1{2,}", r"\\1", s)
    s = _re_dedup.sub(r"\\s+", " ", s).strip()
    return s

def make_dedup_key(row: dict) -> str:
    isrc = (row.get("isrc") or (row.get("external_ids") or {}).get("isrc"))
    if isrc:
        return "isrc::" + str(isrc)
    aid = row.get("artist_id"); tid = row.get("track_id")
    if aid and tid:
        return "arttrk::" + str(aid) + "::" + str(tid)
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
    return "cty::" + _canonical(aname) + "::" + _canonical(tname) + "::" + str(y)

def _load_seen_keys_all():
    seen = set()
    for fp in sorted(glob.glob("data/raw/*.jsonl")):
        try:
            with open(fp, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line=line.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                    except Exception:
                        continue
                    seen.add(make_dedup_key(obj))
        except FileNotFoundError:
            pass
    return seen
# ==== /Dedup Utils ====
"""

INIT_BLOCK = """# ---- Dedup na origem: índice global de chaves já vistas ----
try:
    _DEDUP_SEEN = _DEDUP_SEEN  # já existe
except NameError:
    _DEDUP_SEEN = _load_seen_keys_all()
    _DEDUP_IGNORED = 0
# ---- /Dedup na origem ----
"""

PRINT_BLOCK = """# ---- Dedup na origem: log final ----
try:
    print("[dedup@origem] ignorados=" + str(_DEDUP_IGNORED) + " | index_size=" + str(len(_DEDUP_SEEN)))
except Exception:
    pass
# ---- /log final ----
"""

def find_import_block_end(lines):
    end = 0
    for i, L in enumerate(lines):
        s = L.strip()
        if s.startswith("import ") or s.startswith("from "):
            end = i+1
        elif end and s == "":
            end = i+1
        else:
            if i > 0 and not (s.startswith("import ") or s.startswith("from ")):
                break
    return end

def ensure_utils(lines):
    text = "".join(lines)
    if UTILS_MARK in text:
        return lines
    ins = find_import_block_end(lines)
    return lines[:ins] + [UTILS_BLOCK, "\n"] + lines[ins:]

def ensure_init(lines):
    text = "".join(lines)
    if "_DEDUP_SEEN" in text and "_load_seen_keys_all" in text:
        return lines
    for i, L in enumerate(lines):
        if "==== /Dedup Utils ====" in L:
            return lines[:i+1] + ["\n", INIT_BLOCK, "\n"] + lines[i+1:]
    ins = find_import_block_end(lines)
    return lines[:ins] + [INIT_BLOCK, "\n"] + lines[ins:]

def inject_guard_before_line(lines, idx):
    L = lines[idx]
    indent = L[:len(L) - len(L.lstrip())]
    rowvar = None
    if "json.dumps(" in L:
        part = L.split("json.dumps(",1)[1]
        rowvar = part.split(",",1)[0].strip()
    elif "json.dump(" in L:
        part = L.split("json.dump(",1)[1]
        rowvar = part.split(",",1)[0].strip()
    if not rowvar:
        return lines
    guard = (
        indent + "# [dedup@origem] início\n" +
        indent + "__dedup_key = make_dedup_key(" + rowvar + ")\n" +
        indent + "if __dedup_key in _DEDUP_SEEN:\n" +
        indent + "    _DEDUP_IGNORED += 1\n" +
        indent + "    continue\n" +
        indent + "_DEDUP_SEEN.add(__dedup_key)\n" +
        indent + "# [dedup@origem] fim\n"
    )
    prev = lines[idx-1] if idx>0 else ""
    if "[dedup@origem] início" in prev:
        return lines
    return lines[:idx] + [guard] + lines[idx:]

def ensure_guards(lines):
    new = lines[:]
    i = 0
    injected = 0
    while i < len(new):
        L = new[i]
        if ("write(" in L and "json.dumps(" in L) or ("json.dump(" in L):
            before = len(new)
            new = inject_guard_before_line(new, i)
            injected += (1 if len(new) > before else 0)
            i += 1
        else:
            i += 1
    print("[textpatch] guards inseridos:", injected)
    return new

def ensure_print_block(lines):
    if "[dedup@origem] ignorados=" in "".join(lines):
        return lines
    for i, L in enumerate(lines):
        if L.strip().startswith("if __name__ == '__main__':"):
            return lines[:i] + ["\n", PRINT_BLOCK, "\n"] + lines[i:]
    return lines + ["\n", PRINT_BLOCK, "\n"]

def main():
    if not TARGET.exists():
        print("[textpatch] arquivo não encontrado:", TARGET)
        raise SystemExit(1)
    src = TARGET.read_text(encoding="utf-8", errors="ignore")
    shutil.copy2(TARGET, BACKUP)
    lines = src.splitlines(keepends=True)

    lines = ensure_utils(lines)
    lines = ensure_init(lines)
    lines = ensure_guards(lines)
    lines = ensure_print_block(lines)

    TARGET.write_text("".join(lines), encoding="utf-8")
    print("[textpatch] pronto. backup:", BACKUP)

if __name__ == "__main__":
    main()
