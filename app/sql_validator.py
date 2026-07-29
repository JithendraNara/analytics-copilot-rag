"""
SQL validator: enforces read-only, single-statement, allow-listed queries.

This module exists because the analytics copilot must never emit SQL that
could mutate state (DDL/DML) or reference tables outside the approved
analytics marts. The static templates in :mod:`app.sql_guardrails` are safe
by construction, but every code path that emits SQL should additionally
funnel through :func:`validate_sql` so that a future template edit, prompt
contamination, or model regression cannot silently produce a dangerous
query.

The validator is intentionally strict but pragmatic:

* It strips line (``-- ...``) and block (``/* ... */``) comments before
  scanning so that payloads hidden in comments cannot smuggle keywords
  past the keyword check.
* It rejects any input containing more than one ``;``-delimited statement
  to defeat classic SQL injection chains like
  ``SELECT 1 FROM marts_daily_kpis; DROP TABLE users``.
* The first remaining keyword must be a read-only entry point
  (``SELECT`` or ``WITH``); a leading ``DROP``, ``DELETE``, etc. is rejected
  even if a benign clause appears later in the string.
* It scans the *whole* remaining SQL for forbidden keywords at word
  boundaries so that subqueries or expressions cannot reintroduce DDL/DML
  (``SELECT (DELETE FROM users RETURNING id)`` is blocked).
* Every table referenced via ``FROM`` or ``JOIN`` must appear in the
  configured allow-list; the default allow-list is the curated set of
  analytics mart tables.

The validator deliberately does not parse SQL with a full grammar. A full
parser would be safer but adds a heavy dependency and a much larger
attack surface. The regex-based checks below are sufficient for the
threat model: the validator is a defense-in-depth gate around the static
template picker, not a general-purpose SQL interpreter.
"""

from __future__ import annotations

import re

# Mart tables that the analytics copilot is permitted to query. Anything
# else (e.g. ``users``, ``pg_catalog``) is rejected. Keep this list in
# sync with the curated marts that ship under ``data/knowledge``.
ALLOWED_MART_TABLES: frozenset[str] = frozenset(
    {
        "marts_daily_kpis",
        "marts_channel_performance",
        "marts_experiment_performance",
        "marts_customer_health",
    }
)

# Read-only entry points. The first non-whitespace, non-comment keyword
# must be one of these. ``WITH`` is included so CTEs (``WITH cte AS
# (...) SELECT ...``) are accepted.
_READ_ONLY_LEAD_KEYWORDS: frozenset[str] = frozenset({"SELECT", "WITH"})

# Keywords that indicate a statement can mutate state, schema, session,
# or otherwise leave the read-only envelope. Matches are performed at
# word boundaries so substrings inside identifiers (``updated_at``) do
# not trigger a false positive. ``REPLACE`` covers SQLite/MySQL's
# upsert-style DML; ``COPY`` covers PostgreSQL bulk load; ``VACUUM``,
# ``ANALYZE``, ``REINDEX``, ``EXPLAIN`` are admin verbs that can be
# surprising to expose even read-only because they hit write paths or
# leak planner information.
_FORBIDDEN_KEYWORDS: frozenset[str] = frozenset(
    {
        # DDL
        "CREATE",
        "ALTER",
        "DROP",
        "TRUNCATE",
        "RENAME",
        "COMMENT",
        # DML
        "INSERT",
        "UPDATE",
        "DELETE",
        "MERGE",
        "UPSERT",
        "REPLACE",
        # Permissions / session
        "GRANT",
        "REVOKE",
        "SET",
        "RESET",
        # Procedural / server-side
        "CALL",
        "EXEC",
        "EXECUTE",
        "DO",
        # Bulk / admin
        "COPY",
        "VACUUM",
        "ANALYZE",
        "REINDEX",
        "LOCK",
        # Diagnostics (can leak info even when read-only looking)
        "EXPLAIN",
        "SHOW",
        "DESCRIBE",
        # Transaction control that can mask a preceding mutation
        "COMMIT",
        "ROLLBACK",
        "BEGIN",
        "START",
    }
)

# Regex for line comments (``-- ...`` until end of line).
_LINE_COMMENT_RE = re.compile(r"--[^\n\r]*")

# Regex for block comments (``/* ... */``); non-greedy and dotall so it
# spans newlines correctly.
_BLOCK_COMMENT_RE = re.compile(r"/\*.*?\*/", re.DOTALL)

# Statements are separated by ``;`` outside of comments. We split on
# the comment-stripped string but also enforce that the original SQL
# does not contain a ``;`` inside a comment by stripping comments first.
_STATEMENT_SPLIT_RE = re.compile(r";\s*")

# Extract table references after ``FROM`` or ``JOIN``. The regex permits
# an optional ``schema.`` prefix and an optional ``AS alias`` /
# bare alias; we only capture the bare identifier at the end. The match
# is performed case-insensitively.
_TABLE_REF_RE = re.compile(
    r"\b(?:FROM|JOIN)\s+(?:\"?[A-Za-z_][A-Za-z0-9_]*\"?\.)?\"?([A-Za-z_][A-Za-z0-9_]*)\"?",
    re.IGNORECASE,
)

# Match a Common Table Expression declaration: ``name AS (``. The
# captured identifier becomes a virtual table that the outer query may
# reference without falling foul of the table allow-list. CTE bodies
# themselves still must reference allow-listed tables, because we still
# scan the whole statement for ``FROM`` / ``JOIN``.
_CTE_DECL_RE = re.compile(
    r"\b([A-Za-z_][A-Za-z0-9_]*)\s+AS\s*\(",
    re.IGNORECASE,
)

