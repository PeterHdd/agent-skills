---
name: testing-evidence-collector
description: "Validate implementations against specifications using visual evidence, reproducible test commands, and concrete proof. Use when you need QA verification with screenshots, Playwright-based evidence capture, before-and-after comparison testing, spec compliance auditing, bug reproduction steps, or structured test reports where every finding is backed by visual proof or a copy-pasteable command."
metadata:
  version: "1.0.0"
---

# QA Evidence Collection Guide

Validate implementations against specifications using visual evidence, reproducible test commands, and concrete findings. Every claim in a report must be backed by a screenshot, a test result, or a copy-pasteable command that reproduces the finding.

## Evidence Collection Process

### Step 1: Capture Baseline Evidence
```bash
# Verify the dev server is running and accessible
curl -s -o /dev/null -w "%{http_code}" http://localhost:3000

# Capture full-page screenshots at standard viewports
npx playwright screenshot --viewport-size=1280,720 http://localhost:3000 qa-evidence/desktop-full.png
npx playwright screenshot --viewport-size=375,667 http://localhost:3000 qa-evidence/mobile-full.png
npx playwright screenshot --viewport-size=768,1024 http://localhost:3000 qa-evidence/tablet-full.png

# List actual project files to verify implementation exists
ls -la src/components/ || ls -la app/components/ || ls -la *.html
```

### Step 2: Compare Against Specification
- For each stated requirement, locate the corresponding visual element in the screenshot.
- Quote the exact spec text next to what you observe. Example: Spec says "three-column layout" -- screenshot shows two columns.

### Step 3: Test Interactive Elements
- Run the Playwright capture script for each interactive element to get before/after screenshots.
- Log the exact selector used. Record whether the element responded as specified.

### Step 4: Write the Evidence Report
- Fill in every field with actual observed data. Attach screenshot paths for every finding.
- Mark each spec requirement as PASS, FAIL, or PARTIAL with a one-line explanation.

See [Playwright Capture](references/playwright-capture.md) for the full screenshot utility and test spec code.

## Report Structure

### Report guidelines
- Every reported issue must include a screenshot file path and the exact CSS selector or `data-testid` used to locate the element.
- Before/after screenshots use the same viewport size (1280x720 for desktop, 375x667 for mobile).
- Test commands in the report must be copy-pasteable: running them produces the same result without modification.
- Each spec requirement is individually listed with a PASS / FAIL / PARTIAL verdict and a one-line explanation.
- No issue is reported without a reproduction step (either a Playwright test command or a manual step sequence).
- The evidence report must state the exact URL, browser, viewport, and timestamp of the test session.
- Findings reference the specification by quoting exact text, not paraphrasing.
- Report only what is observed. Do not speculate about features working "behind the scenes."
- Compare against the specification, not against an idealized version. Do not add requirements the spec never stated.

See [Report Example](references/report-example.md) for a complete accordion redesign evidence report.

## Reference

### Verdict Definitions

| Verdict | Meaning |
|---------|---------|
| PASS | Implementation matches the spec requirement exactly |
| PARTIAL | Implementation is present but deviates from spec (e.g., wrong timing, incomplete behavior) |
| FAIL | Implementation is missing or contradicts the spec requirement |

### Issue Severity Levels

| Severity | Meaning |
|----------|---------|
| High | Blocks release; spec requirement not met, accessibility broken, or data loss risk |
| Medium | Deviates from spec but workaround exists; should fix before release |
| Low | Cosmetic or minor deviation; can ship with known issue documented |

### Standard Viewports

| Device | Width x Height |
|--------|---------------|
| Desktop | 1280 x 720 |
| Tablet | 768 x 1024 |
| Mobile | 375 x 667 |

## Scripts

### `scripts/capture_screenshot.py`
Capture a full-page screenshot of a URL using Playwright. Auto-detects available Playwright installations (Node.js, Python, or npx). Configurable viewport size and wait time before capture. Falls back to a helpful error message if Playwright is not installed.

```bash
scripts/capture_screenshot.py http://localhost:3000 screenshot.png
scripts/capture_screenshot.py --full-page --width 1920 --height 1080 http://example.com page.png
scripts/capture_screenshot.py --wait 2000 http://localhost:3000/dashboard dashboard.png
```

### `scripts/generate_report.py`
Generate a markdown evidence report template from a directory of screenshots. Includes environment info (date, browser, viewports), screenshot inventory (file name, size, dimensions), embedded screenshot references, and placeholder finding templates for the agent to fill in.

```bash
scripts/generate_report.py ./qa-evidence
scripts/generate_report.py --project "Login Page Redesign" --url http://localhost:3000 ./screenshots -o report.md
```
