# BI Semantic References

This document extends the copilot grounding set with cross-platform BI metric definitions, KPI interpretation rules, and alerting thresholds. The copilot uses this to answer questions about metrics across Power BI, Tableau, Looker, and other BI tools, and to route questions to the correct semantic layer.

---

## Core KPI Definitions

### conversion_rate
- **Formula:** `paid_conversions / new_users` for a given metric date
- **Context:** Used to measure the efficiency of turning new visitors into paying customers. Primary KPI tracked in `marts_daily_kpis`.
- **Alert threshold:** Below 0.03 (3%) triggers an Alert Flag in Tableau.

### refund_rate
- **Formula:** `refunded_usd / gross_revenue_usd`
- **Context:** Measures payment quality and transaction health. Spikes indicate chargeback risk or product dissatisfaction.
- **Alert threshold:** Above 0.12 (12%) triggers an Alert Flag in Tableau.

### net_revenue_usd
- **Formula:** `gross_revenue_usd - refunded_usd`
- **Context:** True revenue after chargebacks and refunds. Reported as the bottom-line revenue figure in all dashboards.
- **Alert threshold:** Below $3,000 per reporting period triggers an Alert Flag in Tableau.

### paid_conversion_rate
- **Formula:** `paid_conversions / new_users` (subset of conversion_rate, counts only paid conversions)
- **Context:** Looker-specific measure. More selective than conversion_rate since it excludes free-trial conversions.
- **LookML explore:** `channel_performance`

### customer_health_score
- **Formula:** Blended metric combining sessions, revenue, support tickets, and churn risk signals.
- **Context:** Composite score used to identify at-risk or high-value customers. Tracked in `marts_customer_health`.
- **Interpretation:** Higher is better. Below threshold triggers proactive outreach runbooks.

---

## Power BI

### Semantic Model Anchors
- `marts_daily_kpis` — Primary daily KPI rollup including conversion rate, refund rate, and net revenue.
- `marts_channel_performance` — Channel-level breakdown of acquisition metrics.
- `marts_experiment_performance` — A/B test results by channel and variant.

### Measures Reference
| Measure | Table | Formula |
|---|---|---|
| `conversion_rate` | marts_daily_kpis | paid_conversions / new_users |
| `refund_rate` | marts_daily_kpis | refunded_usd / gross_revenue_usd |
| `net_revenue_usd` | marts_daily_kpis | gross_revenue_usd - refunded_usd |
| `paid_conversion_rate` | marts_channel_performance | paid_conversions / new_users |

### KPI Interpretation Guidelines (Power BI)
When a user asks about a KPI trend in Power BI, the copilot should:
1. Identify the metric name and its source table
2. Explain the formula in plain language
3. Note the applicable Alert Flag threshold if relevant
4. Reference the marts layer as the canonical source

---

## Tableau

### Workbook Sections
- **Daily KPI Trend** — Time-series view of all core KPIs (conversion rate, refund rate, net revenue) per day.
- **Channel Revenue Mix** — Breakdown of net revenue by acquisition channel (paid, organic, referral, etc.).
- **Experiment Conversion Comparison** — Side-by-side conversion rates for active A/B test variants.

### Alert Flag Threshold Logic
The `Alert Flag` calculated field applies to all three core KPIs:

```
IF conversion_rate < 0.03 THEN flag = TRUE
IF refund_rate > 0.12 THEN flag = TRUE
IF net_revenue_usd < 3000 THEN flag = TRUE
```

When a row triggers the Alert Flag, the runbook directive is:
- `conversion_rate` low → inspect experiment split and channel mix
- `refund_rate` high → inspect payment quality and failed transactions
- `net_revenue_usd` low → review traffic quality and funnel drop-off

### Tableau Metric Mapping
| Tableau Field | Copilot Alias | Source Table |
|---|---|---|
| `Conversion Rate` | conversion_rate | marts_daily_kpis |
| `Refund Rate` | refund_rate | marts_daily_kpis |
| `Net Revenue` | net_revenue_usd | marts_daily_kpis |
| `Channel` | channel_name | marts_channel_performance |
| `Variant` | experiment_variant | marts_experiment_performance |

---

## Looker

### LookML Explores
- `daily_kpis` — Daily aggregated KPIs with date drill-down.
- `channel_performance` — Channel-level acquisition and conversion metrics.
- `customer_health` — Customer-level health scores and risk signals.

### Core Measures Reference
| LookML Measure | Definition |
|---|---|
| `net_revenue_usd` | Gross revenue minus refunds |
| `conversion_rate` | Conversions divided by sessions or users |
| `paid_conversion_rate` | Paid-channel conversions divided by new paid users |
| `customer_health_score` | Blended risk/satisfaction score |

### Looker -> SQL Mapping
When Looker questions are translated to SQL suggestions:
- Use `marts_daily_kpis` for daily rollups
- Use `marts_channel_performance` for channel breakdowns
- Apply the same threshold rules from the Alert Flag logic

---

## Cross-Platform Interpretation Rules

### Rule 1: One Semantic Definition + One Table Source
If a user asks for KPI interpretation, the copilot must provide:
1. The metric definition in plain language
2. The formula
3. The specific marts table that serves as the canonical source

Example answer format:
> "conversion_rate is the ratio of paid conversions to new users. Formula: paid_conversions / new_users. Canonical source: marts_daily_kpis."

### Rule 2: Threshold Alert Routing
When a user asks about an alert or threshold:
1. Identify which KPI is involved
2. Retrieve the applicable threshold from the Alert Flag logic
3. Reference the correct Tableau or Looker field name
4. Pull the runbook directive from the operational runbook

### Rule 3: Channel vs. Experiment Attribution
When a user asks "which channel or experiment is driving changes":
- Route to `marts_channel_performance` for channel attribution
- Route to `marts_experiment_performance` for experiment attribution
- Cross-reference both when the question involves both

### Rule 4: Health Score Interpretation
Customer health score questions should:
- Use `marts_customer_health` as the source table
- Reference the blended component signals (sessions, revenue, tickets, churn)
- Flag scores below the documented threshold for proactive action

---

## Additional BI Tools (Extension Notes)

### Metabase / Redash
- Ad-hoc SQL querying against the same mart tables
- Use `marts_daily_kpis` for daily aggregates
- Expose `conversion_rate` and `net_revenue_usd` as the primary public metrics

### Sigma Computing
- Spreadsheet-like interface on top of the warehouse
- Same semantic layer as Looker — `daily_kpis` and `channel_performance` explores apply
- Metric references map directly to Looker naming conventions

### Mode Analytics
- Primarily used for longitudinal reporting and cohort analysis
- SQL-first; copilot can suggest safe templates using `marts_daily_kpis` and `marts_customer_health`
- Does not expose the Alert Flag calculated field; threshold logic must be applied manually in SQL

---

## Retrieval Routing Quick Reference

| User Question Type | Route To | Answer Template |
|---|---|---|
| "What is conversion_rate?" | kpi_definitions + bi_semantics | Plain-language formula + table source |
| "Why is my dashboard showing an alert?" | bi_semantics (Tableau section) | Alert Flag logic + runbook directive |
| "Which LookML explore has channel metrics?" | bi_semantics (Looker section) | `channel_performance` + measures list |
| "How is customer health scored?" | bi_seminitions + kpi_definitions | Blended formula + marts_customer_health |
| "Which experiment is performing best?" | schema.md + experiment_marts | marts_experiment_performance + variant breakdown |
| "What is the refund rate trend?" | bi_semantics + schema | Refund rate formula + marts_daily_kpis |
