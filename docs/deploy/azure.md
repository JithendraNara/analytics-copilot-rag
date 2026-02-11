# Azure Deployment Runbook (analytics-copilot-rag)

## Recommended Runtime
- Compute: Azure Container Apps or Azure App Service (container)
- Storage: Azure Blob Storage (optional knowledge snapshots)
- Secrets: Azure Key Vault
- Monitoring: Azure Monitor + Application Insights

## Deployment Steps
1. Build and publish container image.
2. Configure app settings for knowledge and index paths.
3. Expose HTTPS ingress and health probe to `/health`.
4. Validate endpoint checks:
   - `GET /health`
   - `POST /v1/index/rebuild`
   - `GET /v1/eval`

## Operational Checks
- Configure health probe alerts.
- Configure error-rate and latency thresholds.
- Track evaluation score trend for regression detection.
