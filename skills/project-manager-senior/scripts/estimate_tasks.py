#!/usr/bin/env python3
"""Estimate effort for tasks based on complexity sizing.

Takes a CSV or text file of tasks with complexity ratings (S/M/L/XL) and
produces effort estimates. Outputs a Markdown table with per-task estimates,
total hours, and recommended sprint allocation.

Complexity mapping:
  S  =  2 hours
  M  =  5 hours
  L  = 13 hours
  XL = 21 hours
"""

import argparse
import csv
import io
import math
import os
import re
import sys


COMPLEXITY_HOURS = {
    "S": 2,
    "M": 5,
    "L": 13,
    "XL": 21,
}

PRODUCTIVE_HOURS_PER_DAY = 6


def read_file(filepath):
    """Read a file and return its content."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        print(f"Error: File not found: {filepath}", file=sys.stderr)
        sys.exit(1)
    except PermissionError:
        print(f"Error: Permission denied: {filepath}", file=sys.stderr)
        sys.exit(1)
    except UnicodeDecodeError:
        print(f"Error: File is not valid UTF-8 text: {filepath}", file=sys.stderr)
        sys.exit(1)


def parse_csv(content):
    """Parse CSV content into a list of task dicts.

    Expected columns: task name, complexity (S/M/L/XL).
    Optionally: assignee, notes, etc.
    The parser is flexible -- it looks for a column containing complexity values.
    """
    tasks = []
    reader = csv.reader(io.StringIO(content))
    rows = list(reader)

    if not rows:
        return tasks

    # Detect header row
    header = [h.strip().lower() for h in rows[0]]
    has_header = any(
        col in header
        for col in ["task", "name", "complexity", "size", "estimate", "description"]
    )

    # Find column indices
    task_col = None
    complexity_col = None

    if has_header:
        for i, col in enumerate(header):
            if col in ("task", "name", "description", "title", "story"):
                task_col = i
            if col in ("complexity", "size", "estimate", "effort", "t-shirt", "tshirt"):
                complexity_col = i
        data_rows = rows[1:]
    else:
        data_rows = rows

    # If columns not found by header, try to auto-detect
    if task_col is None or complexity_col is None:
        for row in data_rows[:5]:  # sample first 5 rows
            for i, cell in enumerate(row):
                cell_stripped = cell.strip().upper()
                if cell_stripped in COMPLEXITY_HOURS:
                    complexity_col = i
                    break
        if complexity_col is not None:
            # Task column is the first column that isn't the complexity column
            for i in range(len(data_rows[0]) if data_rows else 0):
                if i != complexity_col:
                    task_col = i
                    break

    if task_col is None:
        task_col = 0
    if complexity_col is None:
        complexity_col = 1

    for row_num, row in enumerate(data_rows, 2 if has_header else 1):
        if not row or all(cell.strip() == "" for cell in row):
            continue

        task_name = row[task_col].strip() if task_col < len(row) else f"Task {row_num}"
        complexity_raw = row[complexity_col].strip().upper() if complexity_col < len(row) else ""

        if complexity_raw not in COMPLEXITY_HOURS:
            print(
                f"Warning: Unrecognized complexity '{complexity_raw}' on line {row_num}, "
                f"skipping task '{task_name}'.",
                file=sys.stderr,
            )
            continue

        tasks.append({
            "name": task_name,
            "complexity": complexity_raw,
            "hours": COMPLEXITY_HOURS[complexity_raw],
        })

    return tasks


def parse_text(content):
    """Parse plain text content into a list of task dicts.

    Supports formats like:
      - Task name [S]
      - Task name (M)
      - Task name - L
      - Task name: XL
      Task name, S
    """
    tasks = []
    lines = content.splitlines()
    complexity_pattern = re.compile(
        r'^[-*+]?\s*(.+?)\s*[\[\(:\-,]\s*(S|M|L|XL)\s*[\]\)]?\s*$',
        re.IGNORECASE,
    )

    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if not stripped:
            continue

        match = complexity_pattern.match(stripped)
        if match:
            task_name = match.group(1).strip().rstrip(":-,")
            complexity = match.group(2).strip().upper()

            if complexity in COMPLEXITY_HOURS:
                tasks.append({
                    "name": task_name,
                    "complexity": complexity,
                    "hours": COMPLEXITY_HOURS[complexity],
                })

    return tasks


def format_markdown(tasks, filepath):
    """Format task estimates as Markdown."""
    lines = []
    lines.append("# Task Effort Estimation Report")
    lines.append("")
    lines.append(f"**Source:** `{filepath}`")
    lines.append("")

    # Complexity legend
    lines.append("## Complexity Scale")
    lines.append("")
    lines.append("| Size | Hours |")
    lines.append("|------|-------|")
    for size, hours in COMPLEXITY_HOURS.items():
        lines.append(f"| {size} | {hours}h |")
    lines.append("")

    # Task estimates table
    lines.append("## Task Estimates")
    lines.append("")
    lines.append("| # | Task | Complexity | Estimated Hours |")
    lines.append("|---|------|------------|-----------------|")

    total_hours = 0
    complexity_counts = {"S": 0, "M": 0, "L": 0, "XL": 0}

    for idx, task in enumerate(tasks, 1):
        lines.append(f"| {idx} | {task['name']} | {task['complexity']} | {task['hours']}h |")
        total_hours += task["hours"]
        complexity_counts[task["complexity"]] += 1

    lines.append(f"| | **Total** | | **{total_hours}h** |")
    lines.append("")

    # Distribution summary
    lines.append("## Complexity Distribution")
    lines.append("")
    lines.append("| Complexity | Count | Hours |")
    lines.append("|------------|-------|-------|")
    for size in ["S", "M", "L", "XL"]:
        count = complexity_counts[size]
        if count > 0:
            hours = count * COMPLEXITY_HOURS[size]
            lines.append(f"| {size} | {count} | {hours}h |")
    lines.append("")

    # Sprint allocation
    lines.append("## Sprint Allocation")
    lines.append("")
    lines.append(f"Assuming **{PRODUCTIVE_HOURS_PER_DAY}h** productive time per day:")
    lines.append("")

    total_days = total_hours / PRODUCTIVE_HOURS_PER_DAY
    sprint_days_2w = 10  # 2-week sprint
    sprints_needed = math.ceil(total_days / sprint_days_2w) if total_days > 0 else 0

    lines.append("| Metric | Value |")
    lines.append("|--------|-------|")
    lines.append(f"| Total effort | {total_hours}h |")
    lines.append(f"| Total working days | {total_days:.1f} days |")
    lines.append(f"| 2-week sprints needed (1 person) | {sprints_needed} |")
    lines.append("")

    # Per-sprint breakdown if more than one sprint
    if sprints_needed > 0:
        hours_per_sprint = sprint_days_2w * PRODUCTIVE_HOURS_PER_DAY
        lines.append("### Recommended Sprint Breakdown")
        lines.append("")

        remaining_tasks = list(tasks)
        sprint_num = 1

        while remaining_tasks:
            sprint_hours = 0
            sprint_tasks = []

            for task in list(remaining_tasks):
                if sprint_hours + task["hours"] <= hours_per_sprint:
                    sprint_tasks.append(task)
                    sprint_hours += task["hours"]
                    remaining_tasks.remove(task)

            # If no tasks fit cleanly, take the next one anyway
            if not sprint_tasks and remaining_tasks:
                task = remaining_tasks.pop(0)
                sprint_tasks.append(task)
                sprint_hours += task["hours"]

            lines.append(f"**Sprint {sprint_num}** ({sprint_hours}h / {hours_per_sprint}h capacity):")
            lines.append("")
            for t in sprint_tasks:
                lines.append(f"- {t['name']} ({t['complexity']}, {t['hours']}h)")
            lines.append("")

            sprint_num += 1

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Estimate effort for tasks based on complexity sizing (S/M/L/XL).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Complexity mapping:
  S  =  2 hours
  M  =  5 hours
  L  = 13 hours
  XL = 21 hours

Supported input formats:
  CSV:  task_name,complexity
  Text: - Task name [S]
        - Task name (M)
        - Task name - L

examples:
  %(prog)s tasks.csv
  %(prog)s backlog.txt
""",
    )
    parser.add_argument(
        "file",
        help="Path to the task file (CSV or text)",
    )

    args = parser.parse_args()

    if not os.path.isfile(args.file):
        print(f"Error: File not found: {args.file}", file=sys.stderr)
        sys.exit(1)

    content = read_file(args.file)

    if not content.strip():
        print("Error: Input file is empty.", file=sys.stderr)
        sys.exit(1)

    # Detect format
    if args.file.lower().endswith(".csv"):
        tasks = parse_csv(content)
    else:
        # Try CSV first, fall back to text
        tasks = parse_csv(content)
        if not tasks:
            tasks = parse_text(content)

    if not tasks:
        print("Error: No valid tasks found in file. Each task needs a name and "
              "complexity (S/M/L/XL).", file=sys.stderr)
        sys.exit(1)

    output = format_markdown(tasks, args.file)
    print(output)


if __name__ == "__main__":
    main()
