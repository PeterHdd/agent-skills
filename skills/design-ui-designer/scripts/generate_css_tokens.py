#!/usr/bin/env python3
"""Generate complete CSS custom properties from a JSON design config.

Takes a JSON config file with color palette, font families, and spacing base,
then generates a full :root CSS custom properties block with light theme,
dark theme override, typography scale, and spacing scale.
"""

import argparse
import json
import sys
import colorsys


def hex_to_rgb(hex_color: str) -> tuple:
    """Convert hex color to (R, G, B) tuple with values 0-255."""
    hex_color = hex_color.strip().lstrip("#")
    if len(hex_color) == 3:
        hex_color = "".join(c * 2 for c in hex_color)
    if len(hex_color) != 6:
        raise ValueError(f"Invalid hex color: '#{hex_color}'")
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    return (r, g, b)


def rgb_to_hex(r: int, g: int, b: int) -> str:
    """Convert RGB (0-255) to hex string."""
    return f"#{max(0, min(255, r)):02X}{max(0, min(255, g)):02X}{max(0, min(255, b)):02X}"


def lighten(hex_color: str, amount: float) -> str:
    """Lighten a hex color by a percentage (0.0 - 1.0)."""
    r, g, b = hex_to_rgb(hex_color)
    h, l, s = colorsys.rgb_to_hls(r / 255.0, g / 255.0, b / 255.0)
    l = min(1.0, l + amount)
    r2, g2, b2 = colorsys.hls_to_rgb(h, l, s)
    return rgb_to_hex(round(r2 * 255), round(g2 * 255), round(b2 * 255))


def darken(hex_color: str, amount: float) -> str:
    """Darken a hex color by a percentage (0.0 - 1.0)."""
    r, g, b = hex_to_rgb(hex_color)
    h, l, s = colorsys.rgb_to_hls(r / 255.0, g / 255.0, b / 255.0)
    l = max(0.0, l - amount)
    r2, g2, b2 = colorsys.hls_to_rgb(h, l, s)
    return rgb_to_hex(round(r2 * 255), round(g2 * 255), round(b2 * 255))


def generate_typography_scale(base_size: float, font_families: dict) -> list:
    """Generate a type scale using a 1.25 ratio (Major Third)."""
    ratio = 1.25
    steps = {
        "xs": -2,
        "sm": -1,
        "base": 0,
        "md": 1,
        "lg": 2,
        "xl": 3,
        "2xl": 4,
        "3xl": 5,
        "4xl": 6,
    }

    lines = []
    lines.append("  /* --- Typography --- */")

    # Font families
    for name, stack in font_families.items():
        lines.append(f"  --font-{name}: {stack};")
    lines.append("")

    # Font sizes
    for step_name, exp in sorted(steps.items(), key=lambda x: x[1]):
        size = round(base_size * (ratio ** exp), 2)
        lines.append(f"  --font-size-{step_name}: {size}rem;")

    # Line heights
    lines.append("")
    lines.append("  --line-height-tight: 1.25;")
    lines.append("  --line-height-normal: 1.5;")
    lines.append("  --line-height-relaxed: 1.75;")

    # Font weights
    lines.append("")
    lines.append("  --font-weight-normal: 400;")
    lines.append("  --font-weight-medium: 500;")
    lines.append("  --font-weight-semibold: 600;")
    lines.append("  --font-weight-bold: 700;")

    return lines


def generate_spacing_scale(base: int) -> list:
    """Generate a spacing scale on a base grid."""
    lines = []
    lines.append("  /* --- Spacing --- */")

    multipliers = {
        "0": 0,
        "1": 0.25,
        "2": 0.5,
        "3": 1,
        "4": 1.5,
        "5": 2,
        "6": 3,
        "8": 4,
        "10": 5,
        "12": 6,
        "16": 8,
        "20": 10,
        "24": 12,
    }

    for name, mult in multipliers.items():
        px = round(base * mult)
        lines.append(f"  --space-{name}: {px}px;")

    return lines


def generate_shadow_tokens() -> list:
    """Generate elevation shadow tokens."""
    return [
        "  /* --- Shadows --- */",
        "  --shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.05);",
        "  --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -2px rgba(0, 0, 0, 0.1);",
        "  --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -4px rgba(0, 0, 0, 0.1);",
        "  --shadow-xl: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.1);",
    ]


