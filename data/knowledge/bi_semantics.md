# BI Semantic References

This document extends the copilot grounding set with cross-platform BI metric definitions.

## Power BI
- Semantic model anchors:
- `marts_daily_kpis`
- `marts_channel_performance`
- Key measure: conversion rate = paid conversions / new users.
- Key measure: refund rate = refunded USD / gross revenue USD.

## Tableau
- Workbook sections:
- Daily KPI trend
- Channel revenue mix
- Experiment conversion comparison
- Calculated field `Alert Flag` maps to threshold logic:
- conversion rate below 0.03
- refund rate above 0.12
- net revenue below 3000

## Looker
- LookML explores:
- `daily_kpis`
- `channel_performance`
- Core measures:
- `net_revenue_usd`
- `conversion_rate`
- `paid_conversion_rate`

## Cross-Tool Interpretation Rule
If a user asks for KPI interpretation, the copilot should answer with one semantic definition and one table source from the marts layer.
