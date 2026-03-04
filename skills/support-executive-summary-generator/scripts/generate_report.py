#!/usr/bin/env python3
"""Generate an executive summary structure from a markdown/text input file.

Extracts headers, key metrics (numbers/percentages), action items (lines with
action verbs), and produces a formatted executive summary template.
Output is structured Markdown.
"""

import argparse
import os
import re
import sys


ACTION_VERBS = {
    "implement", "deploy", "create", "build", "develop", "design", "update",
    "upgrade", "migrate", "fix", "resolve", "address", "improve", "optimize",
    "reduce", "increase", "ensure", "establish", "launch", "deliver", "complete",
    "review", "investigate", "analyze", "evaluate", "assess", "monitor",
    "schedule", "plan", "coordinate", "assign", "delegate", "follow",
    "track", "report", "document", "test", "validate", "verify", "approve",
    "finalize", "submit", "send", "prepare", "configure", "setup", "set up",
    "install", "remove", "delete", "refactor", "replace", "add", "integrate",
    "automate", "scale", "prioritize", "escalate", "contact", "notify",
    "communicate", "present", "propose", "recommend", "define", "draft",
    "hire", "train", "onboard", "audit", "backup", "restore", "patch",
}


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


def extract_headers(content):
    """Extract markdown headers with their levels and text."""
    headers = []
    for i, line in enumerate(content.splitlines(), 1):
        match = re.match(r'^(#{1,6})\s+(.+)$', line.strip())
        if match:
            level = len(match.group(1))
            text = match.group(2).strip()
            headers.append({"level": level, "text": text, "line": i})
    return headers


def extract_metrics(content):
    """Extract key metrics -- numbers, percentages, dollar amounts, and dates.

    Looks for lines containing significant numerical data.
    """
    metrics = []
    lines = content.splitlines()

    patterns = [
        # Percentages: "95%", "increased by 30%"
        (re.compile(r'(\d+(?:\.\d+)?)\s*%'), "percentage"),
        # Dollar/currency amounts: "$1,000", "$5M"
        (re.compile(r'\$[\d,]+(?:\.\d+)?(?:\s*[KkMmBb](?:illion)?)?'), "currency"),
        # Large numbers with context: "10,000 users", "500 requests"
        (re.compile(r'(\d{1,3}(?:,\d{3})+)'), "number"),
        # Multipliers: "2x", "10x"
        (re.compile(r'\b(\d+(?:\.\d+)?)\s*[xX]\b'), "multiplier"),
        # Time durations: "3 hours", "2 weeks", "6 months"
        (re.compile(r'\b(\d+)\s+(hours?|days?|weeks?|months?|years?|minutes?|seconds?)\b',
                     re.IGNORECASE), "duration"),
    ]

    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if not stripped:
            continue

        for pattern, metric_type in patterns:
            matches = pattern.findall(stripped)
            if matches:
                # Get the full match context
                for match in pattern.finditer(stripped):
                    # Extract surrounding context (up to 60 chars around match)
                    start = max(0, match.start() - 30)
                    end = min(len(stripped), match.end() + 30)
                    context = stripped[start:end].strip()
                    if start > 0:
                        context = "..." + context
                    if end < len(stripped):
                        context = context + "..."

                    metrics.append({
                        "value": match.group(0),
                        "type": metric_type,
                        "context": context,
                        "line": i,
                        "full_line": stripped,
                    })
                break  # Only match first pattern per line

    # Deduplicate by line number (one metric per line)
    seen_lines = set()
    unique_metrics = []
    for m in metrics:
        if m["line"] not in seen_lines:
            seen_lines.add(m["line"])
            unique_metrics.append(m)

    return unique_metrics


def extract_action_items(content):
    """Extract action items -- lines starting with - or * that contain action verbs."""
    action_items = []
    lines = content.splitlines()

    for i, line in enumerate(lines, 1):
        stripped = line.strip()

        # Must start with - or *
        list_match = re.match(r'^[-*+]\s+(.+)$', stripped)
        if not list_match:
            continue

        item_text = list_match.group(1).strip()
        item_lower = item_text.lower()

        # Check for action verbs
        found_verb = None
        for verb in ACTION_VERBS:
            # Match as whole word
            if re.search(r'\b' + re.escape(verb) + r'\b', item_lower):
                found_verb = verb
                break

        if found_verb:
            # Determine priority hints
            priority = "normal"
            priority_lower = item_lower
            if any(w in priority_lower for w in ["urgent", "critical", "asap", "immediately", "blocker"]):
                priority = "high"
            elif any(w in priority_lower for w in ["important", "must", "required", "shall"]):
                priority = "high"
            elif any(w in priority_lower for w in ["nice to have", "optional", "consider", "could"]):
                priority = "low"

            action_items.append({
                "text": item_text,
                "verb": found_verb,
                "priority": priority,
                "line": i,
            })

    return action_items


