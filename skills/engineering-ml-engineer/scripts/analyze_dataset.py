#!/usr/bin/env python3
"""
analyze_dataset.py -- Analyze a CSV file and report dataset statistics.

Reports:
  - Row count, column count
  - Column types (numeric, categorical, text)
  - Missing values per column
  - Class distribution for a specified target column
  - Text column statistics: min/max/mean length, vocabulary size

Self-contained: uses only stdlib (csv module) + argparse. Outputs markdown.
"""

import argparse
import csv
import os
import re
import sys
from collections import Counter


def read_csv(filepath, max_rows=None):
    """Read a CSV file and return headers and rows."""
    rows = []
    with open(filepath, "r", encoding="utf-8", errors="replace", newline="") as f:
        reader = csv.reader(f)
        headers = next(reader, None)
        if headers is None:
            return [], []
        count = 0
        for row in reader:
            rows.append(row)
            count += 1
            if max_rows and count >= max_rows:
                break
    return headers, rows


def infer_column_type(values):
    """
    Infer column type from values.
    Returns: 'numeric', 'categorical', 'text', or 'empty'.
    """
    non_empty = [v for v in values if v.strip()]
    if not non_empty:
        return "empty"

    # Check if numeric
    numeric_count = 0
    for v in non_empty:
        v_clean = v.strip()
        try:
            float(v_clean)
            numeric_count += 1
        except ValueError:
            pass

    if numeric_count / len(non_empty) > 0.9:
        return "numeric"

    # Check if text (long strings, high cardinality)
    avg_length = sum(len(v) for v in non_empty) / len(non_empty)
    unique_ratio = len(set(non_empty)) / len(non_empty) if non_empty else 0

    if avg_length > 50 or (unique_ratio > 0.8 and avg_length > 20):
        return "text"

    return "categorical"


