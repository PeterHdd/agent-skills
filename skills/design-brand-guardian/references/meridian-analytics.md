# Example: Meridian Analytics Brand Guide

A complete, production-ready brand guide for a fictional B2B analytics company. Use this structure and level of detail as the standard for all brand work.

## Brand Foundation
- **Purpose**: Help mid-market companies make confident decisions from their own data.
- **Vision**: Every growth-stage company operates with enterprise-grade insight.
- **Mission**: Deliver clear, actionable analytics through software that respects the user's time.
- **Values**: Clarity over complexity, Honesty in data, Speed to insight, Respect for privacy.
- **Personality**: Confident but not arrogant. Precise but not cold. Helpful but not hand-holding.
- **Positioning statement**: For data-informed teams who have outgrown spreadsheets, Meridian Analytics provides self-service dashboards that surface the metrics that matter, without requiring a dedicated analyst.

## Voice Guidelines

| Context | Tone | Example |
|---|---|---|
| Marketing copy | Confident, energetic | "See what your data has been trying to tell you." |
| Error messages | Calm, direct, helpful | "That query timed out. Try narrowing the date range or filtering by a single region." |
| Documentation | Precise, patient | "The retention chart shows the percentage of users who returned within each cohort's first 30 days." |
| Success states | Warm, brief | "Dashboard saved. Your team can see it now." |

**Words we use**: insight, clarity, confidence, action, growth.
**Words we avoid**: synergy, leverage (as verb), disrupt, magic, automagically.

## Visual Identity System
```css
:root {
  /* Primary palette */
  --brand-primary: #1B65A6;
  --brand-primary-light: #4A90D9;
  --brand-primary-dark: #0E3F6B;

  /* Secondary palette */
  --brand-secondary: #2EC4B6;
  --brand-secondary-light: #6FDED3;
  --brand-secondary-dark: #1A8A7F;

  /* Accent */
  --brand-accent: #F4A261;

  /* Neutrals */
  --brand-neutral-50: #F8FAFC;
  --brand-neutral-100: #F1F5F9;
  --brand-neutral-300: #CBD5E1;
  --brand-neutral-500: #64748B;
  --brand-neutral-700: #334155;
  --brand-neutral-900: #0F172A;

  /* Semantic */
  --brand-success: #16A34A;
  --brand-warning: #EAB308;
  --brand-error: #DC2626;

  /* Typography */
  --brand-font-heading: 'Plus Jakarta Sans', 'Inter', system-ui, sans-serif;
  --brand-font-body: 'Inter', system-ui, sans-serif;
  --brand-font-mono: 'JetBrains Mono', 'Fira Code', monospace;

  /* Spacing (4px base grid) */
  --brand-space-xs: 0.25rem;
  --brand-space-sm: 0.5rem;
  --brand-space-md: 1rem;
  --brand-space-lg: 2rem;
  --brand-space-xl: 4rem;
}
```

## Logo Usage Rules
- Minimum clear space: equal to the height of the "M" in the wordmark on all sides.
- Minimum size: 120px wide for horizontal lockup, 32px for icon-only.
- Never place the logo on a background with less than 4.5:1 contrast against the logo color.
- Approved logo colors: `--brand-primary` on light backgrounds, white on dark backgrounds, `--brand-neutral-900` for single-color print.

## Accessibility Requirements
| Pairing | Contrast Ratio | Pass Level |
|---|---|---|
| `--brand-neutral-900` on `--brand-neutral-50` | 16.4:1 | AAA |
| `--brand-primary` on white | 5.2:1 | AA |
| `--brand-secondary-dark` on white | 4.6:1 | AA |
| `--brand-accent` on `--brand-neutral-900` | 5.8:1 | AA |
