import os, tempfile, builtins

class _AtomicJsonlWriter:
    def __init__(self, path, *_, **__):
        self._path = path
        self._buf = []

    def __enter__(self):
        class _Writer:
            def __init__(self, outer): self._o = outer
            def write(self, s): 
                self._o._buf.append(s)
                return len(s)
            def flush(self): pass
        return _Writer(self)

    def __exit__(self, exc_type, exc, tb):
        # Não cria arquivo se der exceção no bloco original
        if exc_type:
            return False
        data = "".join(self._buf)
        if not data.strip():
            # buffer vazio → não grava nada (evita .jsonl de 0 bytes)
            return False
        d = os.path.dirname(self._path) or "."
        os.makedirs(d, exist_ok=True)
        fd, tmp = tempfile.mkstemp(prefix=".tmp_", dir=d, suffix=".jsonl")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(data)
        os.replace(tmp, self._path)
        return False  # propaga comportamento normal

# Monkeypatch só para escrita de .jsonl
_open = builtins.open
def open(file, mode="r", *args, **kwargs):
    if isinstance(file, str) and file.endswith(".jsonl") and "w" in mode:
        return _AtomicJsonlWriter(file, *args, **kwargs)
    return _open(file, mode, *args, **kwargs)
