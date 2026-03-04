#!/usr/bin/env python3
"""Generate a complete design token color scale from a primary color.

Produces CSS custom properties for a full color scale (50-900), neutral scale,
and semantic colors (success, warning, error, info) based on a single primary
hex color input.
"""

import argparse
import colorsys
import json
import sys


def hex_to_rgb(hex_color: str) -> tuple:
    """Convert hex color to (R, G, B) tuple with values 0-255."""
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


def rgb_to_hex(r: int, g: int, b: int) -> str:
    """Convert RGB values (0-255) to hex string."""
    return f"#{r:02X}{g:02X}{b:02X}"


def rgb_to_hsl(r: int, g: int, b: int) -> tuple:
    """Convert RGB (0-255) to HSL (h: 0-360, s: 0-100, l: 0-100)."""
    h, l, s = colorsys.rgb_to_hls(r / 255.0, g / 255.0, b / 255.0)
    return (h * 360, s * 100, l * 100)


def hsl_to_rgb(h: float, s: float, l: float) -> tuple:
    """Convert HSL (h: 0-360, s: 0-100, l: 0-100) to RGB (0-255)."""
    r, g, b = colorsys.hls_to_rgb(h / 360.0, l / 100.0, s / 100.0)
    return (
        max(0, min(255, round(r * 255))),
        max(0, min(255, round(g * 255))),
        max(0, min(255, round(b * 255))),
    )


def generate_scale(h: float, s: float, base_l: float) -> dict:
    """Generate a 50-900 color scale by adjusting lightness.

    The scale maps:
      50  -> very light (95% lightness)
      100 -> light (90%)
      200 -> 80%
      ...
      500 -> base lightness (close to input)
      ...
      900 -> very dark (15%)
    """
    # Lightness targets for each step
    lightness_map = {
        50: 97,
        100: 94,
        200: 86,
        300: 74,
        400: 60,
        500: 48,
        600: 40,
        700: 32,
        800: 24,
        900: 15,
    }

    # Slightly adjust saturation for very light and very dark shades
    scale = {}
    for step, target_l in lightness_map.items():
        # Desaturate extremes slightly for more natural palette
        if target_l > 90:
            adj_s = s * 0.6
        elif target_l > 80:
            adj_s = s * 0.75
        elif target_l < 20:
            adj_s = s * 0.8
        else:
            adj_s = s

        r, g, b = hsl_to_rgb(h, adj_s, target_l)
        scale[step] = rgb_to_hex(r, g, b)

    return scale


def generate_neutral_scale() -> dict:
    """Generate a neutral (gray) scale from 50-900."""
    lightness_map = {
        50: 98,
        100: 96,
        200: 90,
        300: 82,
        400: 64,
        500: 46,
        600: 38,
        700: 28,
        800: 18,
        900: 10,
    }
    scale = {}
    for step, l in lightness_map.items():
        r, g, b = hsl_to_rgb(220, 8, l)
        scale[step] = rgb_to_hex(r, g, b)
    return scale


def generate_semantic_colors() -> dict:
    """Generate semantic color tokens (success, warning, error, info)."""
    semantics = {
        "success": {"h": 142, "s": 72, "l": 42},
        "success-light": {"h": 142, "s": 72, "l": 94},
        "warning": {"h": 38, "s": 92, "l": 50},
        "warning-light": {"h": 38, "s": 92, "l": 94},
        "error": {"h": 0, "s": 84, "l": 52},
        "error-light": {"h": 0, "s": 84, "l": 94},
        "info": {"h": 210, "s": 80, "l": 52},
        "info-light": {"h": 210, "s": 80, "l": 94},
    }
    result = {}
    for name, hsl in semantics.items():
        r, g, b = hsl_to_rgb(hsl["h"], hsl["s"], hsl["l"])
        result[name] = rgb_to_hex(r, g, b)
    return result


def format_css(primary_scale: dict, neutral_scale: dict, semantic: dict, primary_hex: str) -> str:
    """Format all tokens as CSS custom properties."""
    lines = [
        "/* ==========================================================",
        f"   Design Tokens — Generated from primary: {primary_hex}",
        "   ========================================================== */",
        "",
        ":root {",
        "  /* --- Primary Scale --- */",
    ]

    for step, color in sorted(primary_scale.items()):
        lines.append(f"  --color-primary-{step}: {color};")

    lines.append("")
    lines.append("  /* --- Neutral Scale --- */")

    for step, color in sorted(neutral_scale.items()):
        lines.append(f"  --color-neutral-{step}: {color};")

    lines.append("")
    lines.append("  /* --- Semantic Colors --- */")

    for name, color in semantic.items():
        lines.append(f"  --color-{name}: {color};")

    lines.append("}")
    lines.append("")
    return "\n".join(lines)


def format_json(primary_scale: dict, neutral_scale: dict, semantic: dict) -> str:
    """Format all tokens as a JSON object."""
    output = {
        "primary": {str(k): v for k, v in sorted(primary_scale.items())},
        "neutral": {str(k): v for k, v in sorted(neutral_scale.items())},
        "semantic": semantic,
    }
    return json.dumps(output, indent=2)


def main():
    parser = argparse.ArgumentParser(
        description="Generate a full design token color scale from a primary color hex value."
    )
    parser.add_argument(
        "color",
        type=str,
        help='Primary color as hex (e.g., "#3B82F6" or "3B82F6")',
    )
    parser.add_argument(
        "--format",
        choices=["css", "json"],
        default="css",
        help="Output format: css (default) or json",
    )
    parser.add_argument(
        "--no-neutral",
        action="store_true",
        help="Skip generating the neutral scale",
    )
    parser.add_argument(
        "--no-semantic",
        action="store_true",
        help="Skip generating semantic colors",
    )

    args = parser.parse_args()

    try:
        r, g, b = hex_to_rgb(args.color)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    h, s, l = rgb_to_hsl(r, g, b)
    primary_scale = generate_scale(h, s, l)
    neutral_scale = {} if args.no_neutral else generate_neutral_scale()
    semantic = {} if args.no_semantic else generate_semantic_colors()

    if args.format == "json":
        output = {
            "primary": {str(k): v for k, v in sorted(primary_scale.items())},
        }
        if neutral_scale:
            output["neutral"] = {str(k): v for k, v in sorted(neutral_scale.items())}
        if semantic:
            output["semantic"] = semantic
        print(json.dumps(output, indent=2))
    else:
        print(format_css(primary_scale, neutral_scale, semantic, args.color))


if __name__ == "__main__":
    main()
