# AWS Deployment Runbook (analytics-copilot-rag)

## Recommended Runtime
- Compute: ECS Fargate or App Runner
- Networking: ALB + private service subnet
- Storage: S3 for optional knowledge snapshots
- Secrets: AWS Secrets Manager
- Monitoring: CloudWatch logs + alarms

## Deployment Steps
1. Build and push container image.
2. Set environment vars (`COPILOT_KNOWLEDGE_DIR`, `COPILOT_INDEX_PATH`, `COPILOT_EVAL_PATH`).
3. Deploy service with health endpoint `/health`.
4. Run post-deploy checks:
   - `GET /health`
   - `POST /v1/index/rebuild`
   - `GET /v1/eval`

## Operational Checks
- Alert when `/health` fails for 3 consecutive intervals.
- Alert when eval score drops below expected baseline.
- Track request/latency trends by endpoint.
