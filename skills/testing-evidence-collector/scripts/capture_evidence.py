#!/usr/bin/env python3
"""Organize test evidence files into a structured markdown report.

Scans a directory for screenshots (*.png, *.jpg, *.jpeg), log files
(*.log, *.txt), and other evidence artifacts. Produces a markdown
index with files organized by type, file sizes, modification dates,
and a summary table.
"""

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple


FILE_CATEGORIES = {
    "Screenshots": {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"},
    "Logs": {".log", ".txt"},
    "Data": {".json", ".xml", ".csv", ".yaml", ".yml"},
    "Documents": {".pdf", ".html", ".htm", ".md"},
    "Videos": {".mp4", ".webm", ".mov", ".avi"},
}


def format_size(size_bytes: int) -> str:
    """Format a file size in bytes to a human-readable string."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"


def categorize_file(filepath: Path) -> str:
    """Determine the category of a file based on its extension."""
    ext = filepath.suffix.lower()
    for category, extensions in FILE_CATEGORIES.items():
        if ext in extensions:
            return category
    return "Other"


def collect_files(directory: Path, recursive: bool = True) -> List[Path]:
    """Collect all files in a directory, optionally recursing into subdirs."""
    files = []
    if recursive:
        for root, _dirs, filenames in os.walk(directory):
            for fname in filenames:
                fpath = Path(root) / fname
                if fpath.is_file() and not fname.startswith("."):
                    files.append(fpath)
    else:
        for item in directory.iterdir():
            if item.is_file() and not item.name.startswith("."):
                files.append(item)
    return sorted(files)


def get_file_info(filepath: Path) -> Tuple[int, datetime]:
    """Get file size in bytes and last modification datetime."""
    stat = filepath.stat()
    size = stat.st_size
    mtime = datetime.fromtimestamp(stat.st_mtime)
    return size, mtime


def generate_report(directory: Path, recursive: bool = True) -> str:
    """Generate a markdown evidence report for the given directory."""
    files = collect_files(directory, recursive)

    if not files:
        return (
            f"# Test Evidence Report\n\n"
            f"**Directory:** `{directory.resolve()}`\n\n"
            f"> No evidence files found in this directory.\n"
        )

    # Categorize files
    categorized: Dict[str, List[Tuple[Path, int, datetime]]] = {}
    total_size = 0

    for fpath in files:
        category = categorize_file(fpath)
        size, mtime = get_file_info(fpath)
        total_size += size
        if category not in categorized:
            categorized[category] = []
        categorized[category].append((fpath, size, mtime))

    # Build report
    lines = []
    lines.append("# Test Evidence Report")
    lines.append("")
    lines.append(f"**Directory:** `{directory.resolve()}`  ")
    lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  ")
    lines.append(f"**Total files:** {len(files)}  ")
    lines.append(f"**Total size:** {format_size(total_size)}")
    lines.append("")

    # Summary table
    lines.append("## Summary")
    lines.append("")
    lines.append("| Category | Count | Total Size |")
    lines.append("|----------|------:|-----------:|")

    # Sort categories by the canonical order, then alphabetically for extras
    category_order = list(FILE_CATEGORIES.keys()) + ["Other"]
    sorted_categories = sorted(
        categorized.keys(),
        key=lambda c: (category_order.index(c) if c in category_order else len(category_order), c),
    )

    for category in sorted_categories:
        file_list = categorized[category]
        cat_size = sum(size for _, size, _ in file_list)
        lines.append(f"| {category} | {len(file_list)} | {format_size(cat_size)} |")

    lines.append("")

    # Detailed sections per category
    for category in sorted_categories:
        file_list = categorized[category]
        lines.append(f"## {category}")
        lines.append("")
        lines.append("| # | File | Size | Last Modified |")
        lines.append("|--:|------|-----:|--------------:|")

        for i, (fpath, size, mtime) in enumerate(file_list, 1):
            rel_path = fpath.relative_to(directory)
            mtime_str = mtime.strftime("%Y-%m-%d %H:%M:%S")
            lines.append(f"| {i} | `{rel_path}` | {format_size(size)} | {mtime_str} |")

        lines.append("")

    # Oldest and newest files
    all_with_info = []
    for file_list in categorized.values():
        all_with_info.extend(file_list)

    if all_with_info:
        oldest = min(all_with_info, key=lambda x: x[2])
        newest = max(all_with_info, key=lambda x: x[2])
        lines.append("## Timeline")
        lines.append("")
        lines.append(f"- **Oldest evidence:** `{oldest[0].relative_to(directory)}` "
                      f"({oldest[2].strftime('%Y-%m-%d %H:%M:%S')})")
        lines.append(f"- **Newest evidence:** `{newest[0].relative_to(directory)}` "
                      f"({newest[2].strftime('%Y-%m-%d %H:%M:%S')})")
        lines.append("")

    lines.append("---")
    lines.append("*Report generated by capture_evidence.py*")
    lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Organize test evidence into a structured markdown report. "
            "Scans a directory for screenshots, logs, and other artifacts, "
            "then outputs a markdown index with file details and summary."
        )
    )
    parser.add_argument(
        "directory",
        help="Path to the directory containing test evidence files",
    )
    parser.add_argument(
        "--no-recursive",
        action="store_true",
        help="Do not recurse into subdirectories (default: recursive)",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default=None,
        help="Write report to a file instead of stdout",
    )

    args = parser.parse_args()

    evidence_dir = Path(args.directory)
    if not evidence_dir.exists():
        print(f"Error: Directory does not exist: {args.directory}", file=sys.stderr)
        sys.exit(1)
    if not evidence_dir.is_dir():
        print(f"Error: Path is not a directory: {args.directory}", file=sys.stderr)
        sys.exit(1)

    recursive = not args.no_recursive
    report = generate_report(evidence_dir, recursive)

    if args.output:
        try:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(report, encoding="utf-8")
            print(f"Report written to: {output_path.resolve()}", file=sys.stderr)
        except OSError as e:
            print(f"Error: Could not write output file: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        print(report)


if __name__ == "__main__":
    main()
