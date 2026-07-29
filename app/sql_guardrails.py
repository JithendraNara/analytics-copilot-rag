from __future__ import annotations

from app.models import SQLSuggestResponse
from app.sql_validator import validate_sql

SAFE_TEMPLATES = {
    "conversion": (
        "marts_daily_kpis",
        "SELECT metric_date, new_users, paid_conversions, conversion_rate "
        "FROM marts_daily_kpis ORDER BY metric_date DESC LIMIT 30;",
        "Tracks conversion trend from daily KPI mart.",
    ),
    "revenue": (
        "marts_daily_kpis",
        "SELECT metric_date, gross_revenue_usd, refunded_usd, net_revenue_usd "
        "FROM marts_daily_kpis ORDER BY metric_date DESC LIMIT 30;",
        "Monitors top-line and net revenue movement.",
    ),
    "channel": (
        "marts_channel_performance",
        "SELECT acquisition_channel, signups, paying_users, paid_conversion_rate, net_revenue_usd "
        "FROM marts_channel_performance ORDER BY net_revenue_usd DESC;",
        "Compares acquisition channels by conversion and revenue.",
    ),
    "experiment": (
        "marts_experiment_performance",
        "SELECT experiment_name, experiment_variant, users_exposed, users_converted, conversion_rate "
        "FROM marts_experiment_performance ORDER BY users_exposed DESC;",
        "Evaluates experiment outcomes by variant.",
    ),
    "health": (
        "marts_customer_health",
        "SELECT user_id, plan_tier, sessions_last_30d, net_revenue_usd, customer_health_score "
        "FROM marts_customer_health ORDER BY customer_health_score ASC LIMIT 50;",
        "Finds users with weak health scores for retention follow-up.",
    ),
}


def suggest_sql(question: str) -> SQLSuggestResponse:
    q = question.lower()
    if "experiment" in q or "variant" in q:
        key = "experiment"
    elif "channel" in q:
        key = "channel"
    elif "health" in q or "churn" in q:
        key = "health"
    elif "revenue" in q or "refund" in q:
        key = "revenue"
    else:
        key = "conversion"

    table, sql, rationale = SAFE_TEMPLATES[key]
    # Defense in depth: every template must round-trip through the
    # validator. If a future template edit silently introduces a
    # forbidden keyword or unlisted table, the validator catches it
    # here instead of leaking through the API.
    valid, reason = validate_sql(sql)
    if not valid:
        raise RuntimeError(
            f"SAFE_TEMPLATES produced sql that failed validation: {reason}"
        )
    return SQLSuggestResponse(sql=sql, table=table, safe_sql=True, rationale=rationale)
