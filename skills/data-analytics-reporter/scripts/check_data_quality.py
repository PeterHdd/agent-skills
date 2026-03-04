#!/usr/bin/env python3
"""Check data quality of a CSV file and report issues.

Checks for duplicate rows, columns with >50% nulls, columns with only one
unique value, potential PII columns (email, phone, SSN patterns), mixed types,
and outliers. Reports a data quality score (0-100) and specific issues found.
Uses only Python stdlib.
"""

import argparse
import csv
import json
import re
import statistics
import sys
from collections import Counter
from datetime import datetime


# Date formats for type detection
DATE_FORMATS = [
    "%Y-%m-%d",
    "%Y/%m/%d",
    "%m/%d/%Y",
    "%m-%d-%Y",
    "%d/%m/%Y",
    "%d-%m-%Y",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%dT%H:%M:%S",
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
    """Check if a string looks like a date."""
    if not value or value.strip() == "":
        return False
    for fmt in DATE_FORMATS:
        try:
            datetime.strptime(value.strip(), fmt)
            return True
        except ValueError:
            continue
    return False


def classify_value(value):
    """Classify a single non-empty value as numeric, date, or text."""
    if is_numeric(value):
        return "numeric"
    if is_date(value):
        return "date"
    return "text"


# PII detection patterns
PII_PATTERNS = {
    "email": re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"),
    "phone (US)": re.compile(r"^[\+]?1?[\s\-\.]?\(?\d{3}\)?[\s\-\.]?\d{3}[\s\-\.]?\d{4}$"),
    "SSN": re.compile(r"^\d{3}[\-\s]?\d{2}[\-\s]?\d{4}$"),
}

PII_NAME_HINTS = {
    "email": ["email", "e-mail", "email_address", "emailaddress"],
    "phone": ["phone", "telephone", "mobile", "cell", "phone_number"],
    "SSN": ["ssn", "social_security", "social_security_number"],
    "name (PII)": ["first_name", "last_name", "full_name", "firstname", "lastname"],
    "address (PII)": ["address", "street", "zip", "zipcode", "zip_code", "postal"],
}


def check_duplicates(rows):
    """Check for duplicate rows."""
    row_tuples = [tuple(row) for row in rows]
    counts = Counter(row_tuples)
    duplicates = {k: v for k, v in counts.items() if v > 1}
    total_dup_rows = sum(v - 1 for v in duplicates.values())

    return {
        "check": "duplicate_rows",
        "duplicate_groups": len(duplicates),
        "total_duplicate_rows": total_dup_rows,
        "status": "PASS" if total_dup_rows == 0 else "WARN",
        "detail": (
            "Found {} duplicate rows across {} groups".format(total_dup_rows, len(duplicates))
            if total_dup_rows > 0
            else "No duplicate rows found"
        ),
    }


def check_null_columns(headers, columns, row_count):
    """Check for columns with >50% null values."""
    high_null_cols = []
    for h in headers:
        values = columns[h]
        null_count = sum(1 for v in values if not v or v.strip() == "")
        null_pct = (null_count / row_count * 100) if row_count > 0 else 0
        if null_pct > 50:
            high_null_cols.append({
                "column": h,
                "null_pct": round(null_pct, 1),
                "null_count": null_count,
            })

    return {
        "check": "high_null_columns",
        "columns_flagged": len(high_null_cols),
        "details": high_null_cols,
        "status": "PASS" if not high_null_cols else "WARN",
        "detail": (
            "{} column(s) have >50% null values".format(len(high_null_cols))
            if high_null_cols
            else "No columns with >50% nulls"
        ),
    }


def check_mixed_types(headers, columns):
    """Check for columns with mixed data types."""
    mixed_cols = []
    for h in headers:
        values = columns[h]
        non_null = [v for v in values if v and v.strip() != ""]
        if not non_null:
            continue

        # Sample for efficiency
        sample = non_null[:500]
        types = [classify_value(v) for v in sample]
        type_counts = Counter(types)

        # If more than one type is present and the minority type is >10% of sample
        if len(type_counts) > 1:
            total = len(types)
            minority_pct = min(type_counts.values()) / total * 100
            if minority_pct > 10:
                mixed_cols.append({
                    "column": h,
                    "types_found": dict(type_counts),
                    "minority_pct": round(minority_pct, 1),
                })

    return {
        "check": "mixed_types",
        "columns_flagged": len(mixed_cols),
        "details": mixed_cols,
        "status": "PASS" if not mixed_cols else "WARN",
        "detail": (
            "{} column(s) contain mixed data types".format(len(mixed_cols))
            if mixed_cols
            else "No mixed-type columns detected"
        ),
    }


def check_outliers(headers, columns, stddev_threshold=3.0):
    """Check for outliers in numeric columns (>3 stddev from mean)."""
    outlier_cols = []
    for h in headers:
        values = columns[h]
        nums = []
        for v in values:
            if v and v.strip() != "":
                try:
                    nums.append(float(v.replace(",", "")))
                except ValueError:
                    continue

        if len(nums) < 10:
            continue

        mean = statistics.mean(nums)
        stddev = statistics.stdev(nums)
        if stddev == 0:
            continue

        outliers = [n for n in nums if abs(n - mean) > stddev_threshold * stddev]
        if outliers:
            outlier_cols.append({
                "column": h,
                "mean": round(mean, 4),
                "stddev": round(stddev, 4),
                "outlier_count": len(outliers),
                "outlier_pct": round(len(outliers) / len(nums) * 100, 2),
                "sample_outliers": [round(o, 4) for o in outliers[:5]],
            })

    return {
        "check": "outliers",
        "columns_flagged": len(outlier_cols),
        "details": outlier_cols,
        "status": "PASS" if not outlier_cols else "INFO",
        "detail": (
            "{} numeric column(s) contain outliers (>{} stddev)".format(
                len(outlier_cols), stddev_threshold
            )
            if outlier_cols
            else "No outliers detected"
        ),
    }


def check_zero_variance(headers, columns):
    """Check for columns with only one unique non-empty value."""
    zero_var = []
    for h in headers:
        values = columns[h]
        unique = set(v.strip() for v in values if v and v.strip() != "")
        if len(unique) <= 1:
            the_value = next(iter(unique)) if unique else "(all empty)"
            zero_var.append({
                "column": h,
                "constant_value": the_value,
            })

    return {
        "check": "zero_variance_columns",
        "columns_flagged": len(zero_var),
        "details": zero_var,
        "status": "PASS" if not zero_var else "WARN",
        "detail": (
            "{} column(s) have only one unique value".format(len(zero_var))
            if zero_var
            else "No zero-variance columns found"
        ),
    }


def check_pii(headers, columns):
    """Check for columns that may contain PII (email, phone, SSN)."""
    pii_findings = []

    for h in headers:
        values = columns[h]
        lower_name = h.lower().replace(" ", "_")

        # Check column name heuristics
        name_match = None
        for pii_type, hints in PII_NAME_HINTS.items():
            if lower_name in hints or any(hint in lower_name for hint in hints):
                name_match = pii_type
                break

        if name_match:
            pii_findings.append({
                "column": h,
                "pii_type": name_match,
                "method": "column name",
            })

        # Check value patterns
        non_empty = [v.strip() for v in values if v and v.strip() != ""]
        sample = non_empty[:200]
        if sample:
            for pii_type, pattern in PII_PATTERNS.items():
                matches = sum(1 for v in sample if pattern.match(v))
                if matches / len(sample) >= 0.5:
                    already = any(
                        f["column"] == h and f["pii_type"] == pii_type
                        for f in pii_findings
                    )
                    if not already:
                        pii_findings.append({
                            "column": h,
                            "pii_type": pii_type,
                            "method": "value pattern",
                        })

    return {
        "check": "potential_pii",
        "columns_flagged": len(pii_findings),
        "details": pii_findings,
        "status": "PASS" if not pii_findings else "WARN",
        "detail": (
            "{} column(s) may contain PII".format(len(pii_findings))
            if pii_findings
            else "No potential PII columns detected"
        ),
    }


def compute_quality_score(checks, row_count):
    """Compute an overall data quality score (0-100).

    Scoring:
    - Start at 100
    - Duplicate rows: -20 if >5% duplicates, -10 if >1%, -5 if any
    - High null columns: -10 per column (max -30)
    - Zero variance columns: -5 per column (max -15)
    - PII columns: -10 per column (max -20)
    - Mixed types: -10 per column (max -20)
    - Outliers: -5 per column (max -15), informational only
    """
    score = 100

    for check in checks:
        if check["check"] == "duplicate_rows":
            dup_rows = check["total_duplicate_rows"]
            if row_count > 0:
                dup_pct = dup_rows / row_count * 100
                if dup_pct > 5:
                    score -= 20
                elif dup_pct > 1:
                    score -= 10
                elif dup_rows > 0:
                    score -= 5

        elif check["check"] == "high_null_columns":
            penalty = min(check["columns_flagged"] * 10, 30)
            score -= penalty

        elif check["check"] == "zero_variance_columns":
            penalty = min(check["columns_flagged"] * 5, 15)
            score -= penalty

        elif check["check"] == "potential_pii":
            penalty = min(check["columns_flagged"] * 10, 20)
            score -= penalty

        elif check["check"] == "mixed_types":
            penalty = min(check["columns_flagged"] * 10, 20)
            score -= penalty

        elif check["check"] == "outliers":
            penalty = min(check["columns_flagged"] * 5, 15)
            score -= penalty

    return max(0, score)


def format_report(result):
    """Format quality check result as human-readable text."""
    lines = [
        "Data Quality Report",
        "====================",
        "",
        "File:          {}".format(result["file"]),
        "Rows:          {:,}".format(result["row_count"]),
        "Columns:       {}".format(result["column_count"]),
        "Quality Score: {}/100".format(result["quality_score"]),
        "",
    ]

    # Score assessment
    score = result["quality_score"]
    if score >= 90:
        assessment = "Excellent - data is clean and consistent"
    elif score >= 75:
        assessment = "Good - minor issues detected"
    elif score >= 50:
        assessment = "Fair - several issues need attention"
    else:
        assessment = "Poor - significant data quality problems"
    lines.append("Assessment:    {}".format(assessment))
    lines.append("")

    # Individual checks
    lines.append("Checks:")
    lines.append("-" * 60)

    for check in result["checks"]:
        status_label = check["status"]
        lines.append("  [{}] {}: {}".format(status_label, check["check"], check["detail"]))

        if check.get("details"):
            for detail in check["details"]:
                if "column" in detail:
                    extra_info = ""
                    if "null_pct" in detail:
                        extra_info = " ({}% null)".format(detail["null_pct"])
                    elif "constant_value" in detail:
                        extra_info = " (value: {})".format(detail["constant_value"])
                    elif "pii_type" in detail:
                        extra_info = " ({}, detected via {})".format(
                            detail["pii_type"], detail["method"]
                        )
                    elif "types_found" in detail:
                        extra_info = " (types: {})".format(detail["types_found"])
                    elif "outlier_count" in detail:
                        extra_info = " ({} outliers, {}%)".format(
                            detail["outlier_count"], detail["outlier_pct"]
                        )
                    lines.append("         - {}{}".format(detail["column"], extra_info))

    lines.append("")

    # Summary of issues
    issues = [c for c in result["checks"] if c["status"] in ("WARN", "INFO")]
    if issues:
        lines.append("Issues Found:")
        for issue in issues:
            lines.append("  - {}".format(issue["detail"]))
    else:
        lines.append("No issues found. Data quality is excellent.")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Check data quality of a CSV file. Reports duplicates, high-null columns, zero-variance columns, potential PII, mixed types, outliers, and a quality score."
    )
    parser.add_argument(
        "csv_file",
        type=str,
        help="Path to the CSV file to check",
    )
    parser.add_argument(
        "--stddev",
        type=float,
        default=3.0,
        help="Standard deviation threshold for outlier detection (default: 3.0)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="output_json",
        help="Output results as JSON",
    )

    args = parser.parse_args()

    # Read CSV
    try:
        with open(args.csv_file, "r", newline="", encoding="utf-8") as f:
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
                print("Error: CSV file is empty (no header row).", file=sys.stderr)
                sys.exit(1)

            rows = []
            columns = {}
            for h in headers:
                columns[h] = []
            for row in reader:
                rows.append(row)
                for i, h in enumerate(headers):
                    if i < len(row):
                        columns[h].append(row[i])
                    else:
                        columns[h].append("")

    except FileNotFoundError:
        print("Error: File not found: {}".format(args.csv_file), file=sys.stderr)
        sys.exit(1)
    except IOError as e:
        print("Error reading file: {}".format(e), file=sys.stderr)
        sys.exit(1)

    row_count = len(rows)
    if row_count == 0:
        print("Error: CSV file has headers but no data rows.", file=sys.stderr)
        sys.exit(1)

    # Run checks
    checks = [
        check_duplicates(rows),
        check_null_columns(headers, columns, row_count),
        check_zero_variance(headers, columns),
        check_pii(headers, columns),
        check_mixed_types(headers, columns),
        check_outliers(headers, columns, stddev_threshold=args.stddev),
    ]

    quality_score = compute_quality_score(checks, row_count)

    result = {
        "file": args.csv_file,
        "row_count": row_count,
        "column_count": len(headers),
        "quality_score": quality_score,
        "checks": checks,
    }

    if args.output_json:
        print(json.dumps(result, indent=2))
    else:
        print(format_report(result))

    # Exit non-zero if quality score is below 50
    if quality_score < 50:
        sys.exit(1)


if __name__ == "__main__":
    main()
