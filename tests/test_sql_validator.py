"""
Security tests for :mod:`app.sql_validator`.

The validator gates every SQL string the analytics copilot emits. The
tests below cover the threat model documented in the module docstring:

* Read-only entry points (SELECT, WITH) are accepted.
* DDL, DML, session, procedural, and admin keywords are rejected even
  when smuggled inside comments or subqueries.
* Comment-stripping bypasses (``/* DROP TABLE x */ SELECT 1``) are
  caught because comments are stripped before keyword analysis.
* Multiple statements (``SELECT 1; DROP TABLE x``) are rejected.
* Tables outside the mart allow-list are rejected.
* The /v1/sql/suggest endpoint always returns SQL that the validator
  accepts, and any payload that would fail validation never reaches
  the response.
"""

from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.sql_validator import (
    ALLOWED_MART_TABLES,
    _strip_comments,
    validate_sql,
)

client = TestClient(app)


# ─── Unit tests: validator primitives ───────────────────────────────────────

class TestStripComments:
    """``_strip_comments`` must remove both line and block comments."""

    def test_line_comment_removed(self) -> None:
        assert _strip_comments("SELECT 1 -- trailing\nFROM x") == "SELECT 1  \nFROM x"

    def test_block_comment_removed(self) -> None:
        assert (
            _strip_comments("SELECT /* hidden */ 1 FROM x")
            == "SELECT   1 FROM x"
        )

    def test_multiline_block_comment_removed(self) -> None:
        sql = "SELECT 1\n/* line1\nline2\nline3 */\nFROM x"
        out = _strip_comments(sql)
        assert "DROP" not in out
        assert "line1" not in out

    def test_block_comment_containing_line_comment_marker(self) -> None:
        # A ``--`` inside a block comment must not start a line comment
        # when the block is stripped first.
        sql = "/* keep -- this */ SELECT 1"
        assert _strip_comments(sql).strip() == "SELECT 1"


# ─── Unit tests: validator happy path ───────────────────────────────────────

class TestValidateAcceptsReadOnly:
    """All read-only SELECT / WITH shapes must pass validation."""

    @pytest.mark.parametrize(
        "sql",
        [
            "SELECT 1",
            "SELECT metric_date FROM marts_daily_kpis",
            "SELECT metric_date FROM marts_daily_kpis LIMIT 30",
            "SELECT metric_date FROM marts_daily_kpis ORDER BY metric_date DESC",
            "SELECT a.x, b.y FROM marts_daily_kpis a JOIN marts_channel_performance b ON a.x = b.y",
            "WITH cte AS (SELECT 1 AS v) SELECT v FROM cte",
            "SELECT COUNT(*) FROM marts_daily_kpis WHERE paid_conversions > 0",
            "SELECT CASE WHEN 1=1 THEN 1 ELSE 0 END FROM marts_daily_kpis",
            "SELECT * FROM marts_daily_kpis WHERE metric_date BETWEEN '2026-01-01' AND '2026-01-31'",
            # ``updated_at`` must not trigger the UPDATE keyword check.
            "SELECT updated_at FROM marts_daily_kpis",
            # ``droptable`` is an identifier, not the DROP keyword.
            'SELECT "droptable" FROM marts_daily_kpis',
        ],
    )
    def test_select_passes(self, sql: str) -> None:
        valid, reason = validate_sql(sql)
        assert valid is True, f"unexpectedly rejected: {reason} ({sql!r})"
        assert reason == ""


# ─── Unit tests: DDL/DML rejection ───────────────────────────────────────────

class TestValidateRejectsMutating:
    """Every forbidden keyword must be rejected, even when smuggled."""

    @pytest.mark.parametrize(
        "sql",
        [
            "DROP TABLE marts_daily_kpis",
            "drop table marts_daily_kpis",
            "ALTER TABLE marts_daily_kpis ADD COLUMN x INT",
            "CREATE TABLE x (y INT)",
            "TRUNCATE marts_daily_kpis",
            "RENAME TABLE x TO y",
            "COMMENT ON TABLE x IS 'leak'",
            "INSERT INTO marts_daily_kpis VALUES (1)",
            "UPDATE marts_daily_kpis SET x = 1",
            "DELETE FROM marts_daily_kpis",
            "MERGE INTO marts_daily_kpis USING x ON 1=1",
            "REPLACE INTO marts_daily_kpis VALUES (1)",
            "GRANT SELECT ON marts_daily_kpis TO public",
            "REVOKE SELECT ON marts_daily_kpis FROM public",
            "SET search_path TO public",
            "RESET search_path",
            "CALL my_proc()",
            "EXEC my_proc",
            "EXECUTE my_proc",
            "DO $$ BEGIN RAISE NOTICE 'leak'; END $$",
            "COPY marts_daily_kpis FROM '/tmp/x'",
            "VACUUM FULL marts_daily_kpis",
            "ANALYZE marts_daily_kpis",
            "REINDEX INDEX marts_daily_kpis_idx",
            "LOCK TABLE marts_daily_kpis",
            "EXPLAIN ANALYZE SELECT * FROM marts_daily_kpis",
            "SHOW TABLES",
            "DESCRIBE marts_daily_kpis",
            "BEGIN",
            "COMMIT",
            "ROLLBACK",
            "START TRANSACTION",
        ],
    )
    def test_forbidden_keyword_rejected(self, sql: str) -> None:
        valid, reason = validate_sql(sql)
        assert valid is False, f"should reject {sql!r}"
        assert reason  # non-empty reason describes why


