---
name: design-ui-designer
description: "Create visual design systems, component libraries, and accessible responsive interfaces with developer-ready specifications. Use when you need design tokens for color, typography, spacing, or motion, light/dark/system theme toggles, CSS Grid or Flexbox layout architecture, responsive breakpoint strategies, semantic CSS custom properties, component state documentation, mobile-first responsive layouts, WCAG AA compliance, touch target sizing, or detailed handoff specs."
metadata:
  version: "1.0.0"
---

# UI Design System Guide

## Overview

This guide covers the creation of visual design systems, component libraries, and responsive layouts with developer-ready specifications. The approach follows a strict order: design tokens first, components second, screens last.

## Core Requirements

- Every interactive element needs five states: default, hover, active, focus-visible, disabled.
- All color pairings must meet WCAG AA contrast (4.5:1 for normal text, 3:1 for large text).
- Touch targets must be at least 44x44px.
- Motion must respect `prefers-reduced-motion` by defaulting to no animation and enhancing for users who allow it.
- When a brand color fails contrast checks, create a darker/lighter variant for text use and document both.

## Token Strategy

Define the full token set before designing any component. Tokens are the single source of truth. Token categories: primary colors, secondary/neutral colors, semantic colors (success, warning, error, info), typography (family, size scale), spacing (4px base grid), shadows, and motion durations.

## Component Checklist

- Build base components (button, input, card, nav, alert) using only tokens.
- Document all five states for each interactive component.
- When a component needs more than three variants, consider splitting into separate components.
- Motion: keep durations under 300ms for micro-interactions and under 500ms for transitions. Use ease-out for entrances, ease-in for exits.

## Responsive Approach

Base styles target mobile (320px+) and progressively add layout complexity at wider breakpoints. Test at 320px, 640px, 768px, 1024px, and 1280px.

## Dark Mode

Invert the semantic meaning of the neutral scale (light-theme neutral-100 becomes dark-theme background) rather than creating separate token names.

## Code Examples

See [Design Tokens Guide](references/tokens.md) for the full CSS custom properties set (light + dark themes), system preference media query, and a complete theme toggle implementation (CSS + HTML + JavaScript with localStorage persistence).

See [Component Patterns Guide](references/components.md) for button, form input, and card CSS with all states, plus the responsive container strategy.

## Workflow

1. **Token definition** -- Define the full color, typography, spacing, shadow, and motion token set. Verify all text/background pairings meet WCAG AA contrast. Create both light and dark theme token overrides.
2. **Component design** -- Build base components using only tokens. Document all five states for each interactive component. Ensure minimum 44px touch targets on all interactive elements.
3. **Layout system** -- Define responsive breakpoints and container widths. Create grid utilities for common layout patterns. Test layouts at each defined breakpoint.
4. **Developer handoff** -- Export token values as CSS custom properties. Provide component specs with exact padding, margin, and border-radius values. Include interaction state documentation: what changes on hover, focus, active, and disabled.

## Scripts

The following scripts are available in the `scripts/` directory for design system work:

### `scripts/check_contrast.py`
WCAG 2.1 contrast ratio checker. Validates foreground/background color pairs against AA and AAA criteria for normal and large text.
```
python scripts/check_contrast.py --fg "#0F172A" --bg "#FFFFFF"
python scripts/check_contrast.py --file color_pairs.json --json
```

### `scripts/generate_css_tokens.py`
Generates a complete `:root` CSS custom properties block from a JSON config file. Includes light theme, dark theme override, system preference media query, typography scale, spacing scale, shadows, motion tokens, and reduced-motion override.
```
python scripts/generate_css_tokens.py --config design-config.json
python scripts/generate_css_tokens.py --example-config > config-template.json
python scripts/generate_css_tokens.py
```