def compute_numeric_stats(values):
    """Compute basic stats for numeric columns."""
    nums = []
    for v in values:
        v_clean = v.strip()
        if v_clean:
            try:
                nums.append(float(v_clean))
            except ValueError:
                pass

    if not nums:
        return None

    nums_sorted = sorted(nums)
    n = len(nums)
    total = sum(nums)
    mean = total / n
    variance = sum((x - mean) ** 2 for x in nums) / n
    std = variance ** 0.5
    median = nums_sorted[n // 2] if n % 2 else (nums_sorted[n // 2 - 1] + nums_sorted[n // 2]) / 2

    return {
        "count": n,
        "mean": mean,
        "std": std,
        "min": nums_sorted[0],
        "25%": nums_sorted[int(n * 0.25)],
        "50%": median,
        "75%": nums_sorted[int(n * 0.75)],
        "max": nums_sorted[-1],
    }


def compute_text_stats(values):
    """Compute text-specific statistics."""
    non_empty = [v for v in values if v.strip()]
    if not non_empty:
        return None

    lengths = [len(v) for v in non_empty]
    word_counts = [len(v.split()) for v in non_empty]

    # Vocabulary: unique lowercased words
    all_words = []
    for v in non_empty:
        words = re.findall(r"\b\w+\b", v.lower())
        all_words.extend(words)
    vocab_size = len(set(all_words))

    return {
        "count": len(non_empty),
        "min_length": min(lengths),
        "max_length": max(lengths),
        "mean_length": sum(lengths) / len(lengths),
        "min_words": min(word_counts),
        "max_words": max(word_counts),
        "mean_words": sum(word_counts) / len(word_counts),
        "vocab_size": vocab_size,
    }


def compute_class_distribution(values):
    """Compute class distribution for a categorical column."""
    non_empty = [v.strip() for v in values if v.strip()]
    if not non_empty:
        return None

    counter = Counter(non_empty)
    total = len(non_empty)
    distribution = []
    for label, count in counter.most_common():
        distribution.append({
            "label": label,
            "count": count,
            "percentage": (count / total) * 100,
        })
    return distribution


def format_number(n):
    """Format a number for display."""
    if isinstance(n, float):
        if abs(n) >= 1000:
            return f"{n:,.1f}"
        return f"{n:.4f}"
    return f"{n:,}"


def main():
    parser = argparse.ArgumentParser(
        description="Analyze a CSV file and report dataset statistics.",
        epilog=(
            "Examples:\n"
            "  %(prog)s data.csv\n"
            "  %(prog)s data.csv --target label\n"
            "  %(prog)s data.csv --target sentiment --max-rows 50000\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("file", help="Path to the CSV file to analyze")
    parser.add_argument(
        "--target",
        type=str,
        default=None,
        help="Name of the target/label column for class distribution analysis",
    )
    parser.add_argument(
        "--max-rows",
        type=int,
        default=None,
        help="Maximum number of rows to read (default: all)",
    )
    args = parser.parse_args()

    filepath = os.path.abspath(args.file)
    if not os.path.isfile(filepath):
        print(f"Error: File not found: {filepath}", file=sys.stderr)
        sys.exit(1)

    headers, rows = read_csv(filepath, max_rows=args.max_rows)
    if not headers:
        print("Error: CSV file is empty or has no headers.", file=sys.stderr)
        sys.exit(1)

    num_rows = len(rows)
    num_cols = len(headers)

    # Build column data
    columns = {}
    for col_idx, header in enumerate(headers):
        values = [row[col_idx] if col_idx < len(row) else "" for row in rows]
        columns[header] = values

    # Infer types
    col_types = {}
    for header, values in columns.items():
        col_types[header] = infer_column_type(values)

    # Count missing values
    missing = {}
    for header, values in columns.items():
        missing_count = sum(1 for v in values if not v.strip())
        missing[header] = missing_count

    # Output
    print(f"## Dataset Analysis: {os.path.basename(filepath)}\n")
    print(f"File: `{filepath}`\n")

    # Summary
    print("### Summary\n")
    print("| Metric | Value |")
    print("|---|---|")
    print(f"| Rows | {num_rows:,} |")
    print(f"| Columns | {num_cols} |")
    num_numeric = sum(1 for t in col_types.values() if t == "numeric")
    num_categorical = sum(1 for t in col_types.values() if t == "categorical")
    num_text = sum(1 for t in col_types.values() if t == "text")
    print(f"| Numeric columns | {num_numeric} |")
    print(f"| Categorical columns | {num_categorical} |")
    print(f"| Text columns | {num_text} |")
    total_missing = sum(missing.values())
    total_cells = num_rows * num_cols
    missing_pct = (total_missing / total_cells * 100) if total_cells > 0 else 0
    print(f"| Total missing values | {total_missing:,} ({missing_pct:.1f}%) |")
    print()

    # Column details
    print("### Columns\n")
    print("| Column | Type | Missing | Missing % |")
    print("|---|---|---|---|")
    for header in headers:
        m = missing[header]
        m_pct = (m / num_rows * 100) if num_rows > 0 else 0
        flag = " **!**" if m_pct > 20 else ""
        print(f"| `{header}` | {col_types[header]} | {m:,} | {m_pct:.1f}%{flag} |")
    print()

    # Numeric column statistics
    numeric_cols = [h for h in headers if col_types[h] == "numeric"]
    if numeric_cols:
        print("### Numeric Column Statistics\n")
        print("| Column | Mean | Std | Min | Median | Max |")
        print("|---|---|---|---|---|---|")
        for header in numeric_cols:
            stats = compute_numeric_stats(columns[header])
            if stats:
                print(
                    f"| `{header}` | {format_number(stats['mean'])} | "
                    f"{format_number(stats['std'])} | {format_number(stats['min'])} | "
                    f"{format_number(stats['50%'])} | {format_number(stats['max'])} |"
                )
        print()

    # Text column statistics
    text_cols = [h for h in headers if col_types[h] == "text"]
    if text_cols:
        print("### Text Column Statistics\n")
        print("| Column | Min Length | Max Length | Mean Length | Mean Words | Vocab Size |")
        print("|---|---|---|---|---|---|")
        for header in text_cols:
            stats = compute_text_stats(columns[header])
            if stats:
                print(
                    f"| `{header}` | {stats['min_length']:,} | {stats['max_length']:,} | "
                    f"{stats['mean_length']:.1f} | {stats['mean_words']:.1f} | "
                    f"{stats['vocab_size']:,} |"
                )
        print()

    # Categorical column value counts
    cat_cols = [h for h in headers if col_types[h] == "categorical"]
    if cat_cols:
        print("### Categorical Column Cardinality\n")
        print("| Column | Unique Values | Top Value | Top Count |")
        print("|---|---|---|---|")
        for header in cat_cols:
            non_empty = [v.strip() for v in columns[header] if v.strip()]
            unique = len(set(non_empty))
            counter = Counter(non_empty)
            if counter:
                top_val, top_count = counter.most_common(1)[0]
                # Truncate long values
                display_val = top_val if len(top_val) <= 30 else top_val[:27] + "..."
                print(f"| `{header}` | {unique:,} | {display_val} | {top_count:,} |")
            else:
                print(f"| `{header}` | 0 | - | - |")
        print()

    # Target column class distribution
    target_col = args.target
    if target_col:
        if target_col not in columns:
            print(f"Warning: Target column '{target_col}' not found in CSV.", file=sys.stderr)
            # Try case-insensitive match
            matches = [h for h in headers if h.lower() == target_col.lower()]
            if matches:
                target_col = matches[0]
                print(f"Using '{target_col}' instead.", file=sys.stderr)
            else:
                print(f"Available columns: {', '.join(headers)}", file=sys.stderr)
                target_col = None

    if target_col and target_col in columns:
        dist = compute_class_distribution(columns[target_col])
        if dist:
            print(f"### Class Distribution: `{target_col}`\n")
            print("| Class | Count | Percentage |")
            print("|---|---|---|")
            for entry in dist:
                bar = "#" * int(entry["percentage"] / 2)
                print(f"| {entry['label']} | {entry['count']:,} | {entry['percentage']:.1f}% {bar} |")

            # Imbalance warning
            max_pct = max(e["percentage"] for e in dist)
            min_pct = min(e["percentage"] for e in dist)
            if max_pct / max(min_pct, 0.01) > 5:
                print()
                print(
                    f"**Warning**: Dataset is imbalanced "
                    f"(ratio {max_pct / max(min_pct, 0.01):.1f}:1). "
                    f"Consider stratified splitting, class weights, or SMOTE."
                )
            print()
    elif not target_col:
        # Auto-detect: show distribution for first categorical column with low cardinality
        for header in headers:
            if col_types[header] == "categorical":
                non_empty = [v.strip() for v in columns[header] if v.strip()]
                unique = len(set(non_empty))
                if 2 <= unique <= 20:
                    dist = compute_class_distribution(columns[header])
                    if dist:
                        print(f"### Possible Target: `{header}` (auto-detected)\n")
                        print("| Class | Count | Percentage |")
                        print("|---|---|---|")
                        for entry in dist:
                            print(f"| {entry['label']} | {entry['count']:,} | {entry['percentage']:.1f}% |")
                        print()
                        print(f"*Use `--target {header}` to confirm this as the target column.*")
                        print()
                    break

    # Recommendations
    print("### Recommendations\n")
    if num_rows < 100:
        print("- **Very small dataset** ({:,} rows): Consider few-shot learning or data augmentation.".format(num_rows))
    elif num_rows < 1000:
        print("- **Small dataset** ({:,} rows): Use cross-validation (5-fold) for reliable evaluation.".format(num_rows))
    elif num_rows < 10000:
        print("- **Medium dataset** ({:,} rows): LoRA fine-tuning or gradient-boosted trees are appropriate.".format(num_rows))
    else:
        print("- **Large dataset** ({:,} rows): Full fine-tuning or deep learning is viable.".format(num_rows))

    if total_missing > 0:
        high_missing = [h for h in headers if missing[h] / max(num_rows, 1) > 0.3]
        if high_missing:
            print(f"- **High missing values** in: {', '.join('`' + h + '`' for h in high_missing)}. Consider dropping or imputing.")
        else:
            print(f"- **Missing values present** ({total_missing:,} total). Imputation recommended.")

    if text_cols:
        print(f"- **Text columns detected**: {', '.join('`' + h + '`' for h in text_cols)}. Consider transformer-based models.")
    if num_numeric > 0 and num_text == 0:
        print(f"- **Tabular data** detected. XGBoost/LightGBM is likely the best starting point.")


if __name__ == "__main__":
    main()