def format_markdown(headers, metrics, action_items, filepath):
    """Format the executive summary as Markdown."""
    lines = []
    lines.append("# Executive Summary")
    lines.append("")
    lines.append(f"**Source document:** `{filepath}`")
    lines.append("")

    # Overview section from headers
    lines.append("## Document Structure")
    lines.append("")
    if headers:
        for h in headers:
            indent = "  " * (h["level"] - 1)
            lines.append(f"{indent}- {h['text']}")
    else:
        lines.append("_No section headers found in the document._")
    lines.append("")

    # Key Metrics
    lines.append("## Key Metrics")
    lines.append("")
    if metrics:
        lines.append("| Metric | Type | Context | Line |")
        lines.append("|--------|------|---------|------|")
        for m in metrics:
            # Escape pipe characters in context
            context = m["context"].replace("|", "\\|")
            lines.append(f"| {m['value']} | {m['type']} | {context} | {m['line']} |")
    else:
        lines.append("_No key metrics (numbers, percentages, amounts) found._")
    lines.append("")

    # Action Items
    lines.append("## Action Items")
    lines.append("")
    if action_items:
        high_items = [a for a in action_items if a["priority"] == "high"]
        normal_items = [a for a in action_items if a["priority"] == "normal"]
        low_items = [a for a in action_items if a["priority"] == "low"]

        if high_items:
            lines.append("### High Priority")
            lines.append("")
            for item in high_items:
                lines.append(f"- [ ] {item['text']} _(line {item['line']})_")
            lines.append("")

        if normal_items:
            lines.append("### Normal Priority")
            lines.append("")
            for item in normal_items:
                lines.append(f"- [ ] {item['text']} _(line {item['line']})_")
            lines.append("")

        if low_items:
            lines.append("### Low Priority")
            lines.append("")
            for item in low_items:
                lines.append(f"- [ ] {item['text']} _(line {item['line']})_")
            lines.append("")
    else:
        lines.append("_No action items found._")
    lines.append("")

    # Summary statistics
    lines.append("## Summary Statistics")
    lines.append("")
    lines.append(f"| Category | Count |")
    lines.append(f"|----------|-------|")
    lines.append(f"| Document sections | {len(headers)} |")
    lines.append(f"| Key metrics found | {len(metrics)} |")
    lines.append(f"| Action items | {len(action_items)} |")
    high_count = sum(1 for a in action_items if a["priority"] == "high")
    lines.append(f"| High priority actions | {high_count} |")
    lines.append("")

    # Executive Summary Template
    lines.append("---")
    lines.append("")
    lines.append("## Executive Summary Template")
    lines.append("")
    lines.append("_Use the following template to draft your executive summary:_")
    lines.append("")
    lines.append("### Purpose")
    lines.append("")
    lines.append("[Describe the purpose of this document/initiative based on the headers above]")
    lines.append("")
    lines.append("### Key Findings")
    lines.append("")
    if metrics:
        for m in metrics[:5]:  # Top 5 metrics
            lines.append(f"- {m['full_line'].strip()}")
    else:
        lines.append("- [Insert key finding 1]")
        lines.append("- [Insert key finding 2]")
    lines.append("")
    lines.append("### Recommended Actions")
    lines.append("")
    if action_items:
        for item in action_items[:5]:  # Top 5 action items
            lines.append(f"1. {item['text']}")
    else:
        lines.append("1. [Insert recommended action 1]")
        lines.append("2. [Insert recommended action 2]")
    lines.append("")
    lines.append("### Next Steps")
    lines.append("")
    lines.append("[Outline the immediate next steps and timeline]")
    lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Generate an executive summary structure from a markdown/text input file.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Extracts from the input document:
  - Section headers (document structure)
  - Key metrics (numbers, percentages, dollar amounts)
  - Action items (bullet points with action verbs)

examples:
  %(prog)s report.md
  %(prog)s meeting_notes.txt
  %(prog)s quarterly_review.md
""",
    )
    parser.add_argument(
        "file",
        help="Path to the input file (markdown or plain text)",
    )

    args = parser.parse_args()

    if not os.path.isfile(args.file):
        print(f"Error: File not found: {args.file}", file=sys.stderr)
        sys.exit(1)

    content = read_file(args.file)

    if not content.strip():
        print("Error: Input file is empty.", file=sys.stderr)
        sys.exit(1)

    headers = extract_headers(content)
    metrics = extract_metrics(content)
    action_items = extract_action_items(content)

    output = format_markdown(headers, metrics, action_items, args.file)
    print(output)


if __name__ == "__main__":
    main()
