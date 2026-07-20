# MANAGED ENVIRONMENT SPECIFICATION — LPR-DIR-031A

Provisioning specification for the **pilot-grade, non-production** managed environment that
DIR-032 will execute against. Cloud-agnostic; the accountable infrastructure owner selects the
concrete provider. **No environment is claimed to exist** — this is the target definition.

## 1. Components + acceptance criteria
| # | Component | Requirement | DIR-032 uses it for |
|---|---|---|---|
| C1 | Application hosting | Managed Kubernetes (or equivalent) with ≥2 replicas capability | deploy execution, rollback, HA |
| C2 | Managed PostgreSQL | Managed instance; automated backup + PITR; separate restore target available | migrations, backup/DR, RTO/RPO |
| C3 | Secrets store | Managed secret manager (KMS-backed); no plaintext secrets in manifests/images | secret injection + rotation |
| C4 | Ingress + TLS | Ingress controller + managed certificate (e.g. cert-manager/ACME); HTTP→HTTPS enforced | HTTPS endpoint, cert lifecycle |
| C5 | Persistent storage / object store | Durable volume + object bucket for images and backup artifacts | image storage, backup targets |
| C6 | Observability stack | Metrics store + dashboards + log aggregation | monitoring demonstration |
| C7 | Alerting + on-call | Alert manager + delivery channel (email/Slack/PagerDuty) + on-call rotation | alert generate→deliver→ack |
| C8 | Config management | Declarative config (manifests/Helm/IaC) under version control | reproducible provisioning |

## 2. Sizing (pilot-grade, minimal)
| Resource | Pilot target (indicative) |
|---|---|
| App replicas | 2 (to exercise rollout + leader election for RES-01) |
| Postgres | smallest managed tier with automated backup + PITR |
| Storage | modest (images + backups), with retention policy |
| Monitoring | single-tenant, retention ≥14 days |

## 3. Data policy (hard constraint)
- **Synthetic / non-PHI data only.** No real patient data, no PHI in the pilot-grade
  environment. (Consistent with the program's no-PHI-in-demo-data constraint.)
- Backups of the pilot DB inherit the same no-PHI property.

## 4. Security posture (must hold before DIR-032 executes)
- Secrets delivered via C3 / CI secret settings — **never** committed to the repo.
- Least-privilege service accounts (see `CREDENTIAL_AND_ACCESS_REQUIREMENTS.md`).
- TLS enforced at the ingress (C4); no plaintext service exposure.
- Tenant isolation, fail-closed webhook, hash-only secret storage — already VERIFIED as code
  behavior (DIR-030); C1–C7 make them operational.
- Network egress governed per the organization's policy.

## 5. Reproducibility
Provisioning SHALL be expressed as version-controlled IaC/manifests (C8) so the environment is
**re-creatable**, and so DIR-032 evidence is tied to a known configuration + commit SHA.

## 6. Explicit non-goals
Not production-sized; not multi-region DR; not a clinical or regulated environment; not
handling PHI. Those belong to later Horizon phases, not DIR-031A/032.

## 7. Definition of "provisioned" (entry condition for DIR-032)
All of C1–C8 exist and are reachable from the executing context, credentials per the
requirements doc are delivered, and a smoke `GET /health` against the ingress returns 200 over
HTTPS. Until then, DIR-032 does not start.