def generate_motion_tokens() -> list:
    """Generate motion/animation tokens."""
    return [
        "  /* --- Motion --- */",
        "  --duration-fast: 100ms;",
        "  --duration-normal: 200ms;",
        "  --duration-slow: 300ms;",
        "  --duration-slower: 500ms;",
        "  --ease-in: cubic-bezier(0.4, 0, 1, 1);",
        "  --ease-out: cubic-bezier(0, 0, 0.2, 1);",
        "  --ease-in-out: cubic-bezier(0.4, 0, 0.2, 1);",
    ]


def generate_border_radius() -> list:
    """Generate border radius tokens."""
    return [
        "  /* --- Border Radius --- */",
        "  --radius-sm: 4px;",
        "  --radius-md: 8px;",
        "  --radius-lg: 12px;",
        "  --radius-xl: 16px;",
        "  --radius-full: 9999px;",
    ]


def build_css(config: dict) -> str:
    """Build the full CSS output from a config dict."""
    colors = config.get("colors", {})
    fonts = config.get("fonts", {})
    spacing_base = config.get("spacing_base", 4)
    font_size_base = config.get("font_size_base", 1.0)

    # Default font families if not provided
    if not fonts:
        fonts = {
            "sans": "'Inter', 'Helvetica Neue', Arial, sans-serif",
            "mono": "'Fira Code', 'Courier New', monospace",
        }

    lines = []
    lines.append("/* ==========================================================")
    lines.append("   Design System Tokens")
    lines.append("   Generated by generate_css_tokens.py")
    lines.append("   ========================================================== */")
    lines.append("")

    # ---- Light theme (default) ----
    lines.append("/* --- Light Theme (default) --- */")
    lines.append(":root {")

    # Color tokens
    lines.append("  /* --- Colors --- */")
    for name, value in colors.items():
        if isinstance(value, str):
            lines.append(f"  --color-{name}: {value};")
        elif isinstance(value, dict):
            for shade, hex_val in sorted(value.items(), key=lambda x: str(x[0])):
                lines.append(f"  --color-{name}-{shade}: {hex_val};")

    # Semantic surface colors for light theme
    bg_color = colors.get("neutral", {}).get("50", colors.get("background", "#FFFFFF"))
    fg_color = colors.get("neutral", {}).get("900", colors.get("foreground", "#0F172A"))
    if isinstance(bg_color, dict):
        bg_color = "#FFFFFF"
    if isinstance(fg_color, dict):
        fg_color = "#0F172A"

    lines.append("")
    lines.append("  /* --- Semantic Surface (Light) --- */")
    lines.append(f"  --color-background: {bg_color};")
    lines.append(f"  --color-foreground: {fg_color};")
    lines.append(f"  --color-surface: {lighten(bg_color, 0.02) if bg_color != '#FFFFFF' else '#FFFFFF'};")
    lines.append(f"  --color-surface-raised: #FFFFFF;")
    lines.append(f"  --color-border: {colors.get('neutral', {}).get('200', '#E2E8F0')};")
    lines.append(f"  --color-muted: {colors.get('neutral', {}).get('500', '#64748B')};")

    lines.append("")
    lines.extend(generate_typography_scale(font_size_base, fonts))
    lines.append("")
    lines.extend(generate_spacing_scale(spacing_base))
    lines.append("")
    lines.extend(generate_shadow_tokens())
    lines.append("")
    lines.extend(generate_motion_tokens())
    lines.append("")
    lines.extend(generate_border_radius())
    lines.append("}")
    lines.append("")

    # ---- Dark theme ----
    lines.append("/* --- Dark Theme --- */")
    lines.append('[data-theme="dark"] {')
    lines.append("  /* Invert neutral scale for dark mode */")

    neutral = colors.get("neutral", {})
    if isinstance(neutral, dict) and neutral:
        sorted_shades = sorted(neutral.items(), key=lambda x: int(x[0]) if str(x[0]).isdigit() else 0)
        reversed_shades = list(reversed([v for _, v in sorted_shades]))
        for i, (shade, _) in enumerate(sorted_shades):
            lines.append(f"  --color-neutral-{shade}: {reversed_shades[i]};")

    dark_bg = colors.get("neutral", {}).get("900", "#0F172A")
    dark_fg = colors.get("neutral", {}).get("50", "#F8FAFC")
    if isinstance(dark_bg, dict):
        dark_bg = "#0F172A"
    if isinstance(dark_fg, dict):
        dark_fg = "#F8FAFC"

    lines.append("")
    lines.append(f"  --color-background: {dark_bg};")
    lines.append(f"  --color-foreground: {dark_fg};")
    lines.append(f"  --color-surface: {lighten(dark_bg, 0.05)};")
    lines.append(f"  --color-surface-raised: {lighten(dark_bg, 0.1)};")
    lines.append(f"  --color-border: {colors.get('neutral', {}).get('700', '#334155') if isinstance(colors.get('neutral', {}), dict) else '#334155'};")
    lines.append(f"  --color-muted: {colors.get('neutral', {}).get('400', '#94A3B8') if isinstance(colors.get('neutral', {}), dict) else '#94A3B8'};")

    lines.append("")
    lines.append("  --shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.3);")
    lines.append("  --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.4), 0 2px 4px -2px rgba(0, 0, 0, 0.3);")
    lines.append("  --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.4), 0 4px 6px -4px rgba(0, 0, 0, 0.3);")
    lines.append("  --shadow-xl: 0 20px 25px -5px rgba(0, 0, 0, 0.4), 0 8px 10px -6px rgba(0, 0, 0, 0.3);")
    lines.append("}")
    lines.append("")

    # ---- System preference ----
    lines.append("/* --- System Preference --- */")
    lines.append("@media (prefers-color-scheme: dark) {")
    lines.append('  :root:not([data-theme="light"]) {')
    lines.append('    /* Same overrides as [data-theme="dark"] */')

    if isinstance(neutral, dict) and neutral:
        sorted_shades = sorted(neutral.items(), key=lambda x: int(x[0]) if str(x[0]).isdigit() else 0)
        reversed_shades = list(reversed([v for _, v in sorted_shades]))
        for i, (shade, _) in enumerate(sorted_shades):
            lines.append(f"    --color-neutral-{shade}: {reversed_shades[i]};")

    lines.append("")
    lines.append(f"    --color-background: {dark_bg};")
    lines.append(f"    --color-foreground: {dark_fg};")
    lines.append(f"    --color-surface: {lighten(dark_bg, 0.05)};")
    lines.append(f"    --color-surface-raised: {lighten(dark_bg, 0.1)};")
    lines.append(f"    --color-border: {colors.get('neutral', {}).get('700', '#334155') if isinstance(colors.get('neutral', {}), dict) else '#334155'};")
    lines.append(f"    --color-muted: {colors.get('neutral', {}).get('400', '#94A3B8') if isinstance(colors.get('neutral', {}), dict) else '#94A3B8'};")
    lines.append("  }")
    lines.append("}")
    lines.append("")

    # ---- Reduced motion ----
    lines.append("/* --- Reduced Motion --- */")
    lines.append("@media (prefers-reduced-motion: reduce) {")
    lines.append("  :root {")
    lines.append("    --duration-fast: 0ms;")
    lines.append("    --duration-normal: 0ms;")
    lines.append("    --duration-slow: 0ms;")
    lines.append("    --duration-slower: 0ms;")
    lines.append("  }")
    lines.append("}")
    lines.append("")

    return "\n".join(lines)


