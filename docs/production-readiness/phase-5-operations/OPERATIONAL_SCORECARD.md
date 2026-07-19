# LPR-DIR-016 — Operational Scorecard (Phase 5)

**Scale:** 0 (absent) – 5 (excellent). Evidence-based at `bd94bc5`. Scores reflect
implemented + documented + *exercised* state (capped where processes exist on paper
but aren't wired/drilled).

| Category | Score | Rationale |
|---|---|---|
| **Deployment** | **2 / 5** | Strong CI gates + versioned GHCR image release, **but production rollout is an un-wired stub (echoes kubectl)** and no rollback drill |
| **Monitoring** | **2 / 5** | Correct liveness/readiness + Prometheus/Grafana provisioned, but thin metrics, no SLOs, **no alerts** |
| **Support** | **3 / 5** | Broad operator/admin/user/training docs; needs consolidated index + escalation/SLA |
| **Incident Response** | **1 / 5** | **No formal IR/on-call/postmortem process**; detection lacks alerting (framework proposed this phase) |
| **Runbooks** | **3 / 5** | Broad coverage (deploy/DB/DR/backup/evidence/staging); gaps (tenant/auth-outage/audit-reconcile) + stale content |
| **Documentation** | **3 / 5** | Rich corpus (1,000+ docs); needs freshness/index pass; some drift (RB-05) |
| **Business Continuity** | **3 / 5** | **DR executed, measured RTO 10.4 s**, provable integrity; no failover automation or comms plan |
| **Change Management** | **3 / 5** | Strong code change-control (PR + gates + arch freeze); no operational CAB/maintenance-window process |
| **Governance** | **2 / 5** | Audit capability strong; **no access-review, on-call, or maintenance-window processes** |
| **Operations Maturity** | **2 / 5** | Solid foundations + honest self-assessment, but many processes documented-not-exercised + inherited blockers |

## Aggregate
**Weighted operational-readiness posture: ~2.4 / 5 — "Strong foundations, immature
operations."**

- **Strongest (3):** Support, Runbooks, Documentation, Business Continuity, Change
  Management — real, substantial assets.
- **Weakest (1–2):** **Incident Response (1)**, Deployment, Monitoring, Governance,
  Operations Maturity — process + wiring gaps.

**Incident Response at 1** is the standout: no alerting + no IR process means the org
cannot yet reliably **detect and respond** to a production incident. Combined with the
inherited Phase 3 CRITICAL (SEC-C-01) and Phase 4 HIGH blockers, this caps the exit at
**PASS WITH CONDITIONS** and firmly gates production authorization.
