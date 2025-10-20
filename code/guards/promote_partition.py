"""Dry-run guard to validate JSONL partitions before promotion.

Default execution validates JSONL files under --src using code/validate_schema.py,
produces a SHA256 manifest, and skips copying unless --confirm is supplied.
Designed to operate with fixtures in tmp/ and never touch real data.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Iterable, List


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate and (optionally) promote JSONL partitions"
    )
    parser.add_argument(
        "--schema", default="schema.json", help="Path to JSON schema for validation"
    )
    parser.add_argument(
        "--src", default="tmp/promote/src", help="Source directory with JSONL files"
    )
    parser.add_argument(
        "--dst", default="tmp/promote/dst", help="Destination directory for promotion"
    )
    parser.add_argument(
        "--manifest",
        default="tmp/promote_manifest.json",
        help="Path to write checksum manifest",
    )
    parser.add_argument(
        "--confirm", action="store_true", help="Copy files to --dst after validation"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Force dry-run even if --confirm is provided",
    )
    return parser.parse_args(argv)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _collect_jsonl(path: Path) -> List[Path]:
    return sorted(p for p in path.glob("*.jsonl") if p.is_file())


def _validate_file(schema: Path, file_path: Path) -> tuple[int, str]:
    validator = Path("code") / "validate_schema.py"
    cmd = [
        sys.executable,
        str(validator),
        "--schema",
        str(schema),
        "--jsonl",
        str(file_path),
        "--fail-fast",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    output = "\n".join(part for part in (proc.stdout.strip(), proc.stderr.strip()) if part)
    return proc.returncode, output


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)
    schema_path = Path(args.schema)
    src_dir = Path(args.src)
    dst_dir = Path(args.dst)
    manifest_path = Path(args.manifest)

    dry_run = not args.confirm or args.dry_run

    if not schema_path.exists():
        print(f"❌ schema file not found: {schema_path}")
        return 2

    src_dir.mkdir(parents=True, exist_ok=True)
    jsonl_files = _collect_jsonl(src_dir)

    if not jsonl_files:
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps({"files": []}, indent=2), encoding="utf-8")
        print("[dry-run] nenhum JSONL encontrado; manifesto vazio gerado")
        return 0

    validation_errors: List[str] = []
    for file_path in jsonl_files:
        code, message = _validate_file(schema_path, file_path)
        if code != 0:
            if message:
                validation_errors.append(f"{file_path}: {message}")
            else:
                validation_errors.append(f"{file_path}: validation returned code {code}")

    if validation_errors:
        for line in validation_errors:
            print(f"❌ {line}")
        return 3

    entries = []
    for file_path in jsonl_files:
        entries.append(
            {
                "file": str(file_path.resolve()),
                "sha256": _sha256(file_path),
                "size_bytes": file_path.stat().st_size,
            }
        )

    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps({"files": entries}, indent=2), encoding="utf-8")

    if dry_run:
        print("[dry-run] validação concluída; promoção não executada")
        return 0

    dst_dir.mkdir(parents=True, exist_ok=True)
    for file_path in jsonl_files:
        target = dst_dir / file_path.name
        shutil.copy2(file_path, target)
        print(f"[promote] copied {file_path} -> {target}")

    print(f"✓ promoção concluída; manifesto salvo em {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
