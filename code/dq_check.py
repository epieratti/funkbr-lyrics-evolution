"""Dry-run data quality checker tailored for JSONL fixtures.

The checker flags duplicates and critical nulls using samples stored under tests/fixtures
and writes summary metrics without mutating real datasets.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable, Iterator, Tuple

CRITICAL_FIELDS = ("artist_id", "track_id", "market")


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate JSONL samples for data quality issues")
    parser.add_argument(
        "--jsonl",
        default="tests/fixtures/schema_sample_valid.jsonl",
        help="Path to JSONL sample",
    )
    parser.add_argument("--out", help="Optional path to write JSON report")
    parser.add_argument(
        "--max-duplicates",
        type=int,
        default=0,
        help="Allowed duplicate count before failure",
    )
    parser.add_argument(
        "--max-null", type=int, default=0, help="Allowed null count for critical fields"
    )
    return parser.parse_args(argv)


def _load_jsonl(path: Path) -> Iterator[dict]:
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped:
                continue
            yield json.loads(stripped)


def _duration_bucket(record: dict) -> int | None:
    duration_ms = record.get("duration_ms")
    if isinstance(duration_ms, (int, float)):
        return int(round(duration_ms / 1000 / 2))
    duration = record.get("duration")
    if isinstance(duration, (int, float)):
        return int(round(duration / 2))
    return None


def _dedupe_key(record: dict) -> Tuple[str, object, object, object]:
    isrc = record.get("isrc")
    if isinstance(isrc, str) and isrc:
        return ("isrc", isrc, None, None)
    track = record.get("track_id") or record.get("track_name")
    artist = record.get("artist_id") or record.get("artist_name")
    duration_bucket = _duration_bucket(record)
    return ("composite", track, artist, duration_bucket)


def _empty_report(path: Path) -> dict:
    return {
        "file": str(path),
        "records": 0,
        "duplicates": {"total": 0, "by_key": {}},
        "null_critical": {"total": 0, "by_field": {}},
    }


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)
    jsonl_path = Path(args.jsonl)

    if not jsonl_path.exists():
        report = _empty_report(jsonl_path)
        if args.out:
            out_path = Path(args.out)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        else:
            print(json.dumps(report, indent=2))
        print("[dry-run] fixture ausente; relatório vazio emitido")
        return 0

    records = list(_load_jsonl(jsonl_path))
    if not records:
        report = _empty_report(jsonl_path)
        if args.out:
            out_path = Path(args.out)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        else:
            print(json.dumps(report, indent=2))
        print("[dry-run] arquivo sem registros; relatório vazio emitido")
        return 0

    duplicate_counter: Counter = Counter()
    null_counter: Counter = Counter()
    seen = defaultdict(list)

    for idx, record in enumerate(records, start=1):
        key = _dedupe_key(record)
        seen[key].append(idx)
        for field in CRITICAL_FIELDS:
            value = record.get(field)
            if value in (None, ""):
                null_counter[field] += 1

    for key, indices in seen.items():
        if len(indices) > 1:
            duplicate_counter[key[0]] += len(indices) - 1

    total_duplicates = sum(duplicate_counter.values())
    total_nulls = sum(null_counter.values())

    report = {
        "file": str(jsonl_path),
        "records": len(records),
        "duplicates": {
            "total": total_duplicates,
            "by_key": dict(duplicate_counter),
        },
        "null_critical": {
            "total": total_nulls,
            "by_field": dict(null_counter),
        },
    }

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    else:
        print(json.dumps(report, indent=2))

    violations = []
    if total_duplicates > args.max_duplicates:
        violations.append(f"duplicates={total_duplicates} > {args.max_duplicates}")
    if total_nulls > args.max_null:
        violations.append(f"nulls={total_nulls} > {args.max_null}")

    if violations:
        for violation in violations:
            print(f"❌ {violation}")
        return 4

    print("✓ data quality checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
