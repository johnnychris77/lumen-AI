# LumenAI Production Hardening Guide

## Purpose

This guide documents the minimum configuration needed before deploying LumenAI outside local development.

## Required production changes

1. Set APP_ENV=production.
2. Set ENABLE_DEV_AUTH=false.
3. Replace DEV_AUTH_TOKEN=dev-token with a real secret or external auth provider.
4. Set PUBLIC_BASE_URL to the deployed HTTPS domain.
5. Set ALLOWED_ORIGINS to trusted browser origins only.
6. Use a strong database password.
7. Store secrets outside GitHub.
8. Configure SMTP only through environment variables.
9. Keep generated artifacts out of Git.
10. Run the enterprise quality gate before each deployment.

## Local validation

Run:

backend/scripts/local-quality-gate.sh

## Readiness endpoint

curl -sS http://127.0.0.1:18011/api/production-readiness/config \
  -H "Authorization: Bearer dev-token" \
  -H "X-LumenAI-Role: admin" | python -m json.tool

## Secrets policy

Do not commit:

- backend/.env
- root .env
- real SMTP credentials
- production database passwords
- real webhook secrets
- generated board packets or briefing artifacts

## Recommended deployment sequence

1. Pull latest main.
2. Configure environment variables.
3. Set production-safe secrets.
4. Run the local quality gate.
5. Build and deploy.
6. Verify /api/health.
7. Verify /api/production-readiness/config.
8. Verify the executive dashboard.
9. Generate a test KPI snapshot.
10. Generate a test governance packet export.
