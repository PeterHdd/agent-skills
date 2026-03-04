#!/usr/bin/env python3
"""Parse a requirements document and extract structured information.

Extracts numbered requirements, user stories (As a... I want... So that...),
acceptance criteria, and dependencies from markdown or plain text documents.
Outputs a structured Markdown summary with counts.
"""

import argparse
import os
import re
import sys


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


def extract_numbered_requirements(content):
    """Extract numbered requirements from the document.

    Matches lines like:
      1. The system shall...
      REQ-001: ...
      R1: ...
      1) ...
    """
    requirements = []
    lines = content.splitlines()

    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        # Match "REQ-NNN:" or "R-NNN:" style
        req_match = re.match(r'^(REQ[-_]?\d+|R[-_]?\d+)\s*[:\.]\s*(.+)', stripped, re.IGNORECASE)
        if req_match:
            requirements.append({
                "id": req_match.group(1),
                "text": req_match.group(2).strip(),
                "line": i,
            })
            continue

        # Match numbered list items like "1. ..." or "1) ..."
        num_match = re.match(r'^(\d+)[.)]\s+(.+)', stripped)
        if num_match:
            text = num_match.group(2).strip()
            # Only include if it looks like a requirement (has keywords or is substantial)
            if len(text) > 15:
                requirements.append({
                    "id": f"#{num_match.group(1)}",
                    "text": text,
                    "line": i,
                })

    return requirements


def extract_user_stories(content):
    """Extract user stories matching the pattern: As a... I want... So that..."""
    stories = []
    lines = content.splitlines()

    # Single-line pattern
    single_pattern = re.compile(
        r'[Aa]s\s+(?:a|an)\s+(.+?),?\s+[Ii]\s+want\s+(.+?)(?:,?\s+[Ss]o\s+that\s+(.+))?$'
    )

    # Try single-line matches first
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        # Remove leading list markers
        cleaned = re.sub(r'^[-*+]\s+', '', stripped)
        cleaned = re.sub(r'^\d+[.)]\s+', '', cleaned)

        match = single_pattern.match(cleaned)
        if match:
            story = {
                "role": match.group(1).strip().rstrip(","),
                "want": match.group(2).strip().rstrip(","),
                "so_that": match.group(3).strip().rstrip(".") if match.group(3) else None,
                "line": i,
                "raw": cleaned,
            }
            stories.append(story)
            continue

    # Try multi-line: look for "As a" and then scan next lines for "I want" / "So that"
    for i, line in enumerate(lines):
        stripped = line.strip()
        cleaned = re.sub(r'^[-*+]\s+', '', stripped)
        cleaned = re.sub(r'^\d+[.)]\s+', '', cleaned)

        as_match = re.match(r'^[Aa]s\s+(?:a|an)\s+(.+?)(?:,?\s*)$', cleaned)
        if as_match and i + 1 < len(lines):
            role = as_match.group(1).strip().rstrip(",")
            want = None
            so_that = None

            # Check next lines
            for j in range(i + 1, min(i + 4, len(lines))):
                next_line = lines[j].strip()
                want_match = re.match(r'^[Ii]\s+want\s+(.+?)(?:,?\s*)$', next_line)
                so_match = re.match(r'^[Ss]o\s+that\s+(.+)$', next_line)
                if want_match:
                    want = want_match.group(1).strip().rstrip(",")
                if so_match:
                    so_that = so_match.group(1).strip().rstrip(".")

            if want:
                # Check we haven't already captured this as a single-line story
                already_found = any(s["line"] == i + 1 for s in stories)
                if not already_found:
                    stories.append({
                        "role": role,
                        "want": want,
                        "so_that": so_that,
                        "line": i + 1,
                        "raw": cleaned,
                    })

    return stories


def extract_acceptance_criteria(content):
    """Extract acceptance criteria from the document.

    Looks for:
    - Checkbox items: - [ ] or - [x]
    - Items under "Acceptance Criteria" or "Definition of Done" headings
    - "Given/When/Then" patterns
    """
    criteria = []
    lines = content.splitlines()
    in_ac_section = False
    current_section = "General"

    for i, line in enumerate(lines, 1):
        stripped = line.strip()

        # Track headings
        heading_match = re.match(r'^(#{1,6})\s+(.+)$', stripped)
        if heading_match:
            heading_text = heading_match.group(2).strip()
            current_section = heading_text
            lower_heading = heading_text.lower()
            in_ac_section = any(
                kw in lower_heading
                for kw in ["acceptance criteria", "definition of done", "done criteria",
                           "acceptance", "success criteria", "exit criteria"]
            )
            continue

        # Checkbox items anywhere
        checkbox_match = re.match(r'^[-*+]\s*\[([ xX])\]\s+(.+)$', stripped)
        if checkbox_match:
            checked = checkbox_match.group(1).lower() == "x"
            criteria.append({
                "text": checkbox_match.group(2).strip(),
                "checked": checked,
                "type": "checkbox",
                "section": current_section,
                "line": i,
            })
            continue

        # Given/When/Then patterns
        gwt_match = re.match(r'^(Given|When|Then|And)\s+(.+)', stripped, re.IGNORECASE)
        if gwt_match:
            criteria.append({
                "text": stripped,
                "checked": False,
                "type": "gherkin",
                "section": current_section,
                "line": i,
            })
            continue

        # List items under AC section
        if in_ac_section:
            list_match = re.match(r'^[-*+]\s+(.+)$', stripped)
            num_match = re.match(r'^\d+[.)]\s+(.+)$', stripped)
            if list_match:
                criteria.append({
                    "text": list_match.group(1).strip(),
                    "checked": False,
                    "type": "list",
                    "section": current_section,
                    "line": i,
                })
            elif num_match:
                criteria.append({
                    "text": num_match.group(1).strip(),
                    "checked": False,
                    "type": "numbered",
                    "section": current_section,
                    "line": i,
                })

    return criteria


