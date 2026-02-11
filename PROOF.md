# Proof Map

| ID | Claim | Evidence | Metric |
|---|---|---|---|
| C1 | Implemented grounded retrieval over local knowledge docs. | `app/retrieval/indexer.py`, `app/retrieval/retriever.py` | Indexed chunk corpus with top-k retrieval |
| C2 | Added safe SQL suggestion constrained to approved marts. | `app/sql_guardrails.py` | SQL templates map to approved mart tables |
| C3 | Added lightweight evaluation harness for retrieval quality. | `app/api/routes.py` (`/v1/eval`), `data/eval/questions.json` | Pass rate over eval question set |
| C4 | Added cloud deployment runbooks with operational health checks for AWS and Azure runtimes. | `docs/deploy/aws.md`, `docs/deploy/azure.md` | End-to-end deploy + health/eval validation steps documented |
