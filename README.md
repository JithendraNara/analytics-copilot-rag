# signal-copilot

RAG-powered analytics assistant grounded in project docs, schemas, and KPI definitions.

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
