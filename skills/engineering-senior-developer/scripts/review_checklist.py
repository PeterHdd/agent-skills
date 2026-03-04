#!/usr/bin/env python3
"""
review_checklist.py -- Analyze a source file for common senior-dev code review concerns.

Checks performed:
  - TODO/FIXME comment count
  - Function length (lines per function)
  - Missing error handling patterns (bare except, empty catch)
  - Hardcoded secrets patterns (API_KEY=, password=, secret=, token=)
  - Debug statements left in (console.log, print, debugger)

Supports: .py, .ts, .js, .tsx, .jsx files
"""

import argparse
import os
import re
import sys
from collections import defaultdict

SUPPORTED_EXTENSIONS = {".py", ".ts", ".js", ".tsx", ".jsx"}

# --- Pattern definitions ---

SECRET_PATTERNS = [
    re.compile(r"""(?:API_KEY|api_key|apiKey)\s*[=:]\s*['"][^'"]{4,}['"]"""),
    re.compile(r"""(?:PASSWORD|password|passwd)\s*[=:]\s*['"][^'"]{4,}['"]"""),
    re.compile(r"""(?:SECRET|secret|SECRET_KEY|secret_key)\s*[=:]\s*['"][^'"]{4,}['"]"""),
    re.compile(r"""(?:TOKEN|token|access_token|ACCESS_TOKEN)\s*[=:]\s*['"][^'"]{4,}['"]"""),
    re.compile(r"""(?:PRIVATE_KEY|private_key)\s*[=:]\s*['"][^'"]{4,}['"]"""),
]

DEBUG_PATTERNS_PY = [
    re.compile(r"""^\s*print\s*\("""),
    re.compile(r"""^\s*breakpoint\s*\("""),
    re.compile(r"""^\s*pdb\.set_trace\s*\("""),
    re.compile(r"""^\s*import\s+pdb"""),
]

DEBUG_PATTERNS_JS = [
    re.compile(r"""^\s*console\.(log|debug|info|warn|error|trace)\s*\("""),
    re.compile(r"""^\s*debugger\s*;?\s*$"""),
]

BARE_EXCEPT_PY = re.compile(r"""^\s*except\s*:\s*$""")
BROAD_EXCEPT_PY = re.compile(r"""^\s*except\s+Exception\s*:\s*$""")
EMPTY_CATCH_JS = re.compile(r"""catch\s*\([^)]*\)\s*\{\s*\}""")

# Function detection patterns
FUNC_DEF_PY = re.compile(r"""^\s*(?:async\s+)?def\s+(\w+)\s*\(""")
FUNC_DEF_JS = re.compile(
    r"""^\s*(?:export\s+)?(?:async\s+)?(?:function\s+(\w+)|(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?(?:\([^)]*\)|[^=])\s*=>)"""
)
CLASS_METHOD_JS = re.compile(r"""^\s*(?:async\s+)?(\w+)\s*\([^)]*\)\s*\{""")


def detect_language(filepath):
    """Determine the language category from file extension."""
    ext = os.path.splitext(filepath)[1].lower()
    if ext == ".py":
        return "python"
    elif ext in (".ts", ".tsx", ".js", ".jsx"):
        return "javascript"
    return None


def find_todos(lines):
    """Find TODO and FIXME comments."""
    findings = []
    pattern = re.compile(r"""(?:#|//|/\*)\s*(TODO|FIXME|HACK|XXX)\b""", re.IGNORECASE)
    for i, line in enumerate(lines, 1):
        match = pattern.search(line)
        if match:
            tag = match.group(1).upper()
            findings.append((i, tag, line.strip()))
    return findings


def find_long_functions(lines, lang, threshold=50):
    """Find functions exceeding the line-length threshold."""
    findings = []

    if lang == "python":
        funcs = []
        indent_stack = []
        for i, line in enumerate(lines, 1):
            m = FUNC_DEF_PY.match(line)
            if m:
                indent = len(line) - len(line.lstrip())
                # Close any functions at same or deeper indent
                while indent_stack and indent_stack[-1][1] >= indent:
                    prev_name, prev_indent, prev_start = indent_stack.pop()
                    funcs.append((prev_name, prev_start, i - 1))
                indent_stack.append((m.group(1), indent, i))

        # Close remaining open functions
        total = len(lines)
        while indent_stack:
            name, indent, start = indent_stack.pop()
            funcs.append((name, start, total))

        for name, start, end in funcs:
            length = end - start + 1
            if length > threshold:
                findings.append((name, start, end, length))

    elif lang == "javascript":
        # Simple brace-counting approach
        func_starts = []
        for i, line in enumerate(lines, 1):
            m = FUNC_DEF_JS.match(line)
            if m:
                name = m.group(1) or m.group(2) or "anonymous"
                func_starts.append((name, i))
            else:
                m2 = CLASS_METHOD_JS.match(line)
                if m2 and m2.group(1) not in ("if", "else", "for", "while", "switch", "catch", "try"):
                    func_starts.append((m2.group(1), i))

        for name, start in func_starts:
            brace_count = 0
            started = False
            end = start
            for j in range(start - 1, len(lines)):
                for ch in lines[j]:
                    if ch == "{":
                        brace_count += 1
                        started = True
                    elif ch == "}":
                        brace_count -= 1
                if started and brace_count <= 0:
                    end = j + 1
                    break
            else:
                end = len(lines)
            length = end - start + 1
            if length > threshold:
                findings.append((name, start, end, length))

    return findings


