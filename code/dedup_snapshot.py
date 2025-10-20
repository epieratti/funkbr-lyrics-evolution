#!/usr/bin/env python3
import os, sys, json, re, glob, shutil, unicodedata
from argparse import ArgumentParser
from typing import Iterable, Tuple

def _strip_accents(s: str) -> str:
    return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')

def canonical(s: str) -> str:
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

def make_key(obj: dict) -> str:
    # 1) ISRC
    isrc = obj.get("isrc") or obj.get("external_ids",{}).get("isrc")
    if isrc:
        return f"isrc::{isrc}"
    # 2) artist_id + track_id
    aid = obj.get("artist_id"); tid = obj.get("track_id")
    if aid and tid:
        return f"arttrk::{aid}::{tid}"
    # 3) fallback: artista + faixa + ano (canônicos)
    aname = obj.get("artist_name") or ""
    tname = obj.get("track_name") or ""
    y = None
    for key in ("album_release_date","release_date","year_launch"):
        val = obj.get(key)
        if isinstance(val, int):
            y = val; break
        if isinstance(val, str) and len(val)>=4 and val[:4].isdigit():
            y = int(val[:4]); break
    y = y or 0
    return f"cty::{canonical(aname)}::{canonical(tname)}::{y}"

def iter_lines_jsonl(path: str) -> Iterable[Tuple[str,dict]]:
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for ln, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                yield (make_key(obj), obj)
            except Exception:
                # mantém linha bruta para não perder dado
                yield (f"raw::{ln}::{hash(line)}", {"__RAW__": line})

def write_atomic(path: str, lines):
    tmp = f"{path}.tmp"
    bak = f"{path}.bak"
    with open(tmp, "w", encoding="utf-8") as w:
        for L in lines:
            w.write(L)
            if not L.endswith("\n"):
                w.write("\n")
    if os.path.exists(path):
        shutil.copy2(path, bak)
    os.replace(tmp, path)

def dedup_file(path: str):
    seen = set()
    kept_lines = []
    total = ded = 0
    for key, obj in iter_lines_jsonl(path):
        total += 1
        if key in seen:
            ded += 1
            continue
        seen.add(key)
        if "__RAW__" in obj:
            kept_lines.append(obj["__RAW__"])
        else:
            kept_lines.append(json.dumps(obj, ensure_ascii=False))
    write_atomic(path, kept_lines)
    return total, len(kept_lines), ded

def main():
    ap = ArgumentParser()
    ap.add_argument("--path", default="data/raw", help="Pasta base com JSONL")
    ap.add_argument("--pattern", default="*.jsonl", help="Glob dos arquivos")
    ap.add_argument("--scope", choices=("file","global"), default="file",
                    help="file: dedup por arquivo; global: dedup entre todos (mantém 1ª ocorrência)")
    args = ap.parse_args()

    pattern = os.path.join(args.path, args.pattern)
    files = sorted(glob.glob(pattern))
    if not files:
        print(f"[dedup] nenhum arquivo encontrado em {pattern}", file=sys.stderr)
        sys.exit(0)

    print(f"[dedup] iniciando: {len(files)} arquivo(s) | base={args.path} | pattern={args.pattern} | scope={args.scope}")
    grand_total = kept_total = dedup_total = 0

    if args.scope == "file":
        # dedup isolado por arquivo
        for fp in files:
            t, k, d = dedup_file(fp)
            grand_total += t; kept_total += k; dedup_total += d
            pct = (d / t * 100.0) if t else 0.0
            print(f"[dedup] {os.path.basename(fp)} → total={t} mantidos={k} descartados={d} ({pct:.1f}%)")
    else:
        # dedup global entre arquivos (ordem lexicográfica dos nomes)
        seen_global = set()
        for fp in files:
            kept_lines = []
            total = ded = 0
            for key, obj in iter_lines_jsonl(fp):
                total += 1
                if key in seen_global:
                    ded += 1
                    continue
                seen_global.add(key)
                if "__RAW__" in obj:
                    kept_lines.append(obj["__RAW__"])
                else:
                    kept_lines.append(json.dumps(obj, ensure_ascii=False))
            write_atomic(fp, kept_lines)
            grand_total += total; kept_total += len(kept_lines); dedup_total += ded
            pct = (ded / total * 100.0) if total else 0.0
            print(f"[dedup][global] {os.path.basename(fp)} → total={total} mantidos={len(kept_lines)} descartados={ded} ({pct:.1f}%)")

    gpct = (dedup_total / grand_total * 100.0) if grand_total else 0.0
    print(f"[dedup] resumo | arquivos={len(files)} total={grand_total} mantidos={kept_total} descartados={dedup_total} ({gpct:.1f}%)")

if __name__ == "__main__":
    main()
