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

## Single-origin migration (localStorage token -> httpOnly cookie)

The token-in-localStorage risk cannot be fixed by a naive "use an httpOnly
cookie" swap, because the SPA (`lumen-ai-1.onrender.com`) and API
(`lumen-ai-53u4.onrender.com`) are different *sites* to the browser
(`onrender.com` is on the Public Suffix List). A backend cookie would be
third-party and get blocked. The fix is to put both on ONE origin, then the
session cookie is first-party. Pieces now in the repo:

1. **`frontend/src/lib/api.ts` — the `apiFetch` client.** Single source of truth
   for base URL, auth headers, `credentials`, JSON vs FormData handling, and a
   central 401 -> sign-out. Components call `api.get/post/...` instead of raw
   `fetch`. Cookie cutover is one env flag (`VITE_AUTH_TRANSPORT=cookie`), no
   component edits.
2. **`frontend/nginx.render.conf` + `Dockerfile.render` + entrypoint.** An nginx
   image that serves the SPA and reverse-proxies `/api` to the backend, so the
   browser sees one origin.
3. **`render.yaml` `lumen-ai-web` service.** Runs that image ALONGSIDE the
   existing static `lumen-ai-1` during migration.

Cutover order: deploy `lumen-ai-web`; verify `/healthz` and login; switch the
backend login to set `httpOnly; Secure; SameSite=Lax` and add a CSRF
custom-header check on state-changing routes; point the custom domain at
`lumen-ai-web`; retire `lumen-ai-1`; make `lumen-ai-api` private.

### Converting the remaining components to apiFetch

`EnterpriseAuditTrailPanel.tsx` is the reference conversion. The mechanical
pattern for each remaining file:

- Delete the per-file `const API_BASE = import.meta.env.VITE_API_BASE_URL || …`
  and any `const AUTH_TOKEN = localStorage.getItem("token") …` (the latter is
  also a latent bug — captured once at module load, it goes stale after login).
- Replace `fetch(\`${API_BASE}/api/x\`, { headers: { Authorization: … } })` with
  `api.get("/api/x")` (or `api.post("/api/x", body)`), and read the parsed JSON
  directly instead of calling `response.json()`/checking `response.ok` by hand.
- Keep only *call-specific* headers (e.g. `X-Tenant-Id`) in the options; role,
  actor, token, and Content-Type are attached centrally.
- Do NOT set Content-Type for FormData uploads — `apiFetch` already leaves it
  alone so the multipart boundary is preserved.

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
