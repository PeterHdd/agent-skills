---
name: design-brand-guardian
description: "Develop and enforce brand identity systems, visual guidelines, and brand voice across all touchpoints. Use when you need brand strategy, positioning, brand audit, color and typography tokens, tone-of-voice guidelines, brand consistency enforcement, WCAG-compliant color pairings, or developer-ready design tokens for brand implementation."
metadata:
  version: "1.0.0"
---

# Brand Identity Guide

## Overview

This guide covers the end-to-end process of building and enforcing a brand identity system: from strategic positioning through visual tokens, voice guidelines, logo rules, and accessibility compliance. All outputs should be developer-ready with real values, not placeholders.

## Brand Foundation Process

### 1. Discovery

- Identify target audience, competitive landscape, and business objectives.
- Audit existing brand assets (if any) for consistency gaps.
- When creating a brand from scratch, start with positioning (audience, differentiator, personality) before any visual work.

### 2. Foundation

- Define positioning, values, and personality before any visual work.
- Write voice guidelines with a tone table and vocabulary lists.
- Voice guidelines must include do/don't examples for each tone variation.

### 3. Visual System

- Create color tokens with real hex values, not placeholders.
- Define typography stack with web-safe fallbacks. Typography stacks should include at least two fallback fonts.
- Specify logo usage rules with minimum sizes and clear-space ratios.
- Verify every text/background pairing against WCAG AA (4.5:1 for normal text, 3:1 for large text).
- Every brand element should reinforce the positioning strategy.

### 4. Enforcement

- Review new assets against the brand guide checklist: palette, typography, voice, logo rules.
- Flag deviations with the specific rule violated and a compliant alternative.
- When a stakeholder requests an off-brand element, explain the brand rationale and offer a compliant alternative.

### How to Handle Brand Evolution

- When a brand needs to evolve, change the minimum number of tokens required to achieve the new positioning. Avoid full redesigns unless the current system cannot express the new direction.
- When extending a brand to a new product line, reuse the core palette and voice but allow a unique accent color and sub-personality within the defined spectrum.

### How to Audit an Asset for Brand Compliance

Check the following in order:
1. Colors are within the defined palette.
2. Typography uses approved families.
3. Voice matches the context-appropriate tone.
4. Logo usage falls within clear-space rules.

When brand guidelines conflict with usability, propose a solution that satisfies both before compromising either.

## Scripts

The following scripts are available in the `scripts/` directory for automated brand work:

### `scripts/check_contrast.py`
WCAG 2.1 contrast ratio checker. Validates foreground/background color pairs against AA and AAA criteria for normal and large text.
```
python scripts/check_contrast.py --fg "#0F172A" --bg "#FFFFFF"
python scripts/check_contrast.py --file color_pairs.json --json
```

### `scripts/generate_tokens.py`
Generates a full design token color scale (50-900), neutral scale, and semantic colors (success, warning, error, info) from a single primary hex color. Outputs CSS custom properties or JSON.
```
python scripts/generate_tokens.py "#3B82F6"
python scripts/generate_tokens.py "#3B82F6" --format json
```

See [Meridian Analytics Example](references/meridian-analytics.md) for a complete, production-ready brand guide demonstrating the expected structure and level of detail for all brand work.
