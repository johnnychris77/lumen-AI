# Cybersecurity Threat Model
LumenAI | FDA 2023 Cybersecurity Guidance Compliance | STRIDE Framework

## 1. System Boundary
- Backend API (FastAPI, Kubernetes pods)
- Frontend SPA (React, Nginx, CDN)
- Database (PostgreSQL, encrypted at rest)
- S3 audit evidence storage (encrypted, immutable)
- External integrations: Stripe, FDA MedWatch API

## 2. STRIDE Threat Analysis

### Spoofing
| Threat | Control | Residual Risk |
|--------|---------|---------------|
| Attacker impersonates hospital tenant | JWT + OIDC validation; `require_enterprise_auth` | Low |
| Attacker impersonates manufacturer | `require_manufacturer_auth` + `X-Manufacturer-ID` header | Low |
| Dev-token used in production | `ENVIRONMENT=production` blocks non-JWT tokens (P11 fix) | Low |

### Tampering
| Threat | Control | Residual Risk |
|--------|---------|---------------|
| Audit log modification | DB-level immutability guard; no UPDATE on audit rows | Low |
| Model artifact tampering | SHA-256 manifest + S3 object lock | Low |
| API request body injection | Pydantic validation + `_sanitize()` on all text fields | Low |

### Repudiation
| Threat | Control | Residual Risk |
|--------|---------|---------------|
| Technician denies override action | Immutable override record with `recorded_by` field | Low |
| Billing dispute | Stripe webhook logs + `PaymentEvent` table | Low |

### Information Disclosure
| Threat | Control | Residual Risk |
|--------|---------|---------------|
| Cross-tenant data leak | `tenant_id` filter on all queries; tested in P0/P1 | Low |
| PHI in logs | No PHI fields in schema; log sanitization | Low |
| `/metrics` endpoint exposure | Auth-gated in P11; IP-restricted at ingress | Low |

### Denial of Service
| Threat | Control | Residual Risk |
|--------|---------|---------------|
| CV inference endpoint flood | slowapi rate limiting (30/min); nginx rate_limit | Medium |
| Database connection exhaustion | SQLAlchemy pool_size=10, max_overflow=20, pool_pre_ping | Low |

### Elevation of Privilege
| Threat | Control | Residual Risk |
|--------|---------|---------------|
| Standard tier accesses enterprise features | `require_tier()` raises 402; enforced server-side | Low |
| Container runs as root | Non-root `appuser` in backend Dockerfile (P11) | Low |

## 3. SBOM
Software Bill of Materials generated via CycloneDX at build time (see `.github/workflows/deploy.yml`).
Current SBOM artifact: attached to each GitHub release.

## 4. Vulnerability Disclosure Policy
- Report vulnerabilities to: security@lumenai.com
- Response SLA: acknowledge within 24h, patch within 30 days for Critical/High
- CVE tracking: GitHub Security Advisories

## 5. Patch Management
- Dependency scanning: `pip-audit` + `npm audit` in CI (security-scan job)
- Image scanning: Trivy (documented in deploy.yml — implement before launch)
- OS patches: Kubernetes node pool managed updates (cloud provider)
- Python/Node base image: rebuild monthly or on CVE notification

## 6. Security Testing Evidence
- Static analysis: ruff (Python), ESLint (frontend)
- Secret scanning: gitleaks in CI
- Dependency audit: pip-audit + npm audit in CI
- Manual pen test: planned Q2 2026 (3rd-party vendor)
- OWASP Top 10 review: completed (P0/P1 security milestones)

## 7. Cybersecurity Labeling (FDA Required)
The following must appear in product labeling per FDA 2023 guidance:
- List of cybersecurity controls
- Instructions for secure network configuration
- Support timeline (security patches through [date])
- Contact for vulnerability disclosure
