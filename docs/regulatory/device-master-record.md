# Device Master Record (DMR)
**LumenAI SPD Intelligence Platform**
**Document Number**: DMR-LUM-001 | **Version**: 1.0-RC | **Status**: In Review
**Subject to regulatory counsel review before submission.**

---

## 1. Product Identification

| Field | Value |
|-------|-------|
| Product Name | LumenAI SPD Intelligence Platform |
| Product Code | LUM-SaaS-001 |
| Software Version | 1.0-RC |
| Software Type | Software as a Medical Device (SaMD) — pending classification |
| Intended Use | AI-assisted visual inspection documentation for sterile processing |
| Primary Markets | United States (target), Canada, EU (future) |
| Regulatory Status | Pre-submission — not cleared, not approved |
| Classification (Proposed) | Class II (pending Q-Sub confirmation) |
| Applicable Standards | IEC 62304, ISO 14971:2019, ISO 13485:2016, 21 CFR Part 820, AAMI TIR57 |

---

## 2. Software Architecture Summary

LumenAI is a multi-tenant cloud-hosted SaaS application with the following primary components:

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Backend API | FastAPI (Python 3.11+) | REST API, business logic, AI orchestration |
| Frontend | React + Vite + TypeScript | Web application, PWA |
| Database (Production) | PostgreSQL 14+ | Primary data store, multi-tenant |
| Database (Development) | SQLite | Local development only |
| ORM | SQLAlchemy 2.x | Database abstraction, query building |
| Background Jobs | APScheduler | Scheduled tasks (sync, monitoring, alerts) |
| CV Inference Engine | Custom Python module | Computer vision model inference |
| Offline Storage | Browser IndexedDB | PWA offline session storage |
| Authentication | JWT + enterprise_auth module | User authentication and authorization |
| Rate Limiting | slowapi | API rate limiting (DoS protection) |
| Static/Proxy | Nginx | Frontend serving, TLS termination, reverse proxy |

**Module Inventory**:
- Module A: Computer Vision Detection (SaMD candidate)
- Module B: AI Inspection Ranking Engine
- Module C: Baseline Intelligence
- Module D: Barcode/UDI/QR/KeyDot Identification
- Module E: Vendor Intelligence Exchange
- Module F: Enterprise Benchmarking Network
- Module G: Predictive Failure Analytics
- Module H: Patient Safety Intelligence
- Module I: Mobile/Offline Platform
- Module J: Security & Audit Infrastructure

---

## 3. Deployment Architecture

| Component | Implementation | Location |
|-----------|---------------|---------|
| Container Runtime | Docker | backend/Dockerfile, frontend/Dockerfile |
| Orchestration | Kubernetes | k8s/ manifest directory |
| Reverse Proxy | Nginx | frontend/nginx.conf |
| TLS Termination | Nginx + Certificate Manager | Required in production |
| Cloud Platform | AWS (primary target) | Managed Kubernetes (EKS) |
| Container Registry | ECR or equivalent | Docker image storage |
| Database Hosting | AWS RDS PostgreSQL | Managed database service |
| Secret Management | AWS Secrets Manager / env vars | Non-hardcoded secrets |
| Monitoring | CloudWatch / Prometheus | /metrics endpoint |

**Deployment Modes**:
1. **Cloud SaaS** (primary): Kubernetes deployment, managed by LumenAI
2. **Self-Hosted** (enterprise option): Docker Compose deployment on customer infrastructure
3. **Mobile PWA**: Browser-based, connected to cloud backend, with offline capability

---

## 4. Configuration Management

| Area | Approach |
|------|----------|
| Secrets | Environment variables; never hardcoded; .env files excluded from version control |
| Database Schema | Alembic migrations (backend/alembic/versions/) — versioned, sequential |
| Docker Images | Tagged by semantic version (e.g., lumenai-backend:1.0.0) |
| CI/CD | GitHub Actions (.github/workflows/); automated build, test, lint, security scan |
| Feature Flags | Environment variables (e.g., RATELIMIT_ENABLED, ENTERPRISE_FEATURES) |
| Frontend Config | Vite build-time environment variables; runtime config via API |

**Critical Environment Variables**:

| Variable | Purpose | Production Requirement |
|----------|---------|----------------------|
| DATABASE_URL | Database connection string | PostgreSQL URL required |
| JWT_SECRET_KEY | JWT signing key | Minimum 32-character random string |
| RATELIMIT_ENABLED | Enable API rate limiting | Must be "1" |
| ENTERPRISE_AUTH_ENABLED | Enable enterprise authentication | Recommended "1" |
| DEV_TOKEN | Development bypass token | Must NOT be set in production |
| CORS_ORIGINS | Allowed CORS origins | Restrict to known domains |

---

## 5. Versioning Strategy

LumenAI uses semantic versioning (SemVer 2.0.0): **MAJOR.MINOR.PATCH**

| Version Component | Trigger | Change Control |
|------------------|---------|----------------|
| MAJOR | Breaking API changes, major architecture changes | Full design review required |
| MINOR | New features, new modules, non-breaking API additions | Standard PR review + QA |
| PATCH | Bug fixes, security patches, documentation updates | Expedited PR review |