def extract_dependencies(content):
    """Extract dependency mentions from the document.

    Looks for:
    - Explicit "depends on", "dependency", "requires", "prerequisite", "blocked by"
    - Lines under "Dependencies" headings
    """
    dependencies = []
    lines = content.splitlines()
    in_dep_section = False

    dep_patterns = [
        re.compile(r'(?:depends?\s+on|dependency|prerequisite|blocked\s+by|requires)\s*[:\-]?\s*(.+)',
                    re.IGNORECASE),
    ]

    for i, line in enumerate(lines, 1):
        stripped = line.strip()

        # Track dependency section headings
        heading_match = re.match(r'^(#{1,6})\s+(.+)$', stripped)
        if heading_match:
            heading_text = heading_match.group(2).strip().lower()
            in_dep_section = any(
                kw in heading_text
                for kw in ["dependencies", "dependency", "prerequisites", "blockers"]
            )
            continue

        # Check for dependency patterns
        for pattern in dep_patterns:
            match = pattern.search(stripped)
            if match:
                dependencies.append({
                    "text": match.group(1).strip(),
                    "line": i,
                    "raw": stripped,
                })
                break
        else:
            # If in a dependencies section, capture list items
            if in_dep_section:
                list_match = re.match(r'^[-*+]\s+(.+)$', stripped)
                num_match = re.match(r'^\d+[.)]\s+(.+)$', stripped)
                if list_match:
                    dependencies.append({
                        "text": list_match.group(1).strip(),
                        "line": i,
                        "raw": stripped,
                    })
                elif num_match:
                    dependencies.append({
                        "text": num_match.group(1).strip(),
                        "line": i,
                        "raw": stripped,
                    })

    return dependencies


def format_markdown(requirements, stories, criteria, dependencies, filepath):
    """Format extracted data as a Markdown summary."""
    lines = []
    lines.append("# Requirements Analysis Report")
    lines.append("")
    lines.append(f"**Source:** `{filepath}`")
    lines.append("")

    # Summary counts
    lines.append("## Summary")
    lines.append("")
    lines.append(f"| Category | Count |")
    lines.append(f"|----------|-------|")
    lines.append(f"| Numbered requirements | {len(requirements)} |")
    lines.append(f"| User stories | {len(stories)} |")
    lines.append(f"| Acceptance criteria | {len(criteria)} |")
    lines.append(f"| Dependencies | {len(dependencies)} |")
    lines.append("")

    # Numbered Requirements
    lines.append("## Numbered Requirements")
    lines.append("")
    if requirements:
        for req in requirements:
            lines.append(f"- **{req['id']}** (line {req['line']}): {req['text']}")
    else:
        lines.append("_No numbered requirements found._")
    lines.append("")

    # User Stories
    lines.append("## User Stories")
    lines.append("")
    if stories:
        for idx, story in enumerate(stories, 1):
            lines.append(f"### Story {idx} (line {story['line']})")
            lines.append("")
            lines.append(f"- **As a** {story['role']}")
            lines.append(f"- **I want** {story['want']}")
            if story["so_that"]:
                lines.append(f"- **So that** {story['so_that']}")
            lines.append("")
    else:
        lines.append("_No user stories found._")
    lines.append("")

    # Acceptance Criteria
    lines.append("## Acceptance Criteria")
    lines.append("")
    if criteria:
        checked_count = sum(1 for c in criteria if c["checked"])
        total_count = len(criteria)
        lines.append(f"**Progress:** {checked_count}/{total_count} completed")
        lines.append("")
        for ac in criteria:
            mark = "[x]" if ac["checked"] else "[ ]"
            lines.append(f"- {mark} {ac['text']} _(line {ac['line']}, {ac['section']})_")
    else:
        lines.append("_No acceptance criteria found._")
    lines.append("")

    # Dependencies
    lines.append("## Dependencies")
    lines.append("")
    if dependencies:
        for dep in dependencies:
            lines.append(f"- {dep['text']} _(line {dep['line']})_")
    else:
        lines.append("_No dependencies found._")
    lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Parse a requirements document and extract structured information.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
examples:
  %(prog)s requirements.md
  %(prog)s spec.txt
  %(prog)s docs/PRD.md
""",
    )
    parser.add_argument(
        "file",
        help="Path to the requirements document (markdown or plain text)",
    )

    args = parser.parse_args()

    if not os.path.isfile(args.file):
        print(f"Error: File not found: {args.file}", file=sys.stderr)
        sys.exit(1)

    content = read_file(args.file)

    if not content.strip():
        print("Error: Input file is empty.", file=sys.stderr)
        sys.exit(1)

    requirements = extract_numbered_requirements(content)
    stories = extract_user_stories(content)
    criteria = extract_acceptance_criteria(content)
    dependencies = extract_dependencies(content)

    output = format_markdown(requirements, stories, criteria, dependencies, args.file)
    print(output)


if __name__ == "__main__":
    main()
