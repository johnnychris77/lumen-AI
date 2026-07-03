# LumenAI Production Hardening Guide

## Purpose

This guide documents the minimum configuration needed before deploying LumenAI outside local development.

## Required production changes

1. Set APP_ENV=production **and** ENVIRONMENT=production (both are checked; the
   app refuses to boot if SECRET_KEY is still the default under either).
2. Set ENABLE_DEV_AUTH=false.
3. Set AUTH_MODE explicitly. The app refuses to boot in production if AUTH_MODE
   is unset. Use AUTH_MODE=oidc with OIDC_ISSUER_URL and OIDC_AUDIENCE.
   AUTH_MODE=dev in production additionally requires ALLOW_DEV_AUTH_IN_PROD=true
   as a deliberate, auditable exception (controlled pilot demos only).
4. Set a strong SECRET_KEY (render.yaml generates one). This signs app-issued
   login tokens; the default value is rejected in production.
5. Set PUBLIC_BASE_URL to the deployed HTTPS domain.
6. Set ALLOWED_ORIGINS and CORS_ORIGIN_REGEX to the exact frontend origin only.
   Do NOT widen CORS to all *.onrender.com — that lets any Render-hosted site
   make credentialed cross-origin requests.
7. Use a strong database password.
8. Store secrets outside GitHub.
9. Configure SMTP only through environment variables.
10. Keep generated artifacts out of Git.
11. Run the enterprise quality gate before each deployment.

## Identity & role trust model

Identity and role are resolved server-side from a validated bearer token
(dev-token map in non-prod, or a login JWT with the role read from the
database). The `X-LumenAI-Role` / `X-LumenAI-Actor` headers are advisory
labels only and are never trusted to authorize a request or to relabel audit
records. Regression coverage:
`backend/tests/test_header_role_privilege_escalation.py`.

## Tracked follow-ups (not yet done)

- **Auth token is stored in localStorage** (`frontend/src/lib/auth.tsx`), which
  is readable by any XSS. Migrating to httpOnly, SameSite cookies (with the
  matching backend Set-Cookie + CSRF handling) removes token theft via XSS and
  is the recommended next hardening step before broad production rollout.
- **No refresh/revocation flow.** Access-token lifetime is now 60 min by
  default (was 8 h); add refresh + a revocation list before long-lived sessions.

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
