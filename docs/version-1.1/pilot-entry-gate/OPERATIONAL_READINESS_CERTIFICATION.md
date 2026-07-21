# LPR-DIR-027 — Operational Readiness Certification (Workstream 3)

Verification of operational readiness for a controlled pilot on IRC-1. **Software artifacts
present in the repo are distinguished from operational provisioning that has actually been
performed.** Only performed/verified items can certify.

| Area | Repo artifact present? | Operationally provisioned / verified? | Certification |
|---|---|---|---|
| **Managed environment** | Dockerfiles, `helm/lumenai/*`, `k8s/*` manifests present | ❌ **No managed environment stood up** (no cluster, no running deployment) | **NOT READY** — Pilot Blocking |
| **Deployment process** | `deploy.yml` exists | ❌ **Stub** — deploy steps only `echo` example kubectl (`deploy.yml:148–186`); OPS-DEP-01 | **NOT READY** — Pilot Blocking |
| **Rollback procedure** | RC is schema-compatible by construction (no V1.1 migration) | ❌ **No rollback drill executed** (OPS-DEP-02) | **NOT READY** — Pilot Blocking |
| **Monitoring** | Health/monitoring service in code (`app/services/*monitoring*`, health endpoints) | ⚠️ Code present; **no monitoring stack deployed/connected** | **NOT READY** (partial) |
| **Alerting** | — | ❌ **No alert routing / on-call** (OPS-INC-01) | **NOT READY** — Pilot Blocking |
| **Logging** | Structured logging in the app | ⚠️ Code present; **no central log aggregation provisioned** | **NOT READY** (partial) |
| **Backup** | Backup/restore procedures documented (`docs/foundation/*`); DR docs from prior sprint | ⚠️ Documented + previously exercised in a **dev** run; **not provisioned for a pilot environment** | **NOT READY** (partial) |
| **Disaster recovery** | DR runbook + measured RTO/RPO from a prior dev exercise | ⚠️ Documented; **not validated on a managed pilot environment** | **NOT READY** (partial) |

## Determination

**Operational readiness is NOT CERTIFIED.** Several capabilities exist **as code or
documentation** (monitoring, logging, backup/DR, health checks), but the pilot-gating
operational items — a **managed environment**, a **real deployment path**, an **executed
rollback drill**, and **alerting/incident response** — have **not been provisioned or
verified**. Per the honesty requirement, documented-but-unprovisioned capabilities are
marked NOT READY, not certified. This workstream alone blocks pilot entry.