# Match a keyword at word boundaries so identifiers such as
# ``updated_at`` or ``droptable`` do not produce false positives.
_KEYWORD_RE_TEMPLATE = r"\b{kw}\b"


def _strip_comments(sql: str) -> str:
    """Return ``sql`` with line and block comments removed.

    Block comments are stripped first so that a ``--`` inside a block
    comment does not get treated as a line comment, and vice versa.
    """
    cleaned = _BLOCK_COMMENT_RE.sub(" ", sql)
    cleaned = _LINE_COMMENT_RE.sub(" ", cleaned)
    return cleaned


def _first_keyword(stmt: str) -> str | None:
    """Return the first lexical token of ``stmt`` or ``None``.

    The token is upper-cased so callers can compare against
    :data:`_READ_ONLY_LEAD_KEYWORDS`.
    """
    match = re.search(r"[A-Za-z_]+", stmt)
    if not match:
        return None
    return match.group(0).upper()


def _has_forbidden_keyword(stmt: str) -> str | None:
    """Return the first forbidden keyword found in ``stmt`` (upper-cased)
    or ``None`` when none is present.
    """
    upper = stmt.upper()
    for kw in _FORBIDDEN_KEYWORDS:
        if re.search(_KEYWORD_RE_TEMPLATE.format(kw=kw), upper):
            return kw
    return None


def _referenced_tables(stmt: str) -> list[str]:
    """Return the list of unquoted table names referenced by ``stmt``.

    Only ``FROM`` and ``JOIN`` are scanned because those are the entry
    points through which a query can read data; subqueries and CTEs are
    recursively valid as long as their own ``FROM`` references are
    allow-listed. Quoted identifiers (``"my.table"``) are unwrapped so
    case-sensitive databases work transparently.
    """
    return [m.group(1).lower() for m in _TABLE_REF_RE.finditer(stmt)]


def _declared_cte_names(stmt: str) -> set[str]:
    """Return the lower-cased identifiers declared as CTEs in ``stmt``.

    A CTE declaration has the shape ``name AS (``. The CTE name then
    becomes a virtual table that the outer ``FROM`` may reference
    without falling foul of the table allow-list. CTE bodies are still
    scanned for ``FROM`` references because those reference real
    tables.
    """
    return {m.group(1).lower() for m in _CTE_DECL_RE.finditer(stmt)}


def validate_sql(
    sql: str,
    *,
    allowed_tables: frozenset[str] | None = None,
) -> tuple[bool, str]:
    """Validate ``sql`` against the read-only, single-statement rules.

    Returns ``(is_valid, reason)``. ``is_valid`` is ``True`` only when
    ``sql`` passes every check; ``reason`` is an empty string on success
    and a short explanation on failure. The check order is chosen so
    that the most informative failure is reported first: multi-statement
    injections are reported before keyword violations, keyword violations
    before table allow-list violations.

    ``allowed_tables`` defaults to :data:`ALLOWED_MART_TABLES`. Tests
    may pass a custom set to exercise the table allow-list without
    touching the production configuration.
    """
    if not isinstance(sql, str):
        return False, "sql must be a string"
    if not sql.strip():
        return False, "empty sql"

    tables = (
        set(allowed_tables) if allowed_tables is not None else set(ALLOWED_MART_TABLES)
    )

    # Strip comments before any further analysis so that payloads hidden
    # in ``/* ... */`` or ``-- ...`` cannot smuggle keywords past the
    # keyword check. We retain the original statement count for the
    # multi-statement guard.
    cleaned = _strip_comments(sql)

    # Multi-statement guard. We split on the comment-stripped text and
    # also require the original text not to contain a bare ``;`` inside
    # a string literal — for this threat model we treat any ``;`` not
    # inside a comment as a statement separator.
    statements = [s for s in _STATEMENT_SPLIT_RE.split(cleaned) if s.strip()]
    if len(statements) != 1:
        return False, f"multiple statements detected ({len(statements)} found)"

    stmt = statements[0]

    # Lead keyword must be SELECT or WITH.
    lead = _first_keyword(stmt)
    if lead is None:
        return False, "no recognizable sql keyword found"
    if lead not in _READ_ONLY_LEAD_KEYWORDS:
        return (
            False,
            f"statement must start with SELECT or WITH (got '{lead}')",
        )

    # No forbidden keywords anywhere in the statement, including inside
    # subqueries and expressions.
    bad = _has_forbidden_keyword(stmt)
    if bad is not None:
        return False, f"forbidden keyword detected: {bad}"

    # Every referenced table must be allow-listed. We tolerate an empty
    # table list (``SELECT 1`` is a legitimate probe query) so the
    # validator can be reused for non-mart probes. CTE names declared
    # in the same statement are treated as virtual tables so that a CTE
    # like ``WITH cte AS (...) SELECT * FROM cte`` is accepted even
    # though ``cte`` is not in the production allow-list.
    refs = _referenced_tables(stmt)
    ctes = _declared_cte_names(stmt)
    disallowed = [t for t in refs if t not in tables and t not in ctes]
    if disallowed:
        return (
            False,
            f"table(s) not in allow-list: {', '.join(sorted(disallowed))}",
        )

    return True, ""