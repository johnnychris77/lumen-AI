# LPR-DIR-016 — Operational Risk Register (Phase 5)

Severity: **Critical / High / Medium / Low / Observation**. Blocking = must resolve
before production authorization. Baseline `bd94bc5`. Documentation only; all items
pre-existing.

| ID | Description | Evidence | Impact | Likelihood | Severity | Owner | Mitigation | Blocking |
|---|---|---|---|---|---|---|---|---|
| **OPS-INC-01** | No formal incident-response/on-call/postmortem process; no alerting → detection human-dependent | doc scan; `prometheus.yml` no rules | Production incidents undetected/uncoordinated | High | **HIGH** | SRE/COO | Adopt IR framework + on-call + Alertmanager rules; run a game-day | **YES** |
| **OPS-DEP-01** | Production deploy not automated — `deploy.yml` echoes kubectl | `.github/workflows/deploy.yml` | No verified, repeatable prod rollout | High | **HIGH** | DevOps | Wire real rollout + post-deploy verify | **YES** |
| **OPS-DEP-02** | No executed production rollback drill (only demo rollback runs) | OPERATIONS_RUNBOOK | Unproven recovery from a bad deploy | Med-High | **HIGH** | DevOps | Execute a rollback drill; document | **YES** |
| MON-02 / OPS-OBS-02 | No alert rules | `prometheus.yml` | No paging on outage/regression | High | MEDIUM | SRE | Prometheus/Alertmanager SLO alerts | No (rolls into OPS-INC-01) |
| OPS-OBS-01 / MON-01 | Thin metrics; no SLOs/error budgets | `/metrics` | Cannot measure/target prod health | High | MEDIUM | SRE | Latency/error/pool histograms + SLOs | No |
| BC-01 | No automated DB failover (single Postgres SPOF) | infra (AR-06) | Extended outage on DB failure | Med | MEDIUM | Infra | Managed HA Postgres / replica promotion | No |
| BC-02 | No disaster-communication plan | doc scan | Uncoordinated tenant comms in a SEV-1 | Med | MEDIUM | COO | Comms plan + status page + RACI | No |
| ENV-01 | Four divergent production descriptors (compose/render/Helm/k8s) | repo | Config drift → deploy inconsistency | Med | MEDIUM | DevOps | Single authoritative IaC | No |
| OPS-GOV-03 | No access-review process | doc scan | Stale/over-broad prod/secret access | Med | MEDIUM | Security | Periodic access review | No |
| OPS-GOV-04 | No on-call/escalation process | doc scan | = OPS-INC-01 | Med | MEDIUM | SRE | On-call roster + escalation | No |
| RB-05 | Runbook drift (GA runbook contradicts executed DR drill) | runbooks | Operators act on stale info | Med | MEDIUM | PMO | Reconcile + doc-ownership | No |
| RB-01/RB-02/RB-04 | Missing tenant-recovery / audit-reconcile / auth-outage runbooks | runbook coverage | Slower incident recovery | Med | MEDIUM | SRE | Author missing runbooks | No |
| MON-03 | No HPA/autoscaling + utilization alerts | k8s | Manual scaling; no burst response | Med | MEDIUM | Infra | HPA + utilization alerts | No |
| SUP-01/SUP-02 | No support index + support→on-call escalation/SLA | docs | Slow first-line support | Med | MEDIUM | Support | Support index + tiered escalation | No |
| OPS-GOV-01/02 | No operational change-mgmt / maintenance-window policy | doc scan | Uncontrolled prod changes | Low-Med | LOW | PMO | CAB + maintenance windows | No |
| DR-02 | WAL/PITR off → RPO = cadence | foundation | Data-loss window = cadence | Low | LOW | Infra | Enable WAL/PITR | No |

## Inherited blocking items (from prior phases — still open)
| ID | Phase | Severity |
|---|---|---|
| SEC-C-01 webhook fail-open → cross-tenant injection | 3 | **CRITICAL** |
| SEC-H-01/02 HS256 secret fallback + no startup validation | 3 | HIGH |
| PERF-07 production load/stress test not executed | 4 | HIGH |
| SCAL-01 single Postgres SPOF + single-worker pods | 4 | HIGH |
| RES-01 in-process scheduler duplicates across replicas | 4 | HIGH |

## Summary
- **Operational HIGH (3, blocking):** OPS-INC-01 (no IR/alerting), OPS-DEP-01
  (deploy not automated), OPS-DEP-02 (no rollback drill). **No new operational
  CRITICAL** — but the **inherited Phase 3 CRITICAL (SEC-C-01)** remains the top
  production blocker.
- **SPOF:** single PostgreSQL (BC-01/AR-06), in-process scheduler (RES-01), and — at
  the process level — a single un-drilled deploy/rollback path.
- **Theme:** the platform has **strong foundations and honest documentation** but
  **immature operational processes** (detect/respond/deploy/rollback/failover/access-
  review) and open cross-phase blockers. All are addressable; none require redesign.
