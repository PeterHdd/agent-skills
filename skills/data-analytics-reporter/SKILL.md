---
name: data-analytics-reporter
description: "Transform raw data into actionable business insights through statistical analysis, dashboard creation, and KPI tracking. Use when you need data analysis, reporting, SQL query optimization, A/B testing, forecasting, customer analytics, churn prediction, marketing attribution, financial modeling, or business intelligence dashboards in tools like Tableau, Power BI, or Looker."
metadata:
  version: "1.0.0"
---

# Data Analytics & Reporting Guide

## Overview

This guide covers the process of transforming raw data into actionable business insights: from data quality validation through statistical analysis, dashboard creation, and strategic reporting. It includes SQL patterns, Python analysis code, and a worked report example.

### Critical Rules

- Validate data accuracy and completeness before any analysis.
- Document data sources, transformations, and assumptions.
- Include statistical significance testing and confidence levels for all conclusions. Claims without significance testing should be labeled as directional observations, not conclusions.
- Connect every analysis to business outcomes and actionable recommendations.
- Design dashboards for specific stakeholder needs and decision contexts.
- Name every data source with its query date range, row count, and completeness percentage.
- Dashboards should include a "last refreshed" timestamp, data freshness SLA, and a link to the underlying query for each metric.

### Workflow

1. **Data Discovery** -- Assess data quality, identify key metrics and stakeholder requirements, establish significance thresholds.
2. **Analysis** -- Build reproducible pipelines, apply appropriate statistical methods, calculate confidence intervals.
3. **Visualization & Reporting** -- Create interactive dashboards with drill-down, write executive summaries with findings and recommendations.
4. **Impact Measurement** -- Track recommendation implementation, measure business outcome correlation, iterate.

See [SQL Patterns](references/sql-patterns.md) for executive dashboard and marketing attribution queries.

See [Report Example](references/report-example.md) for a full Q1 2026 worked report and Python RFM segmentation code.

## Report Structure

### Report Quality Checklist

- All statistical claims include confidence intervals at a minimum 95% confidence level.
- Every data source is named with its query date range, row count, and completeness percentage (e.g., "Snowflake analytics.orders, Jan 1 - Mar 31 2026, 142,300 rows, 99.7% complete").
- Recommendations include projected ROI with explicit assumptions stated (e.g., "Assumes 12% reactivation rate based on historical win-back campaign performance of 7-15%").
- Reports are reproducible: all SQL queries and Python scripts are included and can be re-run against the documented data sources to regenerate all figures and tables.

## Reference

### Capabilities Reference

- Statistical analysis: regression, forecasting, A/B testing, segmentation, correlation
- Dashboard and report creation (Tableau, Power BI, Looker, custom)
- SQL query optimization and data warehouse management
- Python/R for analysis, modeling, and automation
- Customer analytics: lifetime value, churn prediction, RFM segmentation
- Marketing attribution and campaign ROI measurement
- Financial modeling and business performance analysis
- Data quality assurance and GDPR/CCPA compliance in analytics

## Scripts

The following scripts are available in the `scripts/` directory for data analysis:

### `scripts/analyze_csv.py`
Auto-profiles a CSV dataset: row/column counts, column types (numeric/text/date), null percentages, basic statistics for numeric columns (min, max, mean, median, stddev), and top 5 unique values for text columns. Outputs markdown or JSON.
```
python scripts/analyze_csv.py data.csv
python scripts/analyze_csv.py data.csv --json
```

### `scripts/check_data_quality.py`
Checks a CSV file for data quality issues: duplicate rows, columns with >50% nulls, mixed data types, and outliers (>3 stddev from mean). Reports a quality score (0-100) and specific issues found.
```
python scripts/check_data_quality.py data.csv
python scripts/check_data_quality.py data.csv --stddev 2.5 --json
```
