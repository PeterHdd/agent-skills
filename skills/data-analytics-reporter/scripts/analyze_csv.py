#!/usr/bin/env python3
"""Auto-profile a CSV dataset and produce a markdown-formatted report.

Analyzes row/column counts, column types, null percentages, basic statistics
for numeric columns, and unique value counts for text columns. Uses only
Python stdlib (csv, statistics).
"""

import argparse
import csv
import json
import statistics
import sys
from collections import Counter
from datetime import datetime


# Common date formats to try when detecting date columns
DATE_FORMATS = [
    "%Y-%m-%d",
    "%Y/%m/%d",
    "%m/%d/%Y",
    "%m-%d-%Y",
    "%d/%m/%Y",
    "%d-%m-%Y",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%dT%H:%M:%S",
    "%m/%d/%Y %H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%b %d, %Y",
    "%B %d, %Y",
]


def is_numeric(value):
    """Check if a string represents a numeric value."""
    if not value or value.strip() == "":
        return False
    try:
        float(value.replace(",", ""))
        return True
    except ValueError:
        return False


def is_date(value):
    """Check if a string represents a date."""
    if not value or value.strip() == "":
        return False
    for fmt in DATE_FORMATS:
        try:
            datetime.strptime(value.strip(), fmt)
            return True
        except ValueError:
            continue
    return False


def detect_column_type(values):
    """Detect the type of a column based on its non-null values."""
    non_null = [v for v in values if v and v.strip() != ""]
    if not non_null:
        return "empty"

    # Sample up to 100 values for type detection
    sample = non_null[:100]

    numeric_count = sum(1 for v in sample if is_numeric(v))
    date_count = sum(1 for v in sample if is_date(v))

    total = len(sample)
    if numeric_count / total >= 0.8:
        return "numeric"
    if date_count / total >= 0.8:
        return "date"
    return "text"


def compute_numeric_stats(values):
    """Compute basic statistics for a list of numeric string values."""
    nums = []
    for v in values:
        if v and v.strip() != "":
            try:
                nums.append(float(v.replace(",", "")))
            except ValueError:
                continue

    if not nums:
        return {"count": 0}

    return {
        "count": len(nums),
        "min": round(min(nums), 4),
        "max": round(max(nums), 4),
        "mean": round(statistics.mean(nums), 4),
        "median": round(statistics.median(nums), 4),
        "stddev": round(statistics.stdev(nums), 4) if len(nums) > 1 else 0,
    }


def compute_text_stats(values, top_n=5):
    """Compute unique value counts for a text column."""
    non_null = [v.strip() for v in values if v and v.strip() != ""]
    if not non_null:
        return {"unique_count": 0, "top_values": []}

    counts = Counter(non_null)

    return {
        "unique_count": len(counts),
        "top_values": [
            {"value": val, "count": cnt}
            for val, cnt in counts.most_common(top_n)
        ],
    }


def profile_csv(file_path):
    """Profile a CSV file and return structured results."""
    try:
        with open(file_path, "r", newline="", encoding="utf-8") as f:
            # Sniff delimiter
            sample = f.read(8192)
            f.seek(0)
            try:
                dialect = csv.Sniffer().sniff(sample)
            except csv.Error:
                dialect = csv.excel

            reader = csv.reader(f, dialect)
            try:
                headers = next(reader)
            except StopIteration:
                return {"error": "CSV file is empty (no header row)."}

            # Read all rows into columns
            columns = {}
            for h in headers:
                columns[h] = []
            row_count = 0
            for row in reader:
                row_count += 1
                for i, h in enumerate(headers):
                    if i < len(row):
                        columns[h].append(row[i])
                    else:
                        columns[h].append("")

    except FileNotFoundError:
        return {"error": "File not found: {}".format(file_path)}
    except IOError as e:
        return {"error": "Error reading file: {}".format(e)}

    # Profile each column
    column_profiles = []
    for header in headers:
        values = columns[header]
        null_count = sum(1 for v in values if not v or v.strip() == "")
        null_pct = round((null_count / row_count) * 100, 2) if row_count > 0 else 0
        col_type = detect_column_type(values)

        profile = {
            "name": header,
            "type": col_type,
            "null_count": null_count,
            "null_pct": null_pct,
        }

        if col_type == "numeric":
            profile["stats"] = compute_numeric_stats(values)
        elif col_type == "text":
            profile["text_stats"] = compute_text_stats(values)
        elif col_type == "date":
            non_null = [v.strip() for v in values if v and v.strip() != ""]
            profile["sample_values"] = non_null[:3] if non_null else []

        column_profiles.append(profile)

    return {
        "file": file_path,
        "row_count": row_count,
        "column_count": len(headers),
        "columns": column_profiles,
    }


def format_markdown(result):
    """Format the profile result as a markdown report."""
    if "error" in result:
        return "## Error\n\n{}".format(result["error"])

    lines = [
        "# Dataset Profile Report",
        "",
        "**File:** `{}`".format(result["file"]),
        "**Rows:** {:,}".format(result["row_count"]),
        "**Columns:** {}".format(result["column_count"]),
        "",
        "## Column Summary",
        "",
        "| Column | Type | Nulls | Null % |",
        "|--------|------|------:|-------:|",
    ]

    for col in result["columns"]:
        lines.append(
            "| {} | {} | {:,} | {:.1f}% |".format(
                col["name"], col["type"], col["null_count"], col["null_pct"]
            )
        )

    # Detailed stats for numeric columns
    numeric_cols = [c for c in result["columns"] if c["type"] == "numeric" and "stats" in c]
    if numeric_cols:
        lines.extend([
            "",
            "## Numeric Column Statistics",
            "",
            "| Column | Count | Min | Max | Mean | Median | Stddev |",
            "|--------|------:|----:|----:|-----:|-------:|-------:|",
        ])
        for col in numeric_cols:
            s = col["stats"]
            lines.append(
                "| {} | {:,} | {} | {} | {} | {} | {} |".format(
                    col["name"], s["count"], s["min"], s["max"],
                    s["mean"], s["median"], s["stddev"]
                )
            )

    # Top values for text columns
    text_cols = [c for c in result["columns"] if c["type"] == "text" and "text_stats" in c]
    if text_cols:
        lines.extend([
            "",
            "## Text Column Value Counts",
            "",
        ])
        for col in text_cols:
            ts = col["text_stats"]
            lines.append("### {} ({} unique values)".format(col["name"], ts["unique_count"]))
            lines.append("")
            lines.append("| Value | Count |")
            lines.append("|-------|------:|")
            for tv in ts["top_values"]:
                lines.append("| {} | {:,} |".format(tv["value"], tv["count"]))
            lines.append("")

    # Date columns
    date_cols = [c for c in result["columns"] if c["type"] == "date"]
    if date_cols:
        lines.extend([
            "",
            "## Date Columns",
            "",
        ])
        for col in date_cols:
            samples = col.get("sample_values", [])
            sample_str = ", ".join(samples[:3]) if samples else "no samples"
            lines.append("- **{}**: {}".format(col["name"], sample_str))

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Auto-profile a CSV dataset and produce a markdown-formatted report."
    )
    parser.add_argument(
        "csv_file",
        type=str,
        help="Path to the CSV file to analyze",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="output_json",
        help="Output results as JSON instead of markdown",
    )

    args = parser.parse_args()

    result = profile_csv(args.csv_file)

    if "error" in result:
        print("Error: {}".format(result["error"]), file=sys.stderr)
        sys.exit(1)

    if args.output_json:
        print(json.dumps(result, indent=2))
    else:
        print(format_markdown(result))


if __name__ == "__main__":
    main()
