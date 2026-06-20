# Staging Security Smoke Test Checklist

**Environment:** Staging (`APP_ENV=staging`)  
**Run before:** every production deployment  
**Owner:** Backend / DevSecOps  
**Date:** 2026-06-20

---

## How to Use

Work through each section top-to-bottom. Mark each item ✅ pass, ❌ fail, or ⚠️ skip
(with reason). A single ❌ on a P0/P1 item is a deployment blocker.

---

## 1. Authentication

| # | Check | Expected | Priority |
|---|-------|----------|----------|
| 1.1 | `GET /api/inspections` with no `Authorization` header | `401 Unauthorized` | P0 |
| 1.2 | `GET /api/inspections` with `Authorization: Bearer invalid` | `401 Unauthorized` | P0 |
| 1.3 | `GET /api/inspections` with an expired token | `401 Unauthorized` | P0 |
| 1.4 | `GET /api/inspections` with a valid token for correct tenant | `200 OK` | P0 |
| 1.5 | `Authorization: Bearer <alg=none token>` | `401` with "Unsigned JWTs are not allowed" | P0 |
| 1.6 | `Authorization: Bearer <HS256 token>` | `401` with "algorithm is not allowed" | P0 |
| 1.7 | Token with missing `kid` header | `401` with "missing kid" | P1 |

---

## 2. RBAC (Role-Based Access Control)

| # | Check | Expected | Priority |
|---|-------|----------|----------|
| 2.1 | `GET /api/analytics/powerbi` with role `vendor_user` | `403 Forbidden` | P0 |
| 2.2 | `GET /api/analytics/powerbi` with role `spd_manager` | `200 OK` | P0 |
| 2.3 | `POST /stream/frame` with role `viewer` | `403 Forbidden` | P0 |
| 2.4 | `POST /stream/frame` with role `vendor_user` | `200 OK` (or `202 Accepted`) | P0 |
| 2.5 | Enterprise intake routes with no role | `401 Unauthorized` | P1 |
| 2.6 | Enterprise intake routes with `hospital_admin` | `200 OK` | P1 |

---

## 3. Tenant Isolation

| # | Check | Expected | Priority |
|---|-------|----------|----------|
| 3.1 | `GET /api/analytics/powerbi` as `spd_manager` for Tenant A — response contains only Tenant A records | No Tenant B records in response | P0 |
| 3.2 | `GET /api/analytics/powerbi` as platform `admin` — response contains records from all tenants | Multi-tenant rows present | P1 |
| 3.3 | Attempt to read inspections belonging to another tenant using a valid but cross-tenant token | `403 Forbidden` or empty result set | P0 |
| 3.4 | Tenant membership check: user with no `TenantMembership` row in DB | `403 Forbidden` | P1 |
| 3.5 | Tenant membership check: user with disabled membership | `403 Forbidden` | P1 |
| 3.6 | `X-LumenAI-Tenant-ID` header set to a different tenant — JWT claim takes precedence | Response reflects JWT tenant, not header | P0 |

---

## 4. CORS

| # | Check | Expected | Priority |
|---|-------|----------|----------|
| 4.1 | Preflight `OPTIONS` from an allowed origin | `200` with `Access-Control-Allow-Origin` matching request origin | P1 |
| 4.2 | Preflight `OPTIONS` from an unlisted origin | No `Access-Control-Allow-Origin` header (or `null`) | P1 |
| 4.3 | `Access-Control-Allow-Methods` response header | Contains only `GET, POST, PUT, PATCH, DELETE, OPTIONS` — not `*` | P1 |
| 4.4 | `Access-Control-Allow-Headers` response header | Does not contain `*`; contains `Authorization`, `Content-Type` | P1 |

---

## 5. Security Response Headers

| # | Check | Expected | Priority |
|---|-------|----------|----------|
| 5.1 | `X-Content-Type-Options` | `nosniff` | P1 |
| 5.2 | `X-Frame-Options` | `DENY` | P1 |
| 5.3 | `Referrer-Policy` | `no-referrer` | P1 |
| 5.4 | `Permissions-Policy` | Present and restrictive (no `*`) | P1 |
| 5.5 | `Strict-Transport-Security` on staging (if HTTPS) | `max-age=63072000; includeSubDomains; preload` when `APP_ENV=production` | P1 |
| 5.6 | No `Server` header leaking framework/version | Header absent or generic | P2 |

---

## 6. OpenAPI Docs Disabled in Production

| # | Check | Expected | Priority |
|---|-------|----------|----------|
| 6.1 | `GET /docs` with `APP_ENV=production` | `404 Not Found` | P0 |
| 6.2 | `GET /redoc` with `APP_ENV=production` | `404 Not Found` | P0 |
| 6.3 | `GET /openapi.json` with `APP_ENV=production` | `404 Not Found` | P0 |
| 6.4 | `GET /docs` with `APP_ENV=staging` | `200 OK` (docs accessible in non-prod) | P2 |

---

## 7. Analytics Endpoint Protection

| # | Check | Expected | Priority |
|---|-------|----------|----------|
| 7.1 | `GET /api/analytics/powerbi` — no auth | `401` | P0 |
| 7.2 | `GET /api/analytics/powerbi` — `vendor_user` role | `403` | P0 |
| 7.3 | `GET /api/analytics/powerbi` — `spd_manager` role, correct tenant | `200` with scoped data | P0 |
| 7.4 | Response does not include other tenants' inspection IDs | Cross-tenant leak absent | P0 |

---

## 8. Stream Upload Protection

| # | Check | Expected | Priority |
|---|-------|----------|----------|
| 8.1 | `POST /stream/frame` — no auth | `401` | P0 |
| 8.2 | `POST /stream/frame` — valid auth, empty file payload | `400 Bad Request` | P1 |
| 8.3 | `POST /stream/frame` — valid auth, valid frame | `200` / `202` with inspection ID | P0 |
| 8.4 | Created inspection record has correct `tenant_id` from JWT | DB record matches token tenant | P0 |

---

## 9. OIDC / JWKS Configuration

| # | Check | Expected | Priority |
|---|-------|----------|----------|
| 9.1 | `OIDC_JWKS_URL` env var is set | Non-empty URL pointing to issuer JWKS endpoint | P0 |
| 9.2 | `OIDC_ISSUER_URL` env var is set | Matches the `iss` claim in issued tokens | P0 |
| 9.3 | `OIDC_AUDIENCE` env var is set | Matches the `aud` claim in issued tokens | P0 |
| 9.4 | Token from a different issuer is rejected | `401` with "Invalid JWT issuer" | P0 |
| 9.5 | Token with wrong audience is rejected | `401` with "audience" in detail | P0 |
| 9.6 | JWKS key cache refresh: rotate signing key at provider, old tokens still valid within TTL | Graceful key rollover (no outage) | P1 |

---

## 10. Admin Seed Credential

| # | Check | Expected | Priority |
|---|-------|----------|----------|
| 10.1 | `ADMIN_SEED_PASSWORD` env var is set in production secrets | Non-empty, high-entropy value | P0 |
| 10.2 | `POST /users/seed_admin` — password `admin123` does NOT authenticate | `401` | P0 |
| 10.3 | `POST /users/seed_admin` without `ADMIN_SEED_PASSWORD` in production | Server startup raises `RuntimeError` | P0 |

---

## Sign-Off

| Role | Name | Date | Result |
|------|------|------|--------|
| Backend Engineer | | | |
| Security Reviewer | | | |
| DevOps / Deployer | | | |

**Deployment decision:** ☐ GO &nbsp;&nbsp; ☐ NO-GO  
**Blocker(s) if NO-GO:**
