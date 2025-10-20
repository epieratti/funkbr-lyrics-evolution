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


validate_schema = load_module("funkbr_validate_schema", "code/validate_schema.py")


def build_record(**overrides):
    base = {
        "artist_id": "artist123",
        "artist_query": "artist",
        "track_id": "track123",
        "track_name": "Song Name",
        "market": "BR",
        "ts": 1729551000,
        "available_markets": ["BR", "US"],
        "n_markets": 2,
        "available_in_BR": True,
    }
    base.update(overrides)
    return base


def test_schema_validation_passes(tmp_path: Path) -> None:
    record = build_record()
    sample = tmp_path / "valid.jsonl"
    sample.write_text(json.dumps(record) + "\n", encoding="utf-8")

    errors = validate_schema.validate_records(Path("schema.json"), sample)
    assert errors == []


def test_schema_validation_reports_missing_fields(tmp_path: Path) -> None:
    record = build_record()
    record.pop("track_name")
    sample = tmp_path / "invalid.jsonl"
    sample.write_text(json.dumps(record) + "\n", encoding="utf-8")

    errors = validate_schema.validate_records(Path("schema.json"), sample)
    assert errors, "expected validation errors for missing track_name"
    assert any("track_name" in message for message in errors)
