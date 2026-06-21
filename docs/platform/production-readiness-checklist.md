# LumenAI Production Readiness Checklist

Complete this checklist before promoting any deployment to production. Each item must be checked or have a documented exception.

**Service**: LumenAI  
**Version**: P11  
**Deployment Date**: ____________  
**Engineer**: ____________  
**Approver**: ____________  

---

## Security

- [ ] TLS everywhere — all endpoints enforce HTTPS, no plain HTTP in production
- [ ] HSTS header configured (`Strict-Transport-Security: max-age=63072000; includeSubDomains; preload`)
- [ ] Security headers present: X-Frame-Options, X-Content-Type-Options, CSP, Referrer-Policy, Permissions-Policy
- [ ] No secrets in repo — confirmed by `gitleaks detect` returning 0 findings
- [ ] No secrets in Docker images — confirmed by `trivy image` scan
- [ ] `JWKS_URL` is set — dev-token mode disabled in production
- [ ] TLS certificate valid and auto-renewal configured (cert-manager or ACM)

## Authentication & Authorization

- [ ] OIDC/JWKS configured and tested with production IdP
- [ ] JWT validation requires valid `iss`, `aud`, and `exp` claims
- [ ] JWT key rotation plan documented and tested (see security-operations.md)
- [ ] Dev-token (`X-LumenAI-Role` header bypass) disabled — verified with unauthenticated request returning 401
- [ ] Role-based access control (RBAC) enforced on all sensitive endpoints

## Infrastructure

- [ ] Kubernetes manifests reviewed and applied to production namespace `lumenai`
- [ ] Resource requests and limits set on all containers
- [ ] HPA configured (min 2, max 10 replicas, CPU 70% threshold)
- [ ] Non-root user in backend container (`appuser`)
- [ ] NetworkPolicy restricts pod-to-pod traffic
- [ ] Node pool has sufficient capacity for peak load + HPA headroom
- [ ] PodDisruptionBudget configured (min 1 pod available during node maintenance)

## Database

- [ ] PostgreSQL in production — **NOT SQLite** — confirmed by `DATABASE_URL` starting with `postgresql://`
- [ ] Alembic migrations run successfully (`alembic upgrade head`)
- [ ] Migration tested in staging and rolled back/forward without data loss
- [ ] Database connection pooling configured (pool_size=10, max_overflow=20, pool_pre_ping=True)
- [ ] Multi-AZ / high availability enabled
- [ ] Backups automated (daily pg_dump + RDS automated backups)
- [ ] Point-in-time recovery tested
- [ ] Database password stored in Secrets Manager (not in repo or ConfigMap)

## Monitoring & Observability

- [ ] `/health` endpoint returns 200 in production
- [ ] `/ready` endpoint returns 200 (DB connectivity confirmed)
- [ ] Structured JSON logs shipping to CloudWatch / Datadog / ELK
- [ ] Prometheus metrics scraped (`/metrics` endpoint accessible from monitoring namespace)
- [ ] Grafana dashboards created (API latency, error rate, pod count)
- [ ] Correlation IDs (`X-Correlation-ID`) propagated in all responses
- [ ] Alerting rules configured for SEV1 conditions (pod down, DB unreachable, error rate > 0.1%)
- [ ] PagerDuty / on-call rotation configured for SEV1 alerts

## Backups

- [ ] Database backup automated and tested (restore verified in non-production)
- [ ] Audit evidence stored in immutable S3 bucket (Object Lock enabled)
- [ ] S3 bucket versioning enabled for model artifacts
- [ ] Retention policies set: audit logs ≥ 7 years, app logs 90 days
- [ ] Backup restore procedure documented and tested (see database-runbook.md)

## DNS & TLS

- [ ] DNS records configured (app.lumenai.health, api.lumenai.health)
- [ ] TLS certificate issued and valid (cert-manager or ACM)
- [ ] HTTPS redirect enforced at ingress level
- [ ] HSTS header confirmed in response
- [ ] CDN/CloudFront configured (if applicable)

## HIPAA Compliance

- [ ] HIPAA Business Associate Agreement (BAA) signed with cloud provider (AWS/GCP/Azure)
- [ ] Audit log retention ≥ 7 years configured and tested
- [ ] PHI encryption at rest (KMS or AES-256)
- [ ] PHI encryption in transit (TLS 1.2+)
- [ ] Access controls: only authorized roles can access PHI
- [ ] Audit logs capture: who, what, when, where, result for all PHI access
- [ ] BAA in place with any third-party processors (Stripe, FDA API, etc.)

## Performance

- [ ] Load test completed against staging (see load-testing-plan.md)
- [ ] API p99 < 500ms confirmed under load
- [ ] Inference p99 < 2s confirmed under load
- [ ] DB query plan analysis done — no unexpected sequential scans
- [ ] Critical indexes confirmed (tenant_id + created_at on key tables)
- [ ] Frontend LCP < 2.5s, FID < 100ms, CLS < 0.1 (Lighthouse score ≥ 90)

## Rollback

- [ ] Previous image tagged as `stable` (`lumenai/backend:stable`, `lumenai/frontend:stable`)
- [ ] Rollback procedure documented and tested on staging (see reliability.md)
- [ ] Alembic downgrade migration tested for this deployment's schema changes
- [ ] Rollback runbook reviewed by on-call engineer

## CI/CD

- [ ] GitHub Actions deploy pipeline tested end-to-end on staging
- [ ] Manual approval gate configured for `production` environment in GitHub repository settings
- [ ] Required approvers set for production deploys (≥ 2 approvers recommended)
- [ ] Pipeline runs `alembic upgrade head` before pod startup
- [ ] Smoke test job passes after staging deployment

## Secrets

- [ ] All secrets stored in AWS Secrets Manager / Vault (no plaintext in env or repo)
- [ ] External Secrets Operator syncing secrets to Kubernetes namespace
- [ ] Secret rotation schedule documented (see security-operations.md)
- [ ] Old secrets revoked after rotation confirmed
- [ ] Emergency break-glass access procedure documented

## Rate Limiting

- [ ] API rate limits configured at ingress (100 RPS default, burst 500)
- [ ] Per-tenant rate limits configured for expensive operations (inference, PDF export)
- [ ] Rate limit exceeded response returns 429 with `Retry-After` header

## CORS

- [ ] CORS restricted to known hospital domains (`CORS_ORIGINS` does not contain `*`)
- [ ] CORS origins list reviewed and approved by security team
- [ ] Wildcard subdomains not used in CORS

## Dependency Scanning

- [ ] `pip-audit -r backend/requirements.txt` — clean (or all exceptions documented with justification)
- [ ] `npm audit --audit-level=high` in frontend — clean (or exceptions documented)
- [ ] `trivy image lumenai/backend:latest` — no CRITICAL vulnerabilities
- [ ] `gitleaks detect` — 0 findings

---

## Sign-Off

| Role              | Name | Signature | Date |
|-------------------|------|-----------|------|
| Lead Engineer     |      |           |      |
| Security Review   |      |           |      |
| QA/Test Lead      |      |           |      |
| Engineering Lead  |      |           |      |

**Deployment approved**: YES / NO

*If any item is unchecked, document the exception below with a resolution plan and timeline.*

### Exceptions / Known Issues
| Item | Exception Reason | Resolution Plan | Due Date |
|------|-----------------|-----------------|----------|
|      |                 |                 |          |
