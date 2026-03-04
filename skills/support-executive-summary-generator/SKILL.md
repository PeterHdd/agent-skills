---
name: support-executive-summary-generator
description: "Transform complex business inputs into concise, actionable executive summaries for C-suite decision-makers. Use when you need McKinsey SCQA analysis, BCG Pyramid Principle structuring, Bain action-oriented recommendations, board-ready briefings, strategic insight distillation, quantified impact assessments, or decision-focused summaries that executives can act on in under three minutes."
metadata:
  version: "1.0.0"
---

# Executive Summary Guide

Transform complex business inputs into concise, actionable executive summaries for C-suite decision-makers who need to grasp essence, evaluate impact, and decide next steps in under three minutes.

## SCQA Framework

Apply these consulting frameworks to structure the summary:

- **McKinsey's SCQA** (Situation - Complication - Question - Answer): Establish context, identify the tension, frame the decision, and present the recommendation.
- **BCG's Pyramid Principle**: Lead with the conclusion, then organize supporting insights hierarchically by business impact.
- **Bain's Action-Oriented Recommendations**: Every recommendation includes an owner, timeline, and expected result.

### Key guidelines

- Prioritize insight over information.
- Quantify wherever possible.
- Link every finding to impact and every recommendation to action.
- Do not make assumptions beyond provided data.
- Flag data gaps and uncertainties explicitly.

## Formatting Rules

**Total Length:** 325-475 words (500 max)

```markdown
## 1. SITUATION OVERVIEW [50-75 words]
- What is happening and why it matters now
- Current vs. desired state gap

## 2. KEY FINDINGS [125-175 words]
- 3-5 most critical insights (each with >= 1 quantified or comparative data point)
- **Bold the strategic implication in each**
- Order by business impact

## 3. BUSINESS IMPACT [50-75 words]
- Quantify potential gain/loss (revenue, cost, market share)
- Note risk or opportunity magnitude (% or probability)
- Define time horizon for realization

## 4. RECOMMENDATIONS [75-100 words]
- 3-4 prioritized actions labeled (Critical / High / Medium)
- Each with: owner + timeline + expected result
- Include resource or cross-functional needs if material

## 5. NEXT STEPS [25-50 words]
- 2-3 immediate actions (<=30-day horizon)
- Identify decision point + deadline
```

### Section-level guidelines

- Every key finding must include at least 1 quantified or comparative data point.
- Bold strategic implications in findings.
- Order content by business impact.
- Recommendations must include specific timelines, owners, and expected results.
- Tone: decisive, factual, and outcome-driven.
- Focus on actionability over description.

## Workflow

### Step 1: Intake and Analysis
- Review provided business content thoroughly.
- Identify critical insights and quantifiable data points.
- Map content to SCQA framework components.
- Assess data quality and identify gaps.

### Step 2: Structure Development
- Apply Pyramid Principle to organize insights hierarchically.
- Prioritize findings by business impact magnitude.
- Quantify every claim with data from source material.
- Identify strategic implications for each finding.

### Step 3: Draft the Summary
- Draft concise situation overview establishing context and urgency.
- Present 3-5 key findings with bold strategic implications.
- Quantify business impact with specific metrics and timeframes.
- Structure 3-4 prioritized, actionable recommendations with clear ownership.

### Step 4: Verify
- Check adherence to 325-475 word target (500 max).
- Confirm all findings include quantified data points.
- Validate recommendations have owner + timeline + expected result.
- Ensure tone is decisive, factual, and outcome-driven.
- Confirm zero assumptions beyond provided data.

## Reference

### SCQA Quick-Check

| Component | Ask yourself |
|-----------|-------------|
| Situation | Have I established the current state in 1-2 sentences? |
| Complication | Is the tension or problem clearly stated with data? |
| Question | Is the implicit decision framed for the reader? |
| Answer | Does the recommendation lead with the conclusion? |

### Priority Labels

| Label | Meaning | Timeline expectation |
|-------|---------|---------------------|
| Critical | Immediate action required, revenue or operational risk | Within 2 weeks |
| High | Important for strategic goals, significant impact | Within 30 days |
| Medium | Valuable improvement, manageable without urgency | Within quarter |

## Scripts

### `scripts/analyze_input.py`
Analyze a text or markdown file for executive summary generation. Extracts word count, reading time, key metrics (numbers with context), named entities (capitalized multi-word phrases, acronyms), and section headings. Identifies the top 5 most important sentences by keyword density and position scoring. Outputs a structured analysis the agent can use to write the executive summary.

```bash
scripts/analyze_input.py report.md
scripts/analyze_input.py --format json quarterly-review.txt
```

See [Worked Example](references/worked-example.md) for a full before/after demonstration showing raw input transformed into a completed executive summary.
