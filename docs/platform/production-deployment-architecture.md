# LumenAI Production Deployment Architecture

## Overview

LumenAI is deployed as a multi-tier SaaS platform designed for hospital and health system enterprise deployments. This document defines the reference production architecture.

---

## Architecture Diagram

```
                          ┌─────────────────────────────────────────────────┐
                          │                 INTERNET / CLIENTS               │
                          └────────────────────┬────────────────────────────┘
                                               │ HTTPS (443)
                          ┌────────────────────▼────────────────────────────┐
                          │         CDN / Load Balancer                      │
                          │  CloudFront / Cloudflare / AWS ALB               │
                          │  - TLS termination (ACM or cert-manager)         │
                          │  - WAF rules (OWASP top 10)                      │
                          │  - DDoS protection                               │
                          └────────┬──────────────────────┬──────────────────┘
                                   │                      │
              ┌────────────────────▼──┐         ┌─────────▼────────────────┐
              │   Frontend (Nginx)    │         │    Backend API (FastAPI)  │
              │   Static React SPA    │         │    K8s Deployment         │
              │   - Security headers  │         │    - 2–10 replicas (HPA)  │
              │   - SPA routing       │         │    - Non-root user        │
              │   - Health endpoint   │         │    - Resource limits      │
              └───────────────────────┘         └──────┬───────────────────┘
                                                       │
                    ┌──────────────────────────────────┤
                    │                                  │
        ┌───────────▼────────────┐      ┌─────────────▼──────────────┐
        │  PostgreSQL            │      │  Object Storage (S3)        │
        │  RDS / Cloud SQL /     │      │  - Audit evidence (immut.)  │
        │  Azure Database        │      │  - PDF exports              │
        │  - Multi-AZ            │      │  - Model artifacts          │
        │  - Automated backups   │      │  - Object Lock enabled      │
        │  - Encryption at rest  │      └────────────────────────────┘
        └────────────────────────┘
                    │
        ┌───────────▼────────────┐      ┌────────────────────────────┐
        │  Redis (optional)      │      │  Model Inference Service    │
        │  - Celery broker       │      │  - CPU-first deployment     │
        │  - Session caching     │      │  - GPU sidecar (optional)   │
        │  - Rate limiting       │      │  - Separate K8s Deployment  │
        └────────────────────────┘      └────────────────────────────┘
```

---

## Component Details

### 1. Frontend: Static SPA → CDN / Nginx Container

- **Build**: `npm run build` produces static assets in `frontend/dist/`
- **Serving options**:
  - **CDN**: Upload `dist/` to S3, serve via CloudFront with custom domain + ACM TLS certificate
  - **Nginx container**: Multi-stage Dockerfile builds React app, copies to Nginx Alpine image
- **Security headers**: X-Frame-Options, X-Content-Type-Options, CSP, Referrer-Policy (see `frontend/nginx.conf`)
- **SPA routing**: All unknown paths serve `index.html` (React Router handles client-side routing)
- **Cache strategy**: Hash-named assets cached 1 year; `index.html` no-cache

### 2. Backend API: FastAPI on Kubernetes

- **Runtime**: Python 3.11 + Uvicorn with 2–4 workers per pod
- **Orchestration**: Kubernetes (EKS / GKE / AKS / self-hosted K3s)
- **Replicas**: Minimum 2 pods (HPA scales to 10 on CPU > 70%)
- **Security**: Non-root user (`appuser`), read-only root filesystem, no privileged escalation
- **Health**: `/health` (liveness), `/ready` (readiness — DB connectivity check)
- **API prefix**: `/api/` (configured via `settings.API_PREFIX`)
- **Worker scaling**: APScheduler within API pod for lightweight background tasks; migrate to Celery + Redis for high-throughput scheduling

### 3. Database: PostgreSQL (Managed)

| Environment | Database          | Notes                                    |
|-------------|-------------------|------------------------------------------|
| local       | SQLite            | File-based, zero config                  |
| development | SQLite or PG      | Docker Compose PostgreSQL service        |
| staging     | PostgreSQL (managed) | RDS / Cloud SQL dev tier              |
| production  | PostgreSQL (managed) | Multi-AZ, encryption, automated backups |

**Production configuration**:
- Engine: PostgreSQL 15+
- Managed service: AWS RDS, Google Cloud SQL, or Azure Database for PostgreSQL
- Multi-AZ: enabled (automatic failover)
- Encryption at rest: enabled (KMS)
- Automated backups: 7-day retention (configurable)
- Point-in-time recovery: enabled
- Connection: via `DATABASE_URL` environment variable (never hardcoded)
- Pooling: SQLAlchemy `pool_size=10`, `max_overflow=20`, `pool_pre_ping=True`
- Migrations: Alembic (`alembic upgrade head` in deployment pipeline)

