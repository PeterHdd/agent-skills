# Report Example: Q1 2026 E-Commerce Retention Analysis

## Worked Report

```
# Q1 2026 Customer Retention - Business Intelligence Report

## Executive Summary
- **Primary Insight**: 90-day retention dropped from 41% to 33% QoQ,
  concentrated in the $50-$150 AOV cohort (n = 12,400 customers).
- **Confidence**: 95% CI [31.8%, 34.2%]; p < 0.001 vs. prior quarter.
- **Business Impact**: Projected $2.1M annualized revenue loss if
  trend continues at current rate.
- **Actions Required**: (1) Launch win-back campaign for lapsed
  $50-$150 AOV segment, (2) investigate checkout-flow drop-off
  introduced in Jan release.

## Analysis
- **Data Sources**: Snowflake `analytics.orders` (99.7% completeness,
  audited Mar 1), Google Analytics 4 event stream, Stripe
  subscription data.
- **Methodology**: Kaplan-Meier survival curves with log-rank test
  across AOV cohorts; Cox proportional hazards model controlling for
  acquisition channel, device type, and first-order discount usage.
- **Findings**:
  - Mid-AOV cohort hazard ratio 1.38 (95% CI [1.21, 1.57]) vs.
    baseline, indicating significantly higher churn risk.
  - Checkout completion rate fell 6pp (72% -> 66%) after Jan 14
    deploy; correlates with retention dip onset (r = 0.84).
  - Customers acquired via paid social show 2.1x higher 90-day
    churn than organic search (p < 0.01).

## Recommendations
- **Phase 1 (30 days)**: Deploy targeted email win-back sequence to
  8,200 lapsed mid-AOV customers. Success metric: 12% reactivation
  rate (baseline: 7%).
- **Phase 2 (90 days)**: A/B test simplified checkout flow against
  current version; target 4pp lift in completion rate. Run with
  10% traffic for 3 weeks to reach n = 5,000 per arm.
- **Phase 3 (6 months)**: Shift 15% of paid social budget to organic
  content and SEO. Measure 90-day retention by channel monthly;
  target parity within 0.5x by Q3.
```

## Customer RFM Segmentation (Python)
```python
import pandas as pd
import numpy as np

def rfm_segmentation(df: pd.DataFrame) -> pd.DataFrame:
    """RFM analysis with actionable customer segments."""
    current = df["date"].max()
    rfm = df.groupby("customer_id").agg(
        recency=("date", lambda x: (current - x.max()).days),
        frequency=("order_id", "count"),
        monetary=("revenue", "sum"),
    )
    for col, asc in [("recency", True), ("frequency", False), ("monetary", False)]:
        rfm[f"{col[0]}_score"] = pd.qcut(
            rfm[col].rank(method="first", ascending=asc), 5, labels=[1, 2, 3, 4, 5]
        )
    rfm["rfm"] = rfm["r_score"].astype(str) + rfm["f_score"].astype(str) + rfm["m_score"].astype(str)

    rules = [
        (rfm["r_score"].astype(int) >= 4) & (rfm["f_score"].astype(int) >= 4), "Champions",
        (rfm["r_score"].astype(int) >= 3) & (rfm["f_score"].astype(int) >= 3), "Loyal Customers",
        (rfm["r_score"].astype(int) >= 4) & (rfm["f_score"].astype(int) <= 2), "New Customers",
        (rfm["r_score"].astype(int) <= 2) & (rfm["f_score"].astype(int) >= 3), "At Risk",
    ]
    rfm["segment"] = "Others"
    # Apply rules sequentially; last matching rule wins (later rules override earlier ones)
    for i in range(0, len(rules), 2):
        rfm.loc[rules[i], "segment"] = rules[i + 1]
    return rfm
```
