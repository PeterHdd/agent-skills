# Report Example: Accordion Redesign

This is a complete, filled-in report -- not a template. Use this level of detail in every report.

```markdown
# QA Evidence Report: FAQ Accordion Redesign

## Environment
- URL tested: http://localhost:3000/faq
- Browser: Chromium 121 (Playwright)
- Viewport: 1280x720 (desktop), 375x667 (mobile)
- Tested at: 2025-03-15 14:30 UTC
- Dev server verified: `curl -s -o /dev/null -w "%{http_code}" http://localhost:3000` returned 200

## Specification Requirements Checked

| # | Spec Requirement | Result | Evidence |
|---|-----------------|--------|----------|
| 1 | "Accordion items expand on click to reveal answer text" | PASS | `qa-evidence/accordion-expanded.png` -- clicking item 0 reveals content panel |
| 2 | "Only one accordion item open at a time" | FAIL | `qa-evidence/accordion-multi-open.png` -- items 0 and 2 both open simultaneously |
| 3 | "Smooth 300ms expand/collapse animation" | PARTIAL | Animation present but measured at ~150ms via DevTools Performance tab. See `qa-evidence/accordion-timing.png` |
| 4 | "Chevron icon rotates 180deg when expanded" | PASS | `qa-evidence/accordion-expanded.png` -- chevron on item 0 points upward when open |
| 5 | "Accordion is keyboard accessible (Enter/Space to toggle)" | FAIL | Pressing Enter on focused trigger does nothing. See `qa-evidence/accordion-keyboard-fail.png` |

## Issues Found

### Issue 1: Multiple items open simultaneously
**Severity**: High
**Element**: `[data-testid="accordion-item-*"]`
**Expected**: Only one item open at a time (spec: "Only one accordion item open at a time")
**Actual**: Clicking a second item does not collapse the first
**Screenshot**: `qa-evidence/accordion-multi-open.png`
**Reproduce**:
```bash
npx playwright test tests/accordion.spec.ts --grep "only one item"
```

### Issue 2: Keyboard accessibility broken
**Severity**: High
**Element**: `[data-testid="accordion-item-0"] button`
**Expected**: Enter and Space keys toggle the accordion item
**Actual**: No response to keyboard events; only mouse click works
**Screenshot**: `qa-evidence/accordion-keyboard-fail.png`
**Reproduce**:
```bash
npx playwright test tests/accordion.spec.ts --grep "keyboard"
```

### Issue 3: Animation duration mismatch
**Severity**: Low
**Element**: `.accordion-content` transition property
**Expected**: 300ms transition duration (spec: "Smooth 300ms expand/collapse animation")
**Actual**: CSS shows `transition: height 150ms ease-in-out`
**Screenshot**: `qa-evidence/accordion-timing.png`
**Fix**: Change `150ms` to `300ms` in `src/components/Accordion.module.css` line 42

## Quality Assessment
**Spec Compliance**: 2/5 PASS, 1/5 PARTIAL, 2/5 FAIL
**Verdict**: NEEDS WORK -- keyboard accessibility and single-open behavior must be fixed before release
**Re-test Required**: Yes, after issues 1 and 2 are resolved
```