def find_error_handling_issues(lines, lang):
    """Find bare except clauses, broad exception catching, empty catch blocks."""
    findings = []
    if lang == "python":
        for i, line in enumerate(lines, 1):
            if BARE_EXCEPT_PY.match(line):
                findings.append((i, "bare-except", "Bare `except:` catches all exceptions including KeyboardInterrupt"))
            elif BROAD_EXCEPT_PY.match(line):
                findings.append((i, "broad-except", "Catching bare `Exception` -- consider catching specific exception types"))
    elif lang == "javascript":
        full_text = "\n".join(lines)
        for m in EMPTY_CATCH_JS.finditer(full_text):
            line_num = full_text[:m.start()].count("\n") + 1
            findings.append((line_num, "empty-catch", "Empty catch block silently swallows errors"))
    return findings


def find_hardcoded_secrets(lines):
    """Find potential hardcoded secrets."""
    findings = []
    for i, line in enumerate(lines, 1):
        # Skip comment lines
        stripped = line.strip()
        if stripped.startswith("#") or stripped.startswith("//") or stripped.startswith("*"):
            continue
        for pattern in SECRET_PATTERNS:
            if pattern.search(line):
                # Mask the actual value
                findings.append((i, "hardcoded-secret", stripped[:80]))
                break
    return findings


def find_debug_statements(lines, lang):
    """Find debug/logging statements that should be removed before merge."""
    findings = []
    patterns = DEBUG_PATTERNS_PY if lang == "python" else DEBUG_PATTERNS_JS
    for i, line in enumerate(lines, 1):
        # Skip comment lines
        stripped = line.strip()
        if stripped.startswith("#") or stripped.startswith("//") or stripped.startswith("*"):
            continue
        for pattern in patterns:
            if pattern.search(line):
                findings.append((i, "debug-statement", stripped[:80]))
                break
    return findings


def format_findings(filepath, todos, long_funcs, error_issues, secrets, debug_stmts):
    """Format all findings as a structured checklist."""
    sections = []
    total_issues = 0

    sections.append(f"# Code Review Checklist: {os.path.basename(filepath)}")
    sections.append(f"File: `{filepath}`")
    sections.append("")

    # TODOs
    sections.append(f"## TODO/FIXME Comments ({len(todos)} found)")
    if todos:
        for line_num, tag, text in todos:
            sections.append(f"  - [ ] Line {line_num}: [{tag}] {text}")
        total_issues += len(todos)
    else:
        sections.append("  (none)")
    sections.append("")

    # Long functions
    sections.append(f"## Long Functions ({len(long_funcs)} found)")
    if long_funcs:
        for name, start, end, length in long_funcs:
            severity = "WARNING" if length <= 100 else "ERROR"
            sections.append(f"  - [ ] `{name}` (lines {start}-{end}, {length} lines) [{severity}]")
        total_issues += len(long_funcs)
    else:
        sections.append("  (none -- all functions under threshold)")
    sections.append("")

    # Error handling
    sections.append(f"## Error Handling Issues ({len(error_issues)} found)")
    if error_issues:
        for line_num, kind, desc in error_issues:
            sections.append(f"  - [ ] Line {line_num}: [{kind}] {desc}")
        total_issues += len(error_issues)
    else:
        sections.append("  (none)")
    sections.append("")

    # Hardcoded secrets
    sections.append(f"## Hardcoded Secrets ({len(secrets)} found)")
    if secrets:
        for line_num, kind, preview in secrets:
            sections.append(f"  - [ ] Line {line_num}: [{kind}] {preview}")
        total_issues += len(secrets)
    else:
        sections.append("  (none)")
    sections.append("")

    # Debug statements
    sections.append(f"## Debug Statements ({len(debug_stmts)} found)")
    if debug_stmts:
        for line_num, kind, preview in debug_stmts:
            sections.append(f"  - [ ] Line {line_num}: [{kind}] {preview}")
        total_issues += len(debug_stmts)
    else:
        sections.append("  (none)")
    sections.append("")

    # Summary
    sections.append("---")
    if total_issues == 0:
        sections.append("**Summary: No issues found. Code looks clean.**")
    else:
        sections.append(f"**Summary: {total_issues} issue(s) found across 5 categories.**")

    return "\n".join(sections)


def main():
    parser = argparse.ArgumentParser(
        description="Analyze a source file for common code review concerns.",
        epilog="Supports .py, .ts, .js, .tsx, .jsx files.",
    )
    parser.add_argument("file", help="Path to the source file to analyze")
    parser.add_argument(
        "--max-function-lines",
        type=int,
        default=50,
        help="Threshold for flagging long functions (default: 50)",
    )
    args = parser.parse_args()

    filepath = os.path.abspath(args.file)

    if not os.path.isfile(filepath):
        print(f"Error: File not found: {filepath}", file=sys.stderr)
        sys.exit(1)

    ext = os.path.splitext(filepath)[1].lower()
    if ext not in SUPPORTED_EXTENSIONS:
        print(
            f"Error: Unsupported file type '{ext}'. Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}",
            file=sys.stderr,
        )
        sys.exit(1)

    lang = detect_language(filepath)

    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except OSError as e:
        print(f"Error: Could not read file: {e}", file=sys.stderr)
        sys.exit(1)

    lines_stripped = [line.rstrip("\n") for line in lines]

    todos = find_todos(lines_stripped)
    long_funcs = find_long_functions(lines_stripped, lang, threshold=args.max_function_lines)
    error_issues = find_error_handling_issues(lines_stripped, lang)
    secrets = find_hardcoded_secrets(lines_stripped)
    debug_stmts = find_debug_statements(lines_stripped, lang)

    output = format_findings(filepath, todos, long_funcs, error_issues, secrets, debug_stmts)
    print(output)


if __name__ == "__main__":
    main()
