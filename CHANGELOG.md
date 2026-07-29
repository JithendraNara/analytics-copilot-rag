# Changelog

All notable changes to this project are documented here.

## [Unreleased]
- Added `app/sql_validator.py` with stricter parsing checks (closes #4).
  Validates every emitted SQL against read-only rules: rejects DDL/DML,
  session-control, procedural, and admin verbs; strips line and block
  comments before keyword analysis so payloads hidden in comments cannot
  smuggle forbidden keywords past the check; enforces single-statement
  queries; and restricts `FROM`/`JOIN` references to the curated mart
  allow-list.
- Wired the validator into `app/sql_guardrails.py` so every suggested
  template round-trips through validation as defense in depth.
- Added `tests/test_sql_validator.py` covering read-only acceptance,
  forbidden-keyword rejection, comment-stripping bypasses, multi-statement
  injection, table allow-list enforcement, CTE handling, and end-to-end
  integration with `/v1/sql/suggest`.
- Planned: milestone-driven work tracked in GitHub issues.

## [0.1.0] - 2026-02-11
### Added
- Initial MVP implementation.
- Role-mapped README and proof-linked resume bullets.
- CI workflow for automated checks.

### Notes
- This release establishes the baseline for iterative weekly improvements.
