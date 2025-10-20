import os, json, tempfile

def write_jsonl_atomic(dest: str, rows):
    """Escreve JSONL de forma atômica e só promove se tiver conteúdo."""
    d = os.path.dirname(dest) or "."
    os.makedirs(d, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".tmp_", dir=d, suffix=".jsonl")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            n = 0
            for r in rows or []:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
                n += 1
        if os.path.getsize(tmp) > 0:
            os.replace(tmp, dest)
            return n
        else:
            os.remove(tmp)
            return 0
    except Exception:
        try: os.remove(tmp)
        except Exception: pass
        raise
