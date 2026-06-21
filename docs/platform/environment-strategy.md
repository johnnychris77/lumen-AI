# LumenAI Environment Strategy

## Overview

LumenAI operates across four environments with progressively stricter security and infrastructure requirements.

---

## Environment Matrix

| Variable              | local                                | development                          | staging                                     | production                                  |
|-----------------------|--------------------------------------|--------------------------------------|---------------------------------------------|---------------------------------------------|
| `ENVIRONMENT`         | `local`                              | `development`                        | `staging`                                   | `production`                                |
| `DATABASE_URL`        | `sqlite:///./lumenai.db`             | `sqlite:///./lumenai.db` or PG dev   | `postgresql+psycopg2://...staging-db.../lumenai` | `postgresql+psycopg2://...prod-db.../lumenai` |
| `SECRET_KEY`          | `dev-secret-change-in-production`    | `dev-secret-change-in-production`    | From Secrets Manager                        | From Secrets Manager (rotated quarterly)    |
| `STRIPE_SECRET_KEY`   | `` (empty)                           | `sk_test_...`                        | `sk_test_...`                               | `sk_live_...` (from Secrets Manager)        |
| `FDA_API_KEY`         | `` (empty / mock)                    | `test-fda-key`                       | `staging-fda-key`                           | From Secrets Manager                        |
| `CORS_ORIGINS`        | `http://localhost:5173`              | `http://localhost:5173`              | `https://staging.lumenai.health`            | `https://app.lumenai.health,https://*.hospital-domain.com` |
| `LOG_LEVEL`           | `DEBUG`                              | `DEBUG`                              | `INFO`                                      | `WARNING`                                   |
| `JWKS_URL`            | `` (dev-token mode)                  | `` (dev-token mode)                  | `https://staging-idp.lumenai.health/.well-known/jwks.json` | `https://idp.lumenai.health/.well-known/jwks.json` |
| `API_BASE_URL`        | `http://localhost:8000`              | `http://localhost:8000`              | `https://api.staging.lumenai.health`        | `https://api.lumenai.health`                |
| `STORAGE_BUCKET`      | `` (local filesystem)                | `lumenai-dev-bucket`                 | `lumenai-staging-bucket`                    | `lumenai-prod-audit-evidence`               |
| `APP_ENV`             | `development`                        | `development`                        | `staging`                                   | `production`                                |
| `VITE_API_BASE_URL`   | `http://localhost:8000`              | `http://localhost:8000`              | `https://api.staging.lumenai.health`        | `https://api.lumenai.health`                |

---

## Environment Definitions

### 1. Local (Developer Workstation)

**Purpose**: Day-to-day development, rapid iteration, offline-capable.

**Auth mode**: Dev-token (`X-LumenAI-Role: admin` header accepted, no JWT validation)

**Database**: SQLite — file created automatically at first run

**Object storage**: Local filesystem or mocked (no real S3 calls)

**How to run**:
```bash
# Backend
cd backend
DATABASE_URL=sqlite:///./lumenai.db uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend
VITE_API_BASE_URL=http://localhost:8000 npm run dev
```

**`.env` (local, never committed)**:
```env
ENVIRONMENT=local
DATABASE_URL=sqlite:///./lumenai.db
SECRET_KEY=dev-secret-change-in-production
LOG_LEVEL=DEBUG
CORS_ORIGINS=http://localhost:5173
APP_ENV=development
STRIPE_SECRET_KEY=
FDA_API_KEY=
```

---

### 2. Development (Shared Dev Cluster / Docker Compose)

**Purpose**: Integration testing, shared feature branches, QA review of PRs.

**Auth mode**: Dev-token (JWKS_URL empty → falls back to dev-token validation)

**Database**: SQLite (Docker Compose default) or PostgreSQL dev instance

**Object storage**: S3 dev bucket or LocalStack

**How to run**:
```bash
docker compose up --build
```

**`docker-compose.yml` environment**:
```env
ENVIRONMENT=development
DATABASE_URL=sqlite:///./lumenai.db
SECRET_KEY=dev-secret-change-in-production
LOG_LEVEL=DEBUG
CORS_ORIGINS=http://localhost:5173
APP_ENV=development
```

**CI test configuration**:
```bash
DATABASE_URL=sqlite:///./lumenai.db python -m pytest tests/ -q
```

---

### 3. Staging

**Purpose**: Pre-production validation, smoke tests, performance testing, stakeholder demos.

**Auth mode**: Real OIDC/JWKS (staging IdP — Okta or Auth0 staging tenant)

**Database**: Managed PostgreSQL (RDS `db.t3.medium` or equivalent), separate schema from production

**Object storage**: S3 staging bucket (not immutable, shorter retention)

**Logging**: Structured JSON → CloudWatch / Datadog (INFO level)

