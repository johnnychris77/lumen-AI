# ENVIRONMENT AUTHORIZATION REQUEST — LPR-DIR-031A

**Program:** LumenAI Version 1.1 Delivery Program (Horizon 1).
**Directive:** LPR-DIR-031A "Environment Authorization" — the gating step between the
completed **DIR-031 (Operational Execution Attempt → INCOMPLETE)** and the future
**DIR-032 (Operational Execution)**.
**Status of this document:** REQUEST — authorizes nothing on its own. Authorization is
recorded (and signed) in `AUTHORIZATION_DECISION_RECORD.md`.
**Standard (unchanged):** implementation ≠ verification; documentation ≠ operational
evidence; no production/clinical/regulatory claim; no pilot authorization here.

## 1. Why this request exists (the RR-10 unblock)
DIR-031 attempted to generate managed-environment operational evidence and objectively
established (`../pilot-operational-capability/evidence/PROVISIONING_PROBE.log`) that the
execution context **cannot provision** one: no container daemon, no cluster tooling, no cloud
CLI, no managed Postgres, no usable credentials. That single gap — logged as **RR-10** — blocks
every remaining operational Pilot-Entry item (SCAL-01, OPS-DEP-01/02, OPS-INC-01, DR, E-02).

**This request asks the governance authority to authorize and provision a managed environment
and supply scoped credentials**, so that DIR-032 can execute deploy / rollback / backup-DR /
monitoring-alerting / secrets-TLS / incident drills and produce real evidence.

## 2. What is requested
1. Authorization to provision a **non-production, pilot-grade managed environment** per
   `MANAGED_ENVIRONMENT_SPECIFICATION.md`.
2. Provisioning of that environment by the accountable infrastructure/cloud owner.
3. Delivery of **scoped, least-privilege credentials/access** to the DIR-032 executing context
   per `CREDENTIAL_AND_ACCESS_REQUIREMENTS.md` (secrets delivered via a secrets store / CI
   secret settings — **never** committed to the repository).
4. Confirmation of a **budget envelope** per `COST_AND_BUDGET_ENVELOPE.md`.

## 3. Explicitly NOT requested / NOT granted here
- **Not** a pilot authorization (DIR-034 territory) and **not** pilot execution (DIR-035).
- **Not** a production environment or production authorization.
- **Not** clinical-use authorization; **not** any regulatory claim.
- **Not** processing of real patient data or PHI — the pilot-grade environment is for
  operational-capability evidence using synthetic/non-PHI data only.

## 4. Scope of the environment (pilot-grade, non-production)
| Component | Purpose |
|---|---|
| Managed Kubernetes (or equivalent hosting) | run LumenAI; execute deploy + rollback |
| Managed PostgreSQL | authoritative DB; migrations; backup/restore/DR with RTO/RPO |
| Secrets store | inject/rotate `WEBHOOK_SECRET_*`, signing keys, `DATABASE_URL` |
| Ingress + managed TLS | HTTPS endpoint; certificate lifecycle; HTTPS enforcement |
| Persistent storage / object store | images + backup artifacts |
| Monitoring + alerting + on-call route | metrics, dashboards, alert delivery/ack |

## 5. Decision requested
Approve, approve-with-conditions, or deny this request via the decision record. **Until it is
signed and the environment + credentials exist, DIR-032 cannot begin** and Pilot Entry remains
DENIED.

## 6. Acceptance
When authorized and provisioned, DIR-032 will be measured against
`DIR_032_ACCEPTANCE_CHECKLIST.md` — the objective evidence each operational Work Package must
produce.
