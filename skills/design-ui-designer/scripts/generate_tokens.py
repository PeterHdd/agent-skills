#!/usr/bin/env python3
"""Generate CSS custom properties from a JSON token definition file.

Takes a JSON file with design tokens (colors, spacing, typography, borders,
shadows, etc.) and outputs a complete :root {} CSS block with custom
properties. Supports a --dark flag to generate a [data-theme="dark"] block.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List


def flatten_tokens(obj: Any, prefix: str = "") -> List[tuple]:
    """Recursively flatten a nested token object into (name, value) pairs.

    Example:
        {"colors": {"primary-500": "#3B82F6"}}
        -> [("colors-primary-500", "#3B82F6")]
    """
    pairs = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            new_prefix = f"{prefix}-{key}" if prefix else key
            if isinstance(value, dict):
                # Check if this is a "leaf" token with a $value key (DTCG format)
                if "$value" in value:
                    pairs.append((new_prefix, str(value["$value"])))
                else:
                    pairs.extend(flatten_tokens(value, new_prefix))
            else:
                pairs.append((new_prefix, str(value)))
    return pairs


def sanitize_property_name(name: str) -> str:
    """Convert a token name to a valid CSS custom property name.

    Replaces spaces and underscores with hyphens, lowercases, and
    strips any characters that are not alphanumeric, hyphens, or dots.
    """
    name = name.replace(" ", "-").replace("_", "-")
    name = name.lower()
    # Remove characters invalid in CSS custom property names
    cleaned = ""
    for ch in name:
        if ch.isalnum() or ch in ("-", "."):
            cleaned += ch
    # Collapse multiple hyphens
    while "--" in cleaned and not cleaned.startswith("--"):
        cleaned = cleaned.replace("--", "-")
    return cleaned


def generate_root_block(tokens: Dict[str, Any]) -> str:
    """Generate a :root {} CSS block from a token dictionary."""
    pairs = flatten_tokens(tokens)
    if not pairs:
        return ":root {\n  /* No tokens defined */\n}\n"

    lines = []
    lines.append(":root {")

    current_section = None
    for raw_name, value in pairs:
        # Detect section from the top-level key
        section = raw_name.split("-")[0] if "-" in raw_name else raw_name
        if section != current_section:
            if current_section is not None:
                lines.append("")
            lines.append(f"  /* {section} */")
            current_section = section

        prop_name = sanitize_property_name(raw_name)
        lines.append(f"  --{prop_name}: {value};")

    lines.append("}")
    return "\n".join(lines) + "\n"


def generate_dark_block(tokens: Dict[str, Any]) -> str:
    """Generate a [data-theme=\"dark\"] CSS block from a token dictionary."""
    pairs = flatten_tokens(tokens)
    if not pairs:
        return '[data-theme="dark"] {\n  /* No tokens defined */\n}\n'

    lines = []
    lines.append('[data-theme="dark"] {')

    current_section = None
    for raw_name, value in pairs:
        section = raw_name.split("-")[0] if "-" in raw_name else raw_name
        if section != current_section:
            if current_section is not None:
                lines.append("")
            lines.append(f"  /* {section} */")
            current_section = section

        prop_name = sanitize_property_name(raw_name)
        lines.append(f"  --{prop_name}: {value};")

    lines.append("}")
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Generate CSS custom properties from a JSON token definition file. "
            "Outputs a :root {} block with --token-name: value; declarations. "
            "Use --dark to generate a [data-theme=\"dark\"] block instead."
        )
    )
    parser.add_argument(
        "token_file",
        help=(
            'Path to a JSON file with token definitions. '
            'Example structure: {"colors": {"primary-500": "#3B82F6"}, '
            '"spacing": {"4": "1rem"}, "typography": {"base": "1rem"}}'
        ),
    )
    parser.add_argument(
        "--dark",
        action="store_true",
        help='Generate a [data-theme="dark"] block instead of :root',
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default=None,
        help="Write output to a file instead of stdout",
    )
    parser.add_argument(
        "--header",
        action="store_true",
        help="Include a generated-by comment header in the output",
    )

    args = parser.parse_args()

    token_path = Path(args.token_file)
    if not token_path.exists():
        print(f"Error: Token file not found: {args.token_file}", file=sys.stderr)
        sys.exit(1)
    if not token_path.is_file():
        print(f"Error: Path is not a file: {args.token_file}", file=sys.stderr)
        sys.exit(1)

    try:
        with open(token_path, "r", encoding="utf-8") as f:
            tokens = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in token file: {e}", file=sys.stderr)
        sys.exit(1)

    if not isinstance(tokens, dict):
        print("Error: Token file must contain a JSON object at the top level.", file=sys.stderr)
        sys.exit(1)

    if not tokens:
        print("Warning: Token file is empty.", file=sys.stderr)

    # Build output
    output_parts = []

    if args.header:
        output_parts.append("/* ==============================================")
        output_parts.append("   Design Tokens - CSS Custom Properties")
        output_parts.append("   Generated by generate_tokens.py")
        output_parts.append("   ============================================== */")
        output_parts.append("")

    if args.dark:
        output_parts.append(generate_dark_block(tokens))
    else:
        output_parts.append(generate_root_block(tokens))

    output = "\n".join(output_parts)

    if args.output:
        try:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(output, encoding="utf-8")
            print(f"Written to: {output_path.resolve()}", file=sys.stderr)
        except OSError as e:
            print(f"Error: Could not write output file: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        print(output, end="")


if __name__ == "__main__":
    main()
