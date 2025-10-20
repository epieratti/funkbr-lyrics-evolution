"""Generate mock sanity summaries from JSONL fixtures without touching real data."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Iterable, Iterator


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Emit sanity reports based on synthetic inputs")
    parser.add_argument(
        "--input",
        default="tests/fixtures/schema_sample_valid.jsonl",
        help="Path to JSONL fixture (safe to miss)",
    )
    parser.add_argument(
        "--output-dir",
        default="tmp",
        help="Directory to store generated reports",
    )
    return parser.parse_args(argv)


def _load_jsonl(path: Path) -> Iterator[dict]:
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)


def _status_bucket(record: dict) -> str:
    available = record.get("available_in_BR")
    if available is True:
        return "2xx"
    if available is False:
        return "4xx"
    return "5xx"


def _year_bucket(record: dict) -> str:
    ts = record.get("ts")
    if isinstance(ts, (int, float)):
        try:
            return str(datetime.utcfromtimestamp(ts).year)
        except (OverflowError, OSError, ValueError):
            return "unknown"
    return "unknown"


def _market_bucket(record: dict) -> str:
    market = record.get("market")
    if isinstance(market, str) and market:
        return market
    markets = record.get("available_markets")
    if isinstance(markets, list) and markets:
        candidate = markets[0]
        if isinstance(candidate, str) and candidate:
            return candidate
    return "unknown"


def _write_csv(path: Path, rows: list[tuple[str, str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["metric", "bucket", "value"])
        for metric, bucket, value in rows:
            writer.writerow([metric, bucket, value])


def _empty_reports(output_dir: Path) -> tuple[Path, Path]:
    csv_path = output_dir / "sanity_report.csv"
    json_path = output_dir / "sanity_report.json"
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_csv(csv_path, [])
    json_path.write_text(
        json.dumps(
            {"records": 0, "status_ratio": {}, "coverage": {"year": {}, "market": {}}},
            indent=2,
        ),
        encoding="utf-8",
    )
    return csv_path, json_path


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)
    input_path = Path(args.input)
    output_dir = Path(args.output_dir)

    if not input_path.exists():
        csv_path, json_path = _empty_reports(output_dir)
        print(
            f"[dry-run] fixture ausente: {input_path}; relatórios vazios em {csv_path} e {json_path}"
        )
        return 0

    records = list(_load_jsonl(input_path))
    if not records:
        csv_path, json_path = _empty_reports(output_dir)
        print(
            f"[dry-run] fixture sem registros: {input_path}; relatórios vazios em {csv_path} e {json_path}"
        )
        return 0

    total = len(records)
    status_counts = Counter(_status_bucket(record) for record in records)
    year_counts = Counter(_year_bucket(record) for record in records)
    market_counts = Counter(_market_bucket(record) for record in records)

    status_ratio = {
        bucket: status_counts.get(bucket, 0) / total for bucket in ("2xx", "4xx", "5xx")
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / "sanity_report.csv"
    json_path = output_dir / "sanity_report.json"

    csv_rows: list[tuple[str, str, str]] = [("records", "total", str(total))]
    for bucket, ratio in status_ratio.items():
        csv_rows.append(("status_ratio", bucket, f"{ratio:.3f}"))
    for year, count in sorted(year_counts.items()):
        csv_rows.append(("coverage_year", year, str(count)))
    for market, count in sorted(market_counts.items()):
        csv_rows.append(("coverage_market", market, str(count)))

    _write_csv(csv_path, csv_rows)

    summary = {
        "records": total,
        "status_ratio": status_ratio,
        "coverage": {
            "year": dict(sorted(year_counts.items())),
            "market": dict(sorted(market_counts.items())),
        },
    }
    json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(f"✓ sanity reports gravados em {csv_path} e {json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
