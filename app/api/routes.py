from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException

from app.core.settings import EVAL_PATH, INDEX_PATH, KNOWLEDGE_DIR
from app.models import AskRequest, AskResponse, DomainScore, EvalResponse, SQLSuggestRequest, SQLSuggestResponse
from app.retrieval.indexer import build_index, load_index
from app.retrieval.retriever import retrieve
from app.sql_guardrails import suggest_sql

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "analytics-copilot-rag"}


@router.post("/v1/index/rebuild")
def rebuild_index() -> dict[str, object]:
    docs = build_index(KNOWLEDGE_DIR, INDEX_PATH)
    return {"indexed_chunks": len(docs), "index_path": str(INDEX_PATH)}


@router.post("/v1/ask", response_model=AskResponse)
def ask(req: AskRequest) -> AskResponse:
    docs = load_index(INDEX_PATH)
    if not docs:
        docs = build_index(KNOWLEDGE_DIR, INDEX_PATH)

    matches = retrieve(req.question, docs, top_k=req.top_k)
    if not matches:
        raise HTTPException(status_code=404, detail="no grounded context found")

    answer_lines = ["Grounded findings:"]
    for idx, doc in enumerate(matches, start=1):
        answer_lines.append(f"{idx}. {doc['text']}")

    return AskResponse(
        answer="\n".join(answer_lines),
        sources=sorted({m["source"] for m in matches}),
    )


@router.post("/v1/sql/suggest", response_model=SQLSuggestResponse)
def sql_suggest(req: SQLSuggestRequest) -> SQLSuggestResponse:
    return suggest_sql(req.question)


@router.get("/v1/eval", response_model=EvalResponse)
def evaluate() -> EvalResponse:
    docs = load_index(INDEX_PATH)
    if not docs:
        docs = build_index(KNOWLEDGE_DIR, INDEX_PATH)

    if not EVAL_PATH.exists():
        raise HTTPException(status_code=500, detail=f"missing eval set: {EVAL_PATH}")

    tests = json.loads(EVAL_PATH.read_text(encoding="utf-8"))

    domain_results: dict[str, dict[str, int]] = {}
    for idx, test in enumerate(tests):
        domain = test.get("domain")
        if not isinstance(domain, str) or not domain.strip():
            raise HTTPException(
                status_code=500,
                detail=f"invalid or missing 'domain' in eval test at index {idx}",
            )
        domain = domain.strip()
        domain_results.setdefault(domain, {"total": 0, "passed": 0})

        matches = retrieve(test["question"], docs, top_k=2)
        joined = " ".join(m["text"] for m in matches).lower()
        domain_results[domain]["total"] += 1
        if test["must_include"].lower() in joined:
            domain_results[domain]["passed"] += 1

    domain_breakdown: dict[str, DomainScore] = {
        domain: DomainScore(
            total=counts["total"],
            passed=counts["passed"],
            score=round(counts["passed"] / counts["total"], 4) if counts["total"] else 0.0,
        )
        for domain, counts in domain_results.items()
    }

    all_passed = sum(d["passed"] for d in domain_results.values())
    total = len(tests)
    overall_score = round(all_passed / total, 4) if total else 0.0

    return EvalResponse(
        total=total,
        passed=all_passed,
        score=overall_score,
        domain_breakdown=domain_breakdown,
    )
