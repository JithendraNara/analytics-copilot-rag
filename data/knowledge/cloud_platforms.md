# Cloud Platform Guidance

This note summarizes cloud deployment patterns referenced by the runbooks.

## AWS Pattern
- Deploy API services to ECS Fargate.
- Store secrets in AWS Secrets Manager.
- Use EventBridge for schedules and CloudWatch for alarms.
- Validate with `/health` and `/v1/eval` endpoints after deployment.

## Azure Pattern
- Deploy API services to Azure Container Apps or AKS.
- Store secrets in Azure Key Vault.
- Use Azure Data Factory or scheduled jobs for orchestration.
- Validate with `/health` and `/v1/eval` endpoints after deployment.

## Shared Operational Checks
- Endpoint health is green.
- Retrieval eval score is above baseline.
- Alert or KPI endpoints match expected response schema.
