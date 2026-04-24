from __future__ import annotations

from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    question: str = Field(min_length=3)
    top_k: int = Field(default=3, ge=1, le=8)


class AskResponse(BaseModel):
    answer: str
    sources: list[str]
    citations: list[dict] = Field(
        default_factory=list,
        description="Grounded citations with source-linked spans: id, source file, and text chunk"
    )


class SQLSuggestRequest(BaseModel):
    question: str = Field(min_length=3)


class SQLSuggestResponse(BaseModel):
    sql: str
    table: str
    safe_sql: bool
    rationale: str


class DomainScore(BaseModel):
    total: int
    passed: int
    score: float


class EvalResponse(BaseModel):
    total: int
    passed: int
    score: float
    domain_breakdown: dict[str, DomainScore] = Field(
        default_factory=dict,
        description="Score breakdown per domain, e.g. {'core_kpi': {'total': 2, 'passed': 1, 'score': 0.5}}"
    )
