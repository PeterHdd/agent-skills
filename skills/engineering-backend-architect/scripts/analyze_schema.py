#!/usr/bin/env python3
"""
analyze_schema.py -- Analyze a SQL file containing CREATE TABLE statements.

Parses CREATE TABLE definitions using regex and reports:
  - Table count
  - Columns per table
  - Tables missing indexes
  - Tables without primary keys
  - Foreign key relationships
  - Column type distribution

Designed for quick schema review, not full SQL parsing.
"""

import argparse
import os
import re
import sys
from collections import defaultdict


def parse_create_tables(sql_text):
    """
    Extract CREATE TABLE statements and their column definitions.
    Returns a list of dicts with table info.
    """
    tables = []

    # Match CREATE TABLE statements (handles IF NOT EXISTS, schema-qualified names)
    table_pattern = re.compile(
        r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(?:`?(\w+)`?\.)?`?(\w+)`?\s*\((.*?)\)\s*;",
        re.IGNORECASE | re.DOTALL,
    )

    for match in table_pattern.finditer(sql_text):
        schema = match.group(1) or "public"
        table_name = match.group(2)
        body = match.group(3)

        table_info = {
            "schema": schema,
            "name": table_name,
            "full_name": f"{schema}.{table_name}" if schema != "public" else table_name,
            "columns": [],
            "has_primary_key": False,
            "primary_key_columns": [],
            "foreign_keys": [],
            "unique_constraints": [],
        }

        # Split body into lines, handling nested parentheses
        lines = _split_table_body(body)

        for line in lines:
            line = line.strip().rstrip(",").strip()
            if not line:
                continue

            # Check for PRIMARY KEY constraint
            pk_match = re.match(
                r"(?:CONSTRAINT\s+\w+\s+)?PRIMARY\s+KEY\s*\(([^)]+)\)",
                line,
                re.IGNORECASE,
            )
            if pk_match:
                table_info["has_primary_key"] = True
                cols = [c.strip().strip("`\"'") for c in pk_match.group(1).split(",")]
                table_info["primary_key_columns"] = cols
                continue

            # Check for FOREIGN KEY constraint
            fk_match = re.match(
                r"(?:CONSTRAINT\s+\w+\s+)?FOREIGN\s+KEY\s*\(([^)]+)\)\s*REFERENCES\s+`?(\w+)`?\s*\(([^)]+)\)",
                line,
                re.IGNORECASE,
            )
            if fk_match:
                fk_cols = [c.strip().strip("`\"'") for c in fk_match.group(1).split(",")]
                ref_table = fk_match.group(2)
                ref_cols = [c.strip().strip("`\"'") for c in fk_match.group(3).split(",")]
                table_info["foreign_keys"].append({
                    "columns": fk_cols,
                    "references_table": ref_table,
                    "references_columns": ref_cols,
                })
                continue

            # Check for UNIQUE constraint
            uniq_match = re.match(
                r"(?:CONSTRAINT\s+\w+\s+)?UNIQUE\s*\(([^)]+)\)",
                line,
                re.IGNORECASE,
            )
            if uniq_match:
                cols = [c.strip().strip("`\"'") for c in uniq_match.group(1).split(",")]
                table_info["unique_constraints"].append(cols)
                continue

            # Check for CHECK, INDEX, KEY (skip)
            if re.match(r"(?:CHECK|INDEX|KEY|CONSTRAINT)\b", line, re.IGNORECASE):
                continue

            # Parse column definition
            col_match = re.match(
                r"`?(\w+)`?\s+(\w+(?:\([^)]*\))?(?:\s+\w+)*)",
                line,
                re.IGNORECASE,
            )
            if col_match:
                col_name = col_match.group(1)
                col_rest = col_match.group(2)
                col_type = col_rest.split()[0] if col_rest else "UNKNOWN"

                is_pk = bool(re.search(r"\bPRIMARY\s+KEY\b", line, re.IGNORECASE))
                is_not_null = bool(re.search(r"\bNOT\s+NULL\b", line, re.IGNORECASE))
                has_default = bool(re.search(r"\bDEFAULT\b", line, re.IGNORECASE))

                if is_pk:
                    table_info["has_primary_key"] = True
                    table_info["primary_key_columns"].append(col_name)

                table_info["columns"].append({
                    "name": col_name,
                    "type": col_type.upper(),
                    "not_null": is_not_null or is_pk,
                    "has_default": has_default,
                    "is_primary_key": is_pk,
                })

        tables.append(table_info)

    return tables


def _split_table_body(body):
    """Split CREATE TABLE body into individual definitions, respecting parentheses."""
    lines = []
    current = []
    depth = 0
    for char in body:
        if char == "(":
            depth += 1
            current.append(char)
        elif char == ")":
            depth -= 1
            current.append(char)
        elif char == "," and depth == 0:
            lines.append("".join(current))
            current = []
        else:
            current.append(char)
    if current:
        lines.append("".join(current))
    return lines


