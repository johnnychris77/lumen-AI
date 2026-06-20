# LumenAI Security Operations

## Overview

Security operations guide for LumenAI in production hospital deployments. Covers secret management, OIDC configuration, dependency scanning, and HIPAA compliance controls.

---

## 1. Production Secret Rotation Procedure

### Rotation Schedule

| Secret              | Frequency   | Who                     |
|---------------------|-------------|-------------------------|
| `SECRET_KEY`        | Quarterly   | Platform team           |
| Database password   | Quarterly   | DBA + Platform team     |
| `STRIPE_SECRET_KEY` | Per policy  | Finance + Platform team |
| `FDA_API_KEY`       | Annually    | Platform team           |
| OIDC client secret  | Annually    | IdP admin               |
| TLS certificates    | Annually*   | cert-manager (auto)     |

*cert-manager renews Let's Encrypt certs automatically at 60 days.

### Rotation Procedure (SECRET_KEY)
```bash
# 1. Generate new secret key
NEW_SECRET=$(python3 -c "import secrets; print(secrets.token_hex(64))")

# 2. Store in AWS Secrets Manager
aws secretsmanager put-secret-value \
  --secret-id /lumenai/production/SECRET_KEY \
  --secret-string "$NEW_SECRET"

# 3. Trigger External Secrets Operator sync
kubectl annotate externalsecret lumenai-secrets \
  force-sync="$(date +%s)" -n lumenai

# 4. Rolling restart of backend pods (picks up new secret)
kubectl rollout restart deployment/lumenai-backend -n lumenai

# 5. Verify pods are healthy
kubectl rollout status deployment/lumenai-backend -n lumenai

# 6. Revoke old secret (after confirming new secret works)
# (AWS Secrets Manager versioning keeps old value for rollback)
```

---

## 2. OIDC / JWKS Configuration Guide

### Architecture
LumenAI validates JWT tokens using JWKS (JSON Web Key Sets) from your Identity Provider (IdP).

**Supported IdPs**: Okta, Auth0, Azure AD B2C, Keycloak, AWS Cognito

### Environment Variables Required
```env
JWKS_URL=https://your-idp.example.com/.well-known/jwks.json
OIDC_ISSUER=https://your-idp.example.com
OIDC_AUDIENCE=lumenai-api
```

### Okta Setup
1. Create Okta Application (API Services type)
2. Add allowed scopes: `openid`, `profile`, `email`
3. Set `JWKS_URL` to `https://<okta-domain>/oauth2/default/v1/keys`
4. Set `OIDC_ISSUER` to `https://<okta-domain>/oauth2/default`

### Auth0 Setup
1. Create Auth0 API (name: LumenAI, identifier: `https://api.lumenai.health`)
2. Set `JWKS_URL` to `https://<auth0-domain>/.well-known/jwks.json`
3. Set `OIDC_ISSUER` to `https://<auth0-domain>/`

### Azure AD Setup
1. Register app in Azure AD
2. Set `JWKS_URL` to `https://login.microsoftonline.com/<tenant-id>/discovery/keys`
3. Set `OIDC_ISSUER` to `https://login.microsoftonline.com/<tenant-id>/v2.0`

### Dev-Token Mode (disable in production)
When `JWKS_URL` is empty, the API accepts `X-LumenAI-Role` header for dev convenience.
**This MUST be disabled in production** — ensure `JWKS_URL` is set.

Verify dev-token is disabled:
```bash
curl -i https://api.lumenai.health/api/inspections
# Must return 401 Unauthorized (not 200)
```

---

## 3. JWT Key Rotation Steps

1. IdP generates new signing key pair
2. IdP publishes new public key at JWKS endpoint (old key kept for token validity window)
3. New tokens issued with new key ID (`kid` claim)
4. Wait for old tokens to expire (typically 1 hour)
5. IdP removes old key from JWKS endpoint
6. LumenAI backend auto-fetches updated JWKS (no restart needed if JWKS cache TTL ≤ 1h)

**Ensure JWKS caching TTL in backend ≤ 1 hour** to pick up key rotation promptly.

---

## 4. Dependency Scanning

### Backend (Python) — pip-audit
```bash
pip install pip-audit
pip-audit -r backend/requirements.txt

# In CI (fail on high severity only)
pip-audit -r backend/requirements.txt --severity high

# With known exceptions documented
pip-audit -r backend/requirements.txt --ignore-vuln PYSEC-2022-42969
```

**Frequency**: On every PR + weekly scheduled scan

### Frontend (Node.js) — npm audit
```bash
cd frontend
npm audit --audit-level=high

# Fix automatically (test after)
npm audit fix
```

