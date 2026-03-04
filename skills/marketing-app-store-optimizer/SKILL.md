---
name: marketing-app-store-optimizer
description: "Maximize app store discoverability, conversion rates, and organic downloads through data-driven optimization. Use when you need App Store Optimization (ASO), keyword research and ranking strategy, screenshot and icon A/B testing, app store metadata localization, conversion rate optimization, preview video strategy, or competitive analysis for Apple App Store and Google Play Store listings."
metadata:
  version: "1.0.0"
---

# App Store Optimization Guide

## Overview

This guide covers data-driven optimization of app store listings to maximize discoverability, conversion rates, and organic downloads across the Apple App Store and Google Play Store. It includes keyword research methodology, metadata optimization, visual asset strategy, localization, and performance tracking.

Base every optimization decision on measured data, not opinion. Log the metric that triggered each change. Never keyword-stuff: the title and subtitle must read as natural language to a human reviewer.

## Keyword Research Process

### When to Run Keyword Research

- When launching a new app or entering a new market.
- When organic installs decline for 2+ consecutive weeks.
- Re-run keyword gap analysis quarterly to capture seasonal and trend shifts.

### How to Prioritize Keywords

1. Filter by relevance score (7+/10 minimum).
2. Rank by search volume within the relevant set.
3. Factor in competition level -- prefer lower competition at similar volume.
4. Update keyword sets every 4-6 weeks based on ranking data; do not change keywords that already rank in the top 5.

### Competitive Monitoring

Track competitor keyword changes weekly. Adjust strategy only when a competitor move threatens your top-10 positions.

## Visual Asset Strategy Overview

### App Icon
- A/B test icon variants with a minimum of 5,000 impressions over 10 days.
- Success threshold: variant must beat current by >= 0.5pp CTR.

### Screenshots
- Lead with a hero frame showing the core value proposition.
- Update when adding a major feature, entering a new locale, or when install-to-view rate drops below 30%.

### Preview Video
- Produce only if the app has a visual "wow" moment that screenshots cannot convey.
- Keep to 15 seconds: problem hook (0-3s), feature montage (3-12s), CTA (12-15s).
- Technical: 1080x1920 (9:16), .mp4, < 30MB, captions only for accessibility.

## Localization

Localize metadata (title, subtitle, description) for any market contributing 5%+ of impressions but converting below global average. Localize screenshots only after metadata localization shows a measurable lift in that market (minimum 2-week observation).

## Performance Tracking

Run A/B tests for a minimum of 7 days and 1,000 impressions per variant before drawing conclusions. Report conversion rate lift with confidence intervals (minimum 90% confidence).

| Metric | Check Frequency | Action Threshold |
|---|---|---|
| Keyword rankings (top 20 terms) | Weekly | Investigate any term dropping 5+ positions |
| Install-to-impression rate | Weekly | Redesign screenshots if < 30% for 2 weeks |
| App icon CTR (via A/B test) | Per test cycle | Replace if variant wins by >= 0.5pp |
| Rating average | Daily | Trigger review-response workflow if < 4.3 |
| Competitor keyword changes | Weekly | Adjust only if top-10 position threatened |

### Implementation Workflow

1. **Market research and analysis** -- Audit current keyword rankings and identify gaps using App Annie, Sensor Tower, or Mobile Action. Benchmark conversion funnel (impressions -> product page views -> installs) against category medians. Map competitor keyword and visual asset strategies for the top 5 apps in category.
2. **Strategy development** -- Select 15-25 target keywords ranked by (relevance * volume / competition). Draft metadata variants for A/B testing; prepare at least 2 title/subtitle combinations. Design screenshot storyboard; prioritize the hero frame and first two supporting frames.
3. **Implementation and testing** -- Deploy metadata changes; schedule A/B test with minimum 7-day / 1,000-impression run. Submit localized listings for priority markets. Set up weekly keyword-rank tracking and alerting.
4. **Optimization and scaling** -- After each test cycle, document winning variant, measured lift, and confidence level. Roll winning optimizations to additional markets. Re-run keyword gap analysis quarterly to capture seasonal and trend shifts.

## Scripts

The following scripts are available in the `scripts/` directory for ASO work:

### `scripts/validate_metadata.py`
Validates app store metadata against platform character limits (iOS and Android). Checks for keyword stuffing, calculates readability score, and flags title/subtitle keyword overlap.
```
python scripts/validate_metadata.py --title "FitPulse" --subtitle "Your Fitness Companion" --platform ios
python scripts/validate_metadata.py --title "FitPulse - Workout Tracker" --short-desc "Track workouts and nutrition" --platform android --json
```

### `scripts/keyword_density.py`
Analyzes keyword density in text content. Reports top 20 keywords by frequency and flags words exceeding a configurable stuffing threshold (default 3%).
```
python scripts/keyword_density.py --file competitor_description.txt
python scripts/keyword_density.py --text "Your app description here..." --threshold 3.0 --json
```

See [FitPulse Example](references/fitpulse-example.md) for a complete worked example demonstrating the full ASO workflow with keyword tables, metadata optimization, screenshot sequences, and performance tracking.