DEFAULT_CONFIG = {
    "colors": {
        "primary": {
            "50": "#EFF6FF",
            "100": "#DBEAFE",
            "200": "#BFDBFE",
            "300": "#93C5FD",
            "400": "#60A5FA",
            "500": "#3B82F6",
            "600": "#2563EB",
            "700": "#1D4ED8",
            "800": "#1E40AF",
            "900": "#1E3A8A",
        },
        "neutral": {
            "50": "#F8FAFC",
            "100": "#F1F5F9",
            "200": "#E2E8F0",
            "300": "#CBD5E1",
            "400": "#94A3B8",
            "500": "#64748B",
            "600": "#475569",
            "700": "#334155",
            "800": "#1E293B",
            "900": "#0F172A",
        },
        "success": "#16A34A",
        "warning": "#EAB308",
        "error": "#DC2626",
        "info": "#0EA5E9",
    },
    "fonts": {
        "sans": "'Inter', 'Helvetica Neue', Arial, sans-serif",
        "mono": "'Fira Code', 'Courier New', monospace",
    },
    "spacing_base": 4,
    "font_size_base": 1.0,
}


def main():
    parser = argparse.ArgumentParser(
        description="Generate complete CSS custom properties from a JSON design config file."
    )
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Path to a JSON config file with colors, fonts, spacing_base, font_size_base",
    )
    parser.add_argument(
        "--example-config",
        action="store_true",
        help="Print an example JSON config and exit",
    )

    args = parser.parse_args()

    if args.example_config:
        print(json.dumps(DEFAULT_CONFIG, indent=2))
        return

    if args.config:
        try:
            with open(args.config, "r") as f:
                config = json.load(f)
        except FileNotFoundError:
            print(f"Error: Config file not found: {args.config}", file=sys.stderr)
            sys.exit(1)
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON in config file: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        config = DEFAULT_CONFIG

    css = build_css(config)
    print(css)


if __name__ == "__main__":
    main()
