# Environment Variable Checklist

## Required

APP_ENV=production
API_PREFIX=/api
PUBLIC_BASE_URL=https://your-public-demo-url
DATABASE_URL=postgresql+psycopg2://USER:PASSWORD@HOST:PORT/DB
REDIS_URL=redis://HOST:PORT/0

## Auth

ENABLE_DEV_AUTH=false
DEV_AUTH_TOKEN=replace-with-real-secret-or-disable
LUMENAI_JWT_SECRET=replace-with-strong-secret

## Governance

ENABLE_ENTERPRISE_AUDIT=true
ENABLE_ENTERPRISE_RBAC=true

## CORS

ALLOWED_ORIGINS=https://your-public-frontend-url

## Do Not Commit

- real SMTP passwords
- real Slack webhook URLs
- production database passwords
- production JWT secrets
- .env
- backend/.env
