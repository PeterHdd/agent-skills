#!/usr/bin/env python3
"""Summarize experiment metrics from JSON or CSV files."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


def rows_from_json(path: Path) -> list[dict[str, str]]:
    data = json.loads(path.read_text())
    if not isinstance(data, dict):
        raise ValueError("JSON root must be an object")
    row = {"run": str(data.get("run", path.stem))}
    for key, value in data.items():
        if isinstance(value, (int, float, str)):
            row[key] = str(value)
    return [row]


def rows_from_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    for index, row in enumerate(rows, start=1):
        row.setdefault("run", f"{path.stem}-{index}")
    return rows


def rows_from_text(path: Path) -> list[dict[str, str]]:
    text = path.read_text()
    stripped = text.lstrip()
    if stripped.startswith("{"):
        return rows_from_json(path)
    return rows_from_csv(path)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Summarize evaluation metrics from JSON or CSV files."
    )
    parser.add_argument("paths", nargs="+", help="Metric files (.json or .csv)")
    parser.add_argument("--metric", action="append", default=[], help="Metric key/column to include")
    args = parser.parse_args()

    rows: list[dict[str, str]] = []
    for raw_path in args.paths:
        path = Path(raw_path).resolve()
        if not path.exists():
            parser.error(f"path does not exist: {path}")
        if path.suffix.lower() == ".json":
            rows.extend(rows_from_json(path))
        elif path.suffix.lower() == ".csv":
            rows.extend(rows_from_csv(path))
        else:
            rows.extend(rows_from_text(path))

    metrics = args.metric or sorted({key for row in rows for key in row if key != "run"})
    print("## Evaluation Summary")
    print("")
    print("| " + " | ".join(["run"] + metrics) + " |")
    print("|" + "|".join(["---"] * (len(metrics) + 1)) + "|")
    for row in rows:
        values = [row.get("run", "unknown")] + [row.get(metric, "") for metric in metrics]
        print("| " + " | ".join(values) + " |")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