# ─── Unit tests: comment-stripping bypass attempts ───────────────────────────

class TestValidateRejectsCommentBypasses:
    """Forbidden keywords hidden in comments must not slip past."""

    @pytest.mark.parametrize(
        "sql",
        [
            # Classic injection: payload hidden in a block comment that
            # is followed by a benign SELECT. The keyword is in the
            # *first* statement so it must be the leading keyword.
            "DROP TABLE marts_daily_kpis; SELECT 1",
            # Comment containing a forbidden keyword followed by a real
            # SELECT — the keyword lives in the comment and must be
            # stripped before analysis.
            "/* DROP TABLE marts_daily_kpis */ SELECT 1 FROM marts_daily_kpis",
            "-- DELETE FROM marts_daily_kpis\nSELECT 1 FROM marts_daily_kpis",
            # Multi-line comment with a forbidden keyword.
            "/*\nUPDATE marts_daily_kpis SET x = 1\n*/ SELECT 1 FROM marts_daily_kpis",
            # Line comment at end of an otherwise valid SELECT.
            "SELECT 1 FROM marts_daily_kpis -- DROP TABLE x",
        ],
    )
    def test_comment_bypass_rejected_or_safe(self, sql: str) -> None:
        """These inputs must either pass cleanly (when the forbidden
        keyword is inside a comment) or be rejected outright. They must
        never silently approve a statement that contains a live
        forbidden keyword.
        """
        valid, _ = validate_sql(sql)
        cleaned = _strip_comments(sql)
        # If a forbidden keyword survives comment stripping, the
        # validator must reject it. If the keyword only existed in the
        # comment, the validator must accept it.
        forbidden_keywords = {
            "DROP", "DELETE", "INSERT", "UPDATE", "ALTER", "CREATE",
            "TRUNCATE", "MERGE", "GRANT", "REVOKE", "EXEC", "CALL",
            "COPY", "VACUUM", "ANALYZE", "REINDEX", "EXPLAIN", "SHOW",
            "DESCRIBE", "COMMIT", "ROLLBACK", "BEGIN",
        }
        live_keyword = any(
            f" {kw} " in f" {cleaned.upper()} " or cleaned.upper().startswith(f"{kw} ")
            for kw in forbidden_keywords
        )
        if live_keyword:
            assert valid is False, f"must reject {sql!r}"
        else:
            assert valid is True, f"must accept {sql!r}"

    def test_subquery_with_delete_blocked(self) -> None:
        """A forbidden keyword nested inside a subquery must be blocked."""
        sql = (
            "SELECT (DELETE FROM marts_daily_kpis RETURNING metric_date) "
            "FROM marts_daily_kpis"
        )
        valid, reason = validate_sql(sql)
        assert valid is False
        assert "DELETE" in reason


# ─── Unit tests: multi-statement guard ───────────────────────────────────────

class TestValidateRejectsMultiStatement:
    """Anything with more than one statement must be rejected."""

    @pytest.mark.parametrize(
        "sql",
        [
            "SELECT 1 FROM marts_daily_kpis; DROP TABLE x",
            "SELECT 1; SELECT 2",
            "SELECT 1 FROM marts_daily_kpis;\nUPDATE x SET y = 1",
            # Whitespace-only between statements.
            "SELECT 1 FROM marts_daily_kpis;    DROP TABLE x",
        ],
    )
    def test_multi_statement_rejected(self, sql: str) -> None:
        valid, reason = validate_sql(sql)
        assert valid is False
        assert "multiple statements" in reason or "forbidden" in reason

    def test_trailing_semicolon_allowed(self) -> None:
        """A single trailing semicolon is normal SQL syntax and must be
        accepted; only *additional* semicolon-separated statements are
        rejected.
        """
        valid, reason = validate_sql("SELECT 1 FROM marts_daily_kpis;")
        assert valid is True, f"unexpectedly rejected: {reason}"


