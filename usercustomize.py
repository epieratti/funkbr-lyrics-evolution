import os, tempfile, builtins

_ORIG_OPEN = builtins.open  # guarda o open original

class _AtomicJsonlWriter:
    """Bufferiza writes e só cria/substitui o .jsonl se algo não-vazio foi escrito."""
    def __init__(self, path, *_, **__):
        self._path = path
        self._buf = []
        self._closed = False

    # API de arquivo
    def write(self, s):
        if self._closed:
            raise ValueError("I/O operation on closed file")
        # aceita bytes ou str (normalmente será str)
        if isinstance(s, (bytes, bytearray)):
            s = s.decode("utf-8", errors="replace")
        self._buf.append(s)
        return len(s)

    def writelines(self, lines):
        for line in lines:
            self.write(line)

    def flush(self):
        # nada a fazer — é tudo em memória até o close/__exit__
        pass

    def close(self):
        if self._closed:
            return
        self._closed = True
        data = "".join(self._buf)
        # não cria/promove arquivo se só houver whitespace (ou nada)
        if not data.strip():
            return
        d = os.path.dirname(self._path) or "."
        os.makedirs(d, exist_ok=True)
        fd, tmp = tempfile.mkstemp(prefix=".tmp_", dir=d, suffix=".jsonl")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(data)
            os.replace(tmp, self._path)
        finally:
            # se algo deu ruim antes do replace, tenta limpar tmp
            try:
                if os.path.exists(tmp):
                    os.remove(tmp)
            except Exception:
                pass

    # Context manager
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc, tb):
        if exc_type:
            # erro no bloco => não criar/promover
            self._closed = True
            return False
        self.close()
        return False

def _open_wrapper(file, mode="r", *args, **kwargs):
    # Intercepta somente criação de .jsonl com 'w' ou 'x'
    try:
        if (
            isinstance(file, str)
            and file.endswith(".jsonl")
            and (("w" in mode) or ("x" in mode))
        ):
            return _AtomicJsonlWriter(file, *args, **kwargs)
    except Exception:
        pass
    return _ORIG_OPEN(file, mode, *args, **kwargs)

# Monkeypatch GLOBAL
builtins.open = _open_wrapper
