# analytics-copilot-rag

RAG-powered analytics assistant grounded in project docs, schemas, and KPI definitions.

## What This Demonstrates
- Grounded retrieval (knowledge-index backed) instead of unconstrained generation.
- Guardrailed SQL suggestion limited to approved analytics marts.
- Simple evaluation harness for retrieval quality tracking.

## Role Positioning
- Primary fit: AI Engineer, Applied AI Engineer, Software Engineer (AI platform)
- Showcase focus: grounded retrieval, safe SQL guardrails, evaluation harness
- Resume mapping: see `PROOF.md` and `RESUME_BULLETS.md`

## Goals
- Grounded Q&A over repository docs.
- Safe SQL suggestion generation from known schema.
- Evaluation set for answer quality.

## Stack
- Python FastAPI
- Lexical retrieval pipeline with evaluation harness
- Safe SQL template guardrails

## Architecture
- `app/retrieval/indexer.py`: chunking + index creation.
- `app/retrieval/retriever.py`: lexical/fuzzy scoring and top-k retrieval.
- `app/sql_guardrails.py`: safe template selection for SQL suggestions.
- `app/api/routes.py`: ask/index/eval/sql endpoints.

## Repository Layout
```text
app/retrieval/          # Index + retrieval logic
app/api/                # FastAPI routes
data/knowledge/         # Grounding corpus
data/eval/              # Evaluation questions
tests/                  # API tests
```

## Endpoints
- `GET /health`
- `POST /v1/index/rebuild`
- `POST /v1/ask`
- `POST /v1/sql/suggest`
- `GET /v1/eval`

## Quick Start
```bash
python3 -m venv --clear .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts/build_index.py
pytest -q
./scripts/run_local.sh
```

## Example Requests
```bash
curl -X POST http://localhost:8090/v1/ask \\
  -H 'Content-Type: application/json' \\
  -d '{\"question\":\"What is conversion_rate?\",\"top_k\":3}'
```

```bash
curl http://localhost:8090/v1/eval
```

## CI
GitHub Actions builds index + runs tests on push/PR:
- `.github/workflows/ci.yml`

## Development Trail
- Roadmap: `ROADMAP.md`
- Changelog: `CHANGELOG.md`
- Proof mapping: `PROOF.md`
- Resume bullets: `RESUME_BULLETS.md`

## Stack Coverage Extension
- Planned gap-coverage work is tracked in `STACK_COVERAGE_PLAN.md`.

## Deployment Runbooks
- AWS: `docs/deploy/aws.md`
- Azure: `docs/deploy/azure.md`
