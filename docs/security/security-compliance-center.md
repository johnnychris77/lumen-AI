# Security & Compliance Center

A single index tying together LumenAI's existing, extensive security
documentation into the topic checklist an enterprise security team,
auditor, or compliance officer needs to review. This document does not
replace any of the detailed docs it links to — it's the map, not the
territory.

## Authentication

Production authentication is JWT/OIDC-based; hardcoded dev tokens
(`Bearer dev-token` and equivalents) are rejected outright when
`APP_ENV=production` (`app/enterprise_auth.py`).

- `docs/security/production-oidc-deployment-guide.md` — OIDC setup
- `docs/security/jwt-revocation-design.md` — token revocation
- `docs/security/lumenai-production-dev-auth-removal-plan-v1.md` — how
  dev-auth is disabled in production
- `docs/security/production-auth-readiness-plan.md`

## Authorization & RBAC

- `docs/security/lumenai-rbac-matrix-v1.md` — the full role/permission
  matrix (`admin`, `spd_manager`, `operator`, `viewer`)
- Enforced via `app/authz.py::require_roles` on every route — see
  `docs/architecture/architecture-enforcement-checklist.md` for the rule
  that every new feature must preserve auditability and role-gating

## Tenant Isolation

- `docs/security/lumenai-tenant-isolation-plan-v1.md` — design
- `docs/security/lumenai-enterprise-tenant-isolation-test-matrix-v1.md` —
  the automated test matrix verifying it
- See also `docs/deployment/multi-tenant-deployment-guide.md`

## Audit Logging

- `app/audit.py::log_audit_event` + `app/models/audit_log.py` — every
  consequential action (supervisor reviews, ground-truth submissions,
  data exports, intelligence sharing) is logged with a tamper-evident
  hash chain (`previous_event_hash`/`event_hash`)
- Phase 23's Clinical Decision Ledger
  (`docs/cios/clinical-decision-ledger.md`) extends this with a
  clinical-decision-specific permanent record

## Encryption

- TLS in transit (terminated at the load balancer —
  `docs/deployment/cloud-architecture-guide.md`)
- Secrets never stored in plaintext application code or logs
- Secret API keys stored as SHA-256 hashes only, issued once via
  `secrets.token_urlsafe(40)`, never retrievable again (CLAUDE.md
  constraint, enforced across the API key issuance flow)

## Secrets Management

- Environment-variable-driven configuration
  (`docs/deployment/ENVIRONMENT_VARIABLE_CHECKLIST.md`)
- No secret is ever committed to the repository or logged — see
  `docs/security/bandit-triage.md` for the static-analysis process that
  catches this class of issue

## Logging

- Structured JSON application logging (`app/main.py`'s `JSONFormatter`)
- `docs/security/lumenai-production-error-response-policy-v1.md` — what
  is and isn't surfaced in error responses (no stack traces or internal
  details leaked to clients in production)

## Incident Response

- `docs/security/security-risk-register.md` — tracked risks and their
  status
- `docs/security/lumenai-threat-model-v1.md` — the threat model informing
  what an "incident" looks like for this platform
- Disaster scenarios and response procedures:
  `docs/deployment/disaster-recovery-guide.md`

## Vulnerability Management

- `docs/security/bandit-triage.md` — static analysis (Bandit) triage
  process
- `docs/regulatory/external-pentest-scope.md` — external penetration
  testing scope
- `docs/security/lumenai-security-hardening-checklist-v1.md` — the
  hardening checklist run before each release
- CI-enforced: `docs/security/lumenai-security-hardening-ci-validation-v1.md`

## Business Continuity & Disaster Recovery

- `docs/deployment/disaster-recovery-guide.md`
- `docs/deployment/backup-restore-guide.md`
- `docs/deployment/high-availability-guide.md`

## Compliance Control Matrix

- `docs/security/compliance-control-matrix.md` — maps controls to
  relevant frameworks (HIPAA Security Rule, SOC 2-style control
  categories) — see that document for exact framework coverage; this
  center does not duplicate its content.

## For auditors and security reviewers

Start with `docs/security/README.md` for the full security documentation
index, and `docs/security/compliance-control-matrix.md` for a
control-by-control mapping. This document exists to orient a first-time
reviewer to where each topic lives, not to be the sole source of truth.