### Scanning Schedule
- Per PR: `pip-audit` + `npm audit` (warnings only, don't block)
- Weekly: Full scan, file issues for critical/high findings
- Before release: Enforce clean scan or documented exceptions

---

## 5. Image Scanning — Trivy

```bash
# Install trivy
brew install trivy  # or apt/rpm

# Scan backend image
trivy image lumenai/backend:latest

# Scan with exit code for CI
trivy image --exit-code 1 --severity CRITICAL lumenai/backend:latest

# Scan frontend image
trivy image --exit-code 1 --severity CRITICAL lumenai/frontend:latest

# Scan filesystem (in CI before build)
trivy fs --severity HIGH,CRITICAL backend/
```

**CI Integration** (add to GitHub Actions):
```yaml
- name: Trivy image scan
  uses: aquasecurity/trivy-action@master
  with:
    image-ref: 'lumenai/backend:${{ github.sha }}'
    format: 'sarif'
    output: 'trivy-results.sarif'
    severity: 'CRITICAL,HIGH'
```

---

## 6. Secret Scanning — Gitleaks

```bash
# Install gitleaks
brew install gitleaks

# Scan current repo
gitleaks detect --source . --verbose

# Scan staged changes (pre-commit hook)
gitleaks protect --staged

# In CI
gitleaks detect --source . --exit-code 1
```

**Pre-commit hook** (install via `.pre-commit-config.yaml`):
```yaml
repos:
  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.18.0
    hooks:
      - id: gitleaks
```

**CI**: See `.github/workflows/deploy.yml` — gitleaks runs on every push.

---

## 7. Security Headers

Security headers are set in two places:
1. **Backend** (`app/main.py` `SecurityHeadersMiddleware`): X-Content-Type-Options, X-Frame-Options, Referrer-Policy, Permissions-Policy, HSTS (production only)
2. **Frontend** (`frontend/nginx.conf`): X-Frame-Options, X-Content-Type-Options, X-XSS-Protection, Referrer-Policy, Content-Security-Policy

**Verify headers in production**:
```bash
curl -I https://api.lumenai.health/health | grep -i "x-\|strict\|referrer\|content-security"
```

---

## 8. CORS Production Policy

In production, restrict `CORS_ORIGINS` to known hospital domains:
```env
CORS_ORIGINS=https://app.lumenai.health,https://portal.generalhospital.com,https://quality.citymedical.org
```

**Never use `*` in production CORS origins.**

To add a new hospital domain:
1. Verify domain ownership with the hospital IT team
2. Update `CORS_ORIGINS` in AWS Secrets Manager
3. Restart backend pods (or update ConfigMap + rolling restart)

---

## 9. Rate Limiting Strategy

### NGINX Ingress (Kubernetes)
```yaml
# In ingress.yaml annotations:
nginx.ingress.kubernetes.io/limit-rps: "100"
nginx.ingress.kubernetes.io/limit-burst-multiplier: "5"
nginx.ingress.kubernetes.io/limit-connections: "10"
```

### Per-Route Limits (API Gateway)
| Endpoint                    | Rate Limit     | Burst  |
|-----------------------------|---------------|--------|
| `POST /api/cv/analyze`      | 10 RPS/tenant | 20     |
| `POST /api/baseline/upload` | 5 RPS/tenant  | 10     |
| `GET /api/*`                | 100 RPS/IP    | 200    |
| `POST /api/auth/*`          | 10 RPS/IP     | 5      |

### Application-Level Rate Limiting
For future implementation, add `slowapi` or `fastapi-limiter`:
```python
from slowapi import Limiter
from slowapi.util import get_remote_address
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
```

---

## 10. HIPAA Audit Log Retention

- **Minimum retention**: 7 years (HIPAA § 164.530(j))
- **Implementation**: Audit log entries written to PostgreSQL `audit_logs` table + daily export to immutable S3 bucket
- **S3 bucket policy**: Object Lock (Governance mode), 7-year minimum retention rule
- **Access**: Audit logs are append-only; read access restricted to compliance officer role
- **Encryption**: AES-256 at rest (SSE-KMS), TLS in transit

### Audit Log Contents (minimum required by HIPAA)
- Who (user ID, tenant, role)
- What (action, resource, before/after values for PHI modifications)
- When (timestamp with timezone)
- Where (IP address, user agent)
- Result (success / failure)

### Compliance Evidence
Audit log exports are available via:
- `GET /api/compliance/exports` — downloadable CSV/JSON
- `POST /api/regulatory/audit-package` — full audit package ZIP
