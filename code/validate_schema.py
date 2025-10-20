"""Schema validation CLI for JSONL catalogs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable, Iterator, List, Tuple

try:
    from jsonschema import Draft202012Validator, exceptions as jsonschema_exceptions
except ImportError:  # pragma: no cover - lightweight fallback

    class _SimpleValidationError(Exception):
        def __init__(self, message: str) -> None:
            super().__init__(message)
            self.message = message

    class _SimpleValidator:
        def __init__(self, schema: dict) -> None:
            self.schema = schema

        def iter_errors(self, instance: dict):
            if not isinstance(instance, dict):
                yield _SimpleValidationError("instance is not an object")
                return

            required = self.schema.get("required", [])
            for key in required:
                if key not in instance:
                    yield _SimpleValidationError(f"'{key}' is a required property")

            additional = self.schema.get("additionalProperties", True)
            properties = self.schema.get("properties", {})
            if not additional:
                for key in instance.keys():
                    if key not in properties:
                        yield _SimpleValidationError(f"Additional property '{key}' is not allowed")

            for key, definition in properties.items():
                if key not in instance:
                    continue
                value = instance[key]
                allowed_types = definition.get("type")
                if allowed_types is None:
                    continue
                if not isinstance(allowed_types, list):
                    allowed_types = [allowed_types]

                if not any(_matches_type(value, t, definition) for t in allowed_types):
                    yield _SimpleValidationError(f"'{key}' is not of type {allowed_types}")

    class _DummyExceptions:
        SchemaError = ValueError

    def _matches_type(value: object, expected: str, definition: dict) -> bool:
        if expected == "string":
            return isinstance(value, str)
        if expected == "integer":
            if not isinstance(value, int) or isinstance(value, bool):
                return False
            minimum = definition.get("minimum")
            maximum = definition.get("maximum")
            if minimum is not None and value < minimum:
                return False
            if maximum is not None and value > maximum:
                return False
            return True
        if expected == "boolean":
            return isinstance(value, bool)
        if expected == "array":
            if not isinstance(value, list):
                return False
            item_def = definition.get("items")
            if not item_def:
                return True
            item_type = item_def.get("type")
            if item_type:
                return all(_matches_type(item, item_type, item_def) for item in value)
            return True
        if expected == "null":
            return value is None
        if expected == "object":
            return isinstance(value, dict)
        return True

    Draft202012Validator = _SimpleValidator  # type: ignore[assignment]
    jsonschema_exceptions = _DummyExceptions()  # type: ignore[assignment]


def load_jsonl(path: Path) -> Iterator[Tuple[int, dict]]:
    with path.open(encoding="utf-8") as handle:
        for idx, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                yield idx, json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid JSON on line {idx}: {exc}") from exc


def validate_records(schema_path: Path, jsonl_path: Path) -> List[str]:
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    errors: List[str] = []
    for line_no, record in load_jsonl(jsonl_path):
        for error in validator.iter_errors(record):
            errors.append(f"line {line_no}: {error.message}")
    return errors


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate JSONL records against a JSON Schema")
    parser.add_argument("--schema", required=True, help="Path to JSON schema")
    parser.add_argument("--jsonl", required=True, help="Path to JSONL file to validate")
    parser.add_argument("--fail-fast", action="store_true", help="Stop on first validation error")
    return parser.parse_args(argv)


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)
    schema_path = Path(args.schema)
    jsonl_path = Path(args.jsonl)

    if not schema_path.exists():
        print(f"❌ schema file not found: {schema_path}")
        return 2
    if not jsonl_path.exists():
        print(f"❌ jsonl file not found: {jsonl_path}")
        return 3

    try:
        errors = validate_records(schema_path, jsonl_path)
    except (ValueError, jsonschema_exceptions.SchemaError) as exc:
        print(f"❌ validation aborted: {exc}")
        return 4

    if errors:
        for message in errors:
            print(f"❌ {message}")
            if args.fail_fast:
                break
        return 5

    print("✓ schema validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
