from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


def load_module(module_name: str, relative_path: str):
    base = Path(__file__).resolve().parent.parent
    module_path = base / relative_path
    if str(module_path.parent) not in sys.path:
        sys.path.insert(0, str(module_path.parent))
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


collect_module = load_module("funkbr_collect_spotify", "code/collect_spotify_catalog.py")


def test_atomic_append_jsonl_appends_in_order(tmp_path: Path) -> None:
    target = tmp_path / "sample.jsonl"

    collect_module.atomic_append_jsonl(target, {"id": 1, "value": "first"})
    collect_module.atomic_append_jsonl(target, {"id": 2, "value": "second"})

    lines = target.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0])["value"] == "first"
    assert json.loads(lines[1])["id"] == 2