# ─── Unit tests: table allow-list ────────────────────────────────────────────

class TestValidateTableAllowList:
    """Tables outside the mart allow-list must be rejected."""

    def test_unknown_table_rejected(self) -> None:
        valid, reason = validate_sql("SELECT * FROM users")
        assert valid is False
        assert "users" in reason
        assert "allow-list" in reason

    def test_join_unknown_table_rejected(self) -> None:
        sql = (
            "SELECT a.x FROM marts_daily_kpis a "
            "JOIN users b ON a.x = b.x"
        )
        valid, reason = validate_sql(sql)
        assert valid is False
        assert "users" in reason

    def test_schema_qualified_allowed_table_accepted(self) -> None:
        # ``public.marts_daily_kpis`` is allow-listed because the bare
        # identifier matches the allow-list entry.
        valid, _ = validate_sql("SELECT 1 FROM public.marts_daily_kpis")
        assert valid is True

    def test_schema_qualified_unknown_table_rejected(self) -> None:
        valid, reason = validate_sql("SELECT 1 FROM public.users")
        assert valid is False
        assert "users" in reason

    def test_custom_allow_list(self) -> None:
        # A custom allow-list lets the caller reuse the validator for
        # non-mart queries (e.g. admin tools) without forking the rule
        # set.
        valid, _ = validate_sql(
            "SELECT 1 FROM other_table",
            allowed_tables=frozenset({"other_table"}),
        )
        assert valid is True

    def test_default_allow_list_contains_all_marts(self) -> None:
        # Sanity check: every documented mart is present.
        expected = {
            "marts_daily_kpis",
            "marts_channel_performance",
            "marts_experiment_performance",
            "marts_customer_health",
        }
        assert expected.issubset(ALLOWED_MART_TABLES)


# ─── Unit tests: input validation ────────────────────────────────────────────

class TestValidateInputGuards:
    """Non-SQL and malformed inputs must be rejected safely."""

    @pytest.mark.parametrize("sql", ["", "   ", "\n\n", None])
    def test_empty_or_none_rejected(self, sql: object) -> None:
        valid, reason = validate_sql(sql)  # type: ignore[arg-type]
        assert valid is False
        assert reason

    def test_non_string_rejected(self) -> None:
        valid, reason = validate_sql(123)  # type: ignore[arg-type]
        assert valid is False
        assert "string" in reason

    def test_garbage_rejected(self) -> None:
        valid, reason = validate_sql("hello world")
        assert valid is False
        assert reason


# ─── Integration tests: /v1/sql/suggest ──────────────────────────────────────

class TestSQLSuggestIntegration:
    """The /v1/sql/suggest endpoint must always emit validator-clean SQL."""

    def test_endpoint_payload_returns_validator_clean_sql(self) -> None:
        res = client.post(
            "/v1/sql/suggest", json={"question": "show channel performance"}
        )
        assert res.status_code == 200
        body = res.json()
        valid, reason = validate_sql(body["sql"])
        assert valid is True, (
            f"/v1/sql/suggest returned validator-rejected SQL: {reason} "
            f"({body['sql']!r})"
        )

    @pytest.mark.parametrize(
        "payload",
        [
            "'; DROP TABLE marts_daily_kpis;--",
            "1 OR 1=1; --",
            "UNION SELECT * FROM users",
            "'; DELETE FROM marts_daily_kpis WHERE 1=1;--",
            "/* test */",
            "show me conversion rate",
            "channel performance please",
        ],
    )
    def test_adversarial_payload_returns_safe_sql(self, payload: str) -> None:
        """Even adversarial questions must yield validator-clean SQL."""
        res = client.post("/v1/sql/suggest", json={"question": payload})
        assert res.status_code == 200
        body = res.json()
        valid, reason = validate_sql(body["sql"])
        assert valid is True, (
            f"endpoint emitted invalid SQL for payload {payload!r}: "
            f"{reason} ({body['sql']!r})"
        )
        assert body["safe_sql"] is True
        # The response's claimed table must match what the validator
        # observes in the SQL — preventing label/contents divergence.
        refs = [t for t in body["sql"].lower().split() if t.startswith("marts_")]
        for ref in refs:
            assert ref in body["table"].lower()

    def test_all_templates_are_validator_clean(self) -> None:
        """Every entry in SAFE_TEMPLATES must round-trip through the
        validator. This guards against accidental template drift.
        """
        from app.sql_guardrails import SAFE_TEMPLATES

        for key, (_table, sql, _rationale) in SAFE_TEMPLATES.items():
            valid, reason = validate_sql(sql)
            assert valid is True, (
                f"SAFE_TEMPLATES[{key!r}] produced validator-rejected "
                f"SQL: {reason} ({sql!r})"
            )