**OIDC config**:
```
JWKS_URL=https://staging-idp.lumenai.health/.well-known/jwks.json
OIDC_ISSUER=https://staging-idp.lumenai.health
OIDC_AUDIENCE=lumenai-staging-api
```

**Kubernetes namespace**: `lumenai-staging`

**Deployment**: Auto-deployed from `main` branch via GitHub Actions after tests pass

**Secrets**: AWS Secrets Manager (staging prefix: `/lumenai/staging/`)

**Environment variables (injected from Secrets Manager via External Secrets Operator)**:
```
ENVIRONMENT=staging
APP_ENV=staging
DATABASE_URL=<from secrets manager>
SECRET_KEY=<from secrets manager>
STRIPE_SECRET_KEY=sk_test_<from secrets manager>
FDA_API_KEY=<from secrets manager>
CORS_ORIGINS=https://staging.lumenai.health
LOG_LEVEL=INFO
JWKS_URL=https://staging-idp.lumenai.health/.well-known/jwks.json
API_BASE_URL=https://api.staging.lumenai.health
STORAGE_BUCKET=lumenai-staging-bucket
```

---

### 4. Production

**Purpose**: Live hospital and health system customers. HIPAA-compliant, zero-tolerance for data leakage.

**Auth mode**: Real OIDC/JWKS — dev-token **disabled** (`JWKS_URL` must be set; any request without valid JWT is rejected)

**Database**: Managed PostgreSQL Multi-AZ (RDS `db.r6g.large` or equivalent)
- Encryption at rest: KMS
- Backups: automated 7-day + weekly pg_dump to immutable S3
- Read replica: optional for analytics queries

**Object storage**: S3 immutable audit bucket with Object Lock (7-year retention)

**Logging**: Structured JSON → CloudWatch / Datadog (WARNING level for application, INFO for audit events)

**TLS**: ACM certificate, HTTPS enforced, HSTS header (max-age=63072000)

**Security headers**: Full set (X-Frame-Options, CSP, nosniff, Referrer-Policy, HSTS)

**Rate limiting**: NGINX Ingress `nginx.ingress.kubernetes.io/limit-rps: "100"` + burst

**CORS**: Restricted to specific hospital domains — no wildcards

**Secrets**: AWS Secrets Manager (`/lumenai/production/`) — rotated quarterly via Lambda rotation function

**Kubernetes namespace**: `lumenai`

**Deployment**: Manual approval gate in GitHub Actions (`environment: production`)

**Environment variables (all from Secrets Manager)**:
```
ENVIRONMENT=production
APP_ENV=production
DATABASE_URL=<from secrets manager>
SECRET_KEY=<from secrets manager — rotated quarterly>
STRIPE_SECRET_KEY=sk_live_<from secrets manager>
FDA_API_KEY=<from secrets manager>
CORS_ORIGINS=https://app.lumenai.health,https://portal.generalhospital.com
LOG_LEVEL=WARNING
JWKS_URL=https://idp.lumenai.health/.well-known/jwks.json
OIDC_ISSUER=https://idp.lumenai.health
OIDC_AUDIENCE=lumenai-api
API_BASE_URL=https://api.lumenai.health
STORAGE_BUCKET=lumenai-prod-audit-evidence
```

---

## Environment Promotion Flow

```
local → development (PR) → staging (auto, main branch) → production (manual approval)
```

- **local → development**: Developer pushes PR; CI runs tests
- **development → staging**: Merge to `main` triggers auto-deploy to staging
- **staging → production**: After smoke tests pass, engineer triggers `workflow_dispatch` with `environment: production`; GitHub environment protection rule requires manual approval from production approvers

---

## Secret Rotation Schedule

| Secret              | Rotation Frequency | Method                              |
|---------------------|-------------------|-------------------------------------|
| SECRET_KEY          | Quarterly         | AWS Secrets Manager Lambda rotation |
| Database password   | Quarterly         | RDS Secrets Manager integration     |
| STRIPE_SECRET_KEY   | Per Stripe policy | Manual + Secrets Manager update     |
| FDA_API_KEY         | Annually          | Manual + Secrets Manager update     |
| OIDC client secret  | Annually          | IdP rotation + Secrets Manager      |

---

## Configuration Files (Never Commit Real Values)

```
.env.example          ← template with placeholder values (committed)
.env.local            ← developer overrides (gitignored)
.env.test             ← test-specific (DATABASE_URL=sqlite://:memory:)
```

`.env.example`:
```env
ENVIRONMENT=local
DATABASE_URL=sqlite:///./lumenai.db
SECRET_KEY=CHANGE_ME_IN_PRODUCTION
STRIPE_SECRET_KEY=
FDA_API_KEY=
CORS_ORIGINS=http://localhost:5173
LOG_LEVEL=DEBUG
APP_ENV=development
JWKS_URL=
API_BASE_URL=http://localhost:8000
STORAGE_BUCKET=
VITE_API_BASE_URL=http://localhost:8000
```