**AI Model Versioning**:
- CV model versions tracked separately: MODEL-A-{MAJOR}.{MINOR}
- Model changes subject to AI/ML Change Control Plan (docs/regulatory/ai-ml-change-control-plan.md)
- Significant algorithm changes require re-validation per Predetermined Change Control Plan

**Branch Strategy**:
- `main` — production-ready code
- `release/x.y.z` — release candidate branches
- `claude/` prefix — feature development branches
- Tags: `v{MAJOR}.{MINOR}.{PATCH}` on release commits

---

## 6. Release Process

The LumenAI release pipeline follows these gates:

```
Code PR → Automated Tests (pytest) → Lint (ruff) → Build → Security Scan →
Staging Deployment → Smoke Tests → Manual Approval Gate → Production Deployment
```

| Stage | Tool/Method | Requirement |
|-------|------------|-------------|
| Unit/Integration Tests | pytest | All tests must pass |
| Static Analysis | ruff | No errors (warnings reviewed) |
| Docker Build | docker build | Must succeed |
| Security Scan | pip-audit (target) | No critical CVEs |
| Staging Deployment | Kubernetes rolling update | Smoke tests must pass |
| Smoke Tests | Automated API tests | /health, auth, inspection endpoints |
| Manual Approval | Designated approver | Required for production promotion |
| Production Deployment | Kubernetes rolling update | Zero-downtime deployment |
| Post-Deploy Verification | /health + monitoring | 15-minute burn-in monitoring |

**Rollback Procedure**: Previous Docker image tag re-deployed via Kubernetes rollout undo. Database migrations are forward-only; rollback requires coordination with DBA.

---

## 7. Installation Requirements

### 7.1 Server/Infrastructure Requirements (Cloud Deployment)

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| CPU | 4 vCPU | 8 vCPU |
| RAM | 8 GB | 16 GB |
| Storage | 100 GB SSD | 500 GB SSD |
| Database | PostgreSQL 14+ | PostgreSQL 15+ |
| Python | 3.11+ | 3.12+ |
| Node.js | 20+ (build only) | 20+ |
| Container Runtime | Docker 24+ | Docker 25+ |
| Orchestration | Kubernetes 1.28+ | Kubernetes 1.29+ |

### 7.2 Network Requirements

| Requirement | Specification |
|-------------|--------------|
| Protocol | HTTPS (TLS 1.2+) required |
| Port (HTTPS) | 443 |
| Port (HTTP) | 80 (redirect to 443 only) |
| Minimum bandwidth (image upload) | 10 Mbps per concurrent user |
| Latency target | < 200ms API response (p95) |
| DNS | FQDN required for TLS certificate |

---

## 8. Operating Environment

### 8.1 Supported Client Environments

| Browser | Minimum Version | Notes |
|---------|----------------|-------|
| Google Chrome | 120+ | Primary supported browser |
| Safari | 17+ | iOS and macOS |
| Firefox | 121+ | Secondary support |
| Edge | 120+ | Chromium-based |

**Requirements**: JavaScript enabled, cookies enabled, IndexedDB available (for offline mode), camera permission (for mobile image capture).

**Not supported**: Internet Explorer (any version), Chrome < 100, Safari < 15.

### 8.2 Mobile Requirements

- Modern smartphone or tablet (iOS 16+ / Android 12+)
- Minimum 8MP rear camera for adequate image quality
- HTTPS connectivity for sync operations
- ServiceWorker support in browser

---

## 9. Labeling

Device labeling is maintained in: `docs/regulatory/user-labeling-and-instructions.md`

Labeling includes:
- Instructions for Use (IFU)
- System indications, contraindications, and warnings
- Human review requirements and disclaimers
- Software version and identification
- Manufacturer information
- Intended user population
- Electronic labeling (in-app help, tooltips, warnings)

**Required label elements per 21 CFR 801**:
- Name and place of business of manufacturer
- Adequate directions for use
- Intended use statement
- Warnings and precautions

---

## 10. Change History

| Version | Date | Description | Change Control Reference |
|---------|------|-------------|------------------------|
| 0.1 | 2024-01 | Initial architecture (P0) | git log |
| 0.2 | 2024-03 | CV inspection module (P4) | git log |
| 0.5 | 2024-06 | Clinical validation framework (P12) | git log |
| 0.8 | 2024-09 | Regulatory automation (P13) | git log |
| 0.9 | 2025-01 | Mobile/offline platform (P17) | git log |
| 0.9.5 | 2025-06 | Patient safety intelligence (P16) | git log |
| 1.0-RC | 2026-06-21 | Regulatory submission package (P19) | This DMR |

For complete change history: `git log --oneline` in repository root.
For AI model changes: docs/regulatory/ai-ml-change-control-plan.md
For planned changes: docs/regulatory/predetermined-change-control-plan.md

---

*Document Owner: Software Engineering Lead + Regulatory Affairs Lead*
*Review Cycle: Per release | Next Review: v1.1.0 release*
*This document does not constitute regulatory clearance or approval.*
