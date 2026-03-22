from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health() -> None:
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_ask_and_sql_suggest() -> None:
    ask_res = client.post("/v1/ask", json={"question": "what is conversion_rate?", "top_k": 2})
    assert ask_res.status_code == 200
    assert "Grounded findings" in ask_res.json()["answer"]

    sql_res = client.post("/v1/sql/suggest", json={"question": "show channel performance"})
    assert sql_res.status_code == 200
    body = sql_res.json()
    assert body["safe_sql"] is True
    assert body["table"] == "marts_channel_performance"


def test_eval_domain_breakdown() -> None:
    res = client.get("/v1/eval")
    assert res.status_code == 200
    body = res.json()

    # Core fields present
    assert "total" in body
    assert "passed" in body
    assert "score" in body
    assert "domain_breakdown" in body

    breakdown = body["domain_breakdown"]
    assert isinstance(breakdown, dict)
    assert len(breakdown) > 0

    # Each domain has required fields
    for domain, scores in breakdown.items():
        assert "total" in scores
        assert "passed" in scores
        assert "score" in scores
        assert 0.0 <= scores["score"] <= 1.0
        assert scores["passed"] <= scores["total"]

    # Overall score matches sum of domain scores weighted by domain totals
    total = body["total"]
    all_passed = sum(d["passed"] for d in breakdown.values())
    assert body["passed"] == all_passed
    expected_score = round(all_passed / total, 4) if total else 0.0
    assert body["score"] == expected_score