**SQLite**: Used only for local development and CI testing. Never in production.

### 4. Object Storage: S3-Compatible

| Bucket Purpose         | Configuration                                          |
|------------------------|--------------------------------------------------------|
| Audit evidence         | Immutable (S3 Object Lock, Governance mode, 7-year retention) |
| PDF exports            | Standard, lifecycle policy 90 days                    |
| Model artifacts        | Versioned, KMS encrypted                              |
| Static frontend assets | Public read via CloudFront OAI                        |

- **Access**: Backend accesses via IAM role (IRSA on EKS / Workload Identity on GKE) — no hardcoded credentials
- **Encryption**: SSE-S3 or SSE-KMS
- **Versioning**: Enabled on audit and model artifact buckets

### 5. Background Jobs

**APScheduler (default)**:
- Runs within API pod process
- Suitable for single-pod or low-frequency scheduling (predictions, digest delivery)
- No external dependencies

**Celery + Redis (scale-out)**:
- Add when job queue exceeds API pod capacity
- Redis as broker and result backend
- Separate Celery worker Deployment in Kubernetes
- Redis: managed ElastiCache / Cloud Memorystore

### 6. Model Inference

- **CPU-first**: All inference runs on CPU by default (scikit-learn, lightweight models)
- **GPU sidecar**: Attach GPU node pool and schedule inference pods with `nvidia.com/gpu: 1` resource request
- **Separate inference service**: For LLM or heavy CV workloads, deploy a separate `inference` Deployment with its own HPA and GPU node affinity
- **Model artifacts**: Loaded from S3 at pod startup or baked into image for immutability

### 7. Audit / Evidence Storage (HIPAA)

- Dedicated S3 bucket with **S3 Object Lock** in Governance mode
- Minimum retention: **7 years** (HIPAA requirement)
- Access logging enabled on bucket
- CloudTrail logs all S3 API calls
- Bucket policy denies `s3:DeleteObject` to all principals except compliance admin role

### 8. Secrets Management

**Option A: Kubernetes Secrets + External Secrets Operator**
```
AWS Secrets Manager / HashiCorp Vault
         ↓  (External Secrets Operator sync)
Kubernetes Secret (namespace: lumenai)
         ↓  (mounted as env vars)
Pod containers
```

**Option B: AWS Secrets Manager (direct)**
- Use IAM role (IRSA) to fetch secrets at startup via `boto3`
- Or inject via AWS Secrets Manager CSI driver

**Option C: HashiCorp Vault**
- Vault Agent sidecar injects secrets as files or env vars
- Dynamic database credentials via Vault database secrets engine

**Never**: store real secrets in ConfigMaps, environment variable literals in manifests, or source control.

---

## Network Architecture

```
Internet → CloudFront/ALB (public)
         → Nginx pods (port 80, internal)
         → FastAPI pods (port 8000, internal only)
         → PostgreSQL (port 5432, private subnet only)
         → Redis (port 6379, private subnet only)
```

- All inter-service communication within private Kubernetes network
- NetworkPolicy restricts pod-to-pod traffic (see `k8s/network-policy.yaml`)
- Database and Redis accessible only from API pod namespace/labels

---

## Deployment Topology (Production)

```
Region: us-east-1 (or customer-selected)
  VPC
  ├── Public Subnets (AZ-a, AZ-b)
  │   ├── ALB / NAT Gateway
  │   └── CloudFront Origin
  ├── Private Subnets (AZ-a, AZ-b)
  │   ├── EKS Node Group (API + Frontend pods)
  │   └── Redis ElastiCache
  └── Database Subnets (AZ-a, AZ-b)
      └── RDS PostgreSQL Multi-AZ
```

---

## Technology Stack Summary

| Layer            | Technology                          |
|------------------|-------------------------------------|
| Frontend         | React 18, TypeScript, Vite, Nginx   |
| Backend API      | Python 3.11, FastAPI, Uvicorn       |
| Database         | PostgreSQL 15 (prod), SQLite (dev)  |
| ORM / Migrations | SQLAlchemy 2.x, Alembic             |
| Container        | Docker (multi-stage builds)         |
| Orchestration    | Kubernetes (EKS/GKE/AKS)           |
| CI/CD            | GitHub Actions                      |
| Secrets          | Kubernetes Secrets + Ext. Secrets   |
| Monitoring       | Prometheus + Grafana / CloudWatch   |
| Tracing          | OpenTelemetry (future)              |
| Storage          | AWS S3 (audit immutable bucket)     |
| Auth             | OIDC/JWKS (production), dev-token   |
