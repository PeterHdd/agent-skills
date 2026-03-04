# SQL Patterns

## Executive Dashboard Query
```sql
WITH monthly_metrics AS (
  SELECT
    DATE_TRUNC('month', date) AS month,
    SUM(revenue) AS monthly_revenue,
    COUNT(DISTINCT customer_id) AS active_customers,
    AVG(order_value) AS avg_order_value
  FROM transactions
  WHERE date >= CURRENT_DATE - INTERVAL '12 months'
  GROUP BY 1
),
growth AS (
  SELECT *,
    LAG(monthly_revenue) OVER (ORDER BY month) AS prev_revenue,
    ROUND((monthly_revenue - LAG(monthly_revenue) OVER (ORDER BY month))
      / NULLIF(LAG(monthly_revenue) OVER (ORDER BY month), 0) * 100, 1) AS growth_pct
  FROM monthly_metrics
)
SELECT month, monthly_revenue, active_customers, avg_order_value, growth_pct,
  CASE
    WHEN growth_pct > 10 THEN 'High Growth'
    WHEN growth_pct > 0  THEN 'Positive'
    ELSE 'Needs Attention'
  END AS status
FROM growth ORDER BY month DESC;
```

## Marketing Attribution Query
```sql
WITH touches AS (
  SELECT mt.customer_id, mt.channel, mt.campaign, mt.touchpoint_date,
    c.revenue,
    ROW_NUMBER() OVER (PARTITION BY mt.customer_id ORDER BY mt.touchpoint_date) AS seq,
    COUNT(*) OVER (PARTITION BY mt.customer_id) AS total
  FROM marketing_touchpoints mt
  JOIN conversions c ON mt.customer_id = c.customer_id
  WHERE mt.touchpoint_date <= c.conversion_date
),
weighted AS (
  SELECT *, CASE
    WHEN total = 1 THEN 1.0
    WHEN seq = 1 THEN 0.4
    WHEN seq = total THEN 0.4
    ELSE 0.2 / NULLIF(total - 2, 0)
  END AS weight
  FROM touches
)
SELECT channel, campaign,
  ROUND(SUM(revenue * weight), 2) AS attributed_revenue,
  COUNT(DISTINCT customer_id) AS conversions
FROM weighted GROUP BY 1, 2 ORDER BY attributed_revenue DESC;
```