def parse_indexes(sql_text):
    """Extract CREATE INDEX statements."""
    indexes = []
    idx_pattern = re.compile(
        r"CREATE\s+(?:UNIQUE\s+)?INDEX\s+(?:IF\s+NOT\s+EXISTS\s+)?`?(\w+)`?\s+ON\s+`?(\w+)`?\s*\(([^)]+)\)",
        re.IGNORECASE,
    )
    for match in idx_pattern.finditer(sql_text):
        indexes.append({
            "name": match.group(1),
            "table": match.group(2),
            "columns": [c.strip().strip("`\"'") for c in match.group(3).split(",")],
        })
    return indexes


def format_output(tables, indexes, filepath):
    """Format analysis as a structured markdown report."""
    lines = []

    lines.append(f"## Schema Analysis: {os.path.basename(filepath)}")
    lines.append(f"File: `{filepath}`")
    lines.append("")

    # Summary
    lines.append("### Summary")
    lines.append("")
    lines.append(f"| Metric | Value |")
    lines.append(f"|---|---|")
    lines.append(f"| Tables | {len(tables)} |")
    total_cols = sum(len(t['columns']) for t in tables)
    lines.append(f"| Total columns | {total_cols} |")
    lines.append(f"| Indexes (CREATE INDEX) | {len(indexes)} |")
    fk_count = sum(len(t['foreign_keys']) for t in tables)
    lines.append(f"| Foreign key relationships | {fk_count} |")
    lines.append("")

    # Per-table details
    lines.append("### Tables")
    lines.append("")
    lines.append("| Table | Columns | Primary Key | Foreign Keys | Has Index |")
    lines.append("|---|---|---|---|---|")

    indexed_tables = {idx["table"] for idx in indexes}

    for table in tables:
        pk_display = ", ".join(table["primary_key_columns"]) if table["has_primary_key"] else "MISSING"
        fk_display = str(len(table["foreign_keys"])) if table["foreign_keys"] else "0"
        # A table has an index if it has a PK (implicitly indexed) or an explicit CREATE INDEX
        has_index = table["has_primary_key"] or table["name"] in indexed_tables
        index_display = "Yes" if has_index else "MISSING"

        lines.append(
            f"| `{table['full_name']}` | {len(table['columns'])} | {pk_display} | {fk_display} | {index_display} |"
        )
    lines.append("")

    # Issues
    issues = []

    tables_no_pk = [t for t in tables if not t["has_primary_key"]]
    if tables_no_pk:
        for t in tables_no_pk:
            issues.append(f"- Table `{t['full_name']}` has no PRIMARY KEY")

    tables_no_index = [
        t for t in tables
        if not t["has_primary_key"] and t["name"] not in indexed_tables
    ]
    if tables_no_index:
        for t in tables_no_index:
            issues.append(f"- Table `{t['full_name']}` has no indexes (no PK, no CREATE INDEX)")

    if issues:
        lines.append("### Issues")
        lines.append("")
        for issue in issues:
            lines.append(issue)
        lines.append("")

    # Foreign key relationships
    if fk_count > 0:
        lines.append("### Foreign Key Relationships")
        lines.append("")
        lines.append("| From Table | Column(s) | References | Referenced Column(s) |")
        lines.append("|---|---|---|---|")
        for table in tables:
            for fk in table["foreign_keys"]:
                lines.append(
                    f"| `{table['full_name']}` | {', '.join(fk['columns'])} "
                    f"| `{fk['references_table']}` | {', '.join(fk['references_columns'])} |"
                )
        lines.append("")

    # Column type distribution
    type_counts = defaultdict(int)
    for table in tables:
        for col in table["columns"]:
            base_type = re.sub(r"\(.*\)", "", col["type"])
            type_counts[base_type] += 1

    if type_counts:
        lines.append("### Column Type Distribution")
        lines.append("")
        lines.append("| Type | Count |")
        lines.append("|---|---|")
        for ctype, count in sorted(type_counts.items(), key=lambda x: -x[1]):
            lines.append(f"| {ctype} | {count} |")
        lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Analyze a SQL file containing CREATE TABLE statements.",
        epilog="Reports table count, columns, missing indexes, missing primary keys, and foreign key relationships.",
    )
    parser.add_argument("file", help="Path to the SQL file to analyze")
    args = parser.parse_args()

    filepath = os.path.abspath(args.file)

    if not os.path.isfile(filepath):
        print(f"Error: File not found: {filepath}", file=sys.stderr)
        sys.exit(1)

    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            sql_text = f.read()
    except OSError as e:
        print(f"Error: Could not read file: {e}", file=sys.stderr)
        sys.exit(1)

    tables = parse_create_tables(sql_text)
    indexes = parse_indexes(sql_text)

    if not tables:
        print(f"No CREATE TABLE statements found in {filepath}", file=sys.stderr)
        print("Hint: This tool uses regex-based parsing. Ensure statements end with ';'.", file=sys.stderr)
        sys.exit(1)

    print(format_output(tables, indexes, filepath))


if __name__ == "__main__":
    main()
