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
