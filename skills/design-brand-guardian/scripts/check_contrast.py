#!/usr/bin/env python3
"""WCAG 2.1 contrast ratio checker for color pairs.

Calculates relative luminance and contrast ratios per WCAG 2.1 guidelines.
Supports individual color pairs or batch checking via JSON file.
"""

import argparse
import json
import sys


def hex_to_rgb(hex_color: str) -> tuple:
    """Convert a hex color string to an (R, G, B) tuple with values 0-255."""
    hex_color = hex_color.strip().lstrip("#")
    if len(hex_color) == 3:
        hex_color = "".join(c * 2 for c in hex_color)
    if len(hex_color) != 6:
        raise ValueError(f"Invalid hex color: '#{hex_color}'. Expected 3 or 6 hex digits.")
    try:
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
    except ValueError:
        raise ValueError(f"Invalid hex color: '#{hex_color}'. Contains non-hex characters.")
    return (r, g, b)


def relative_luminance(hex_color: str) -> float:
    """Calculate WCAG 2.1 relative luminance for a hex color.

    Formula: L = 0.2126 * R + 0.7152 * G + 0.0722 * B
    where each channel is linearized from sRGB.
    """
    r, g, b = hex_to_rgb(hex_color)
    channels = []
    for c in (r, g, b):
        s = c / 255.0
        if s <= 0.04045:
            channels.append(s / 12.92)
        else:
            channels.append(((s + 0.055) / 1.055) ** 2.4)
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]


def contrast_ratio(fg: str, bg: str) -> float:
    """Calculate WCAG 2.1 contrast ratio between two colors.

    Returns a value between 1 and 21.
    """
    l1 = relative_luminance(fg)
    l2 = relative_luminance(bg)
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def check_pair(fg: str, bg: str) -> dict:
    """Check a foreground/background color pair against WCAG criteria."""
    ratio = contrast_ratio(fg, bg)
    return {
        "foreground": fg,
        "background": bg,
        "contrast_ratio": round(ratio, 2),
        "wcag_aa_normal_text": "PASS" if ratio >= 4.5 else "FAIL",
        "wcag_aa_large_text": "PASS" if ratio >= 3.0 else "FAIL",
        "wcag_aaa_normal_text": "PASS" if ratio >= 7.0 else "FAIL",
        "wcag_aaa_large_text": "PASS" if ratio >= 4.5 else "FAIL",
    }


def format_result(result: dict) -> str:
    """Format a single contrast check result as a readable string."""
    lines = [
        f"  Foreground:           {result['foreground']}",
        f"  Background:           {result['background']}",
        f"  Contrast Ratio:       {result['contrast_ratio']}:1",
        f"  WCAG AA  Normal Text: {result['wcag_aa_normal_text']}  (>= 4.5:1)",
        f"  WCAG AA  Large Text:  {result['wcag_aa_large_text']}  (>= 3.0:1)",
        f"  WCAG AAA Normal Text: {result['wcag_aaa_normal_text']}  (>= 7.0:1)",
        f"  WCAG AAA Large Text:  {result['wcag_aaa_large_text']}  (>= 4.5:1)",
    ]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="WCAG 2.1 contrast ratio checker. Validates color pairs against AA and AAA criteria."
    )
    parser.add_argument(
        "--fg",
        type=str,
        help='Foreground color as hex (e.g., "#0F172A" or "0F172A")',
    )
    parser.add_argument(
        "--bg",
        type=str,
        help='Background color as hex (e.g., "#FFFFFF" or "FFF")',
    )
    parser.add_argument(
        "--file",
        type=str,
        help='Path to a JSON file with color pairs. Format: [{"fg": "#000", "bg": "#FFF"}, ...]',
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="output_json",
        help="Output results as JSON instead of human-readable text",
    )

    args = parser.parse_args()

    if not args.file and not (args.fg and args.bg):
        parser.error("Provide either --fg and --bg, or --file with a JSON file of color pairs.")

    results = []

    if args.file:
        try:
            with open(args.file, "r") as f:
                pairs = json.load(f)
        except FileNotFoundError:
            print(f"Error: File not found: {args.file}", file=sys.stderr)
            sys.exit(1)
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON in {args.file}: {e}", file=sys.stderr)
            sys.exit(1)

        if not isinstance(pairs, list):
            print("Error: JSON file must contain a list of objects with 'fg' and 'bg' keys.", file=sys.stderr)
            sys.exit(1)

        for i, pair in enumerate(pairs):
            if not isinstance(pair, dict) or "fg" not in pair or "bg" not in pair:
                print(f"Error: Entry {i} must be an object with 'fg' and 'bg' keys.", file=sys.stderr)
                sys.exit(1)
            try:
                results.append(check_pair(pair["fg"], pair["bg"]))
            except ValueError as e:
                print(f"Error in entry {i}: {e}", file=sys.stderr)
                sys.exit(1)
    else:
        try:
            results.append(check_pair(args.fg, args.bg))
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    if args.output_json:
        print(json.dumps(results, indent=2))
    else:
        for i, result in enumerate(results):
            if len(results) > 1:
                print(f"--- Pair {i + 1} ---")
            print(format_result(result))
            if i < len(results) - 1:
                print()

    # Exit with non-zero status if any pair fails AA normal text
    if any(r["wcag_aa_normal_text"] == "FAIL" for r in results):
        sys.exit(1)


if __name__ == "__main__":
    main()
