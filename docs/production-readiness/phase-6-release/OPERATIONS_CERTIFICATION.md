# LPR-DIR-017 — Operations Certification (Phase 6)

Certifies the Phase 5 operational-readiness review (LPR-DIR-016). Baseline `bd94bc5`.

| Item | Verdict | Evidence (Phase 5) |
|---|---|---|
| Deployment | **CONDITIONAL** | gated CI + versioned GHCR release; **`deploy.yml` echoes kubectl (OPS-DEP-01)**; no rollback drill (OPS-DEP-02) |
| Runbooks | **CERTIFIED w/ conditions** | broad coverage (deploy/DB/DR/backup/evidence/staging); gaps (tenant/auth-outage/audit-reconcile) + drift (RB-05) |
| Monitoring | **CONDITIONAL** | probes + Prometheus/Grafana provisioned; **no SLOs/alerts (MON-01/02)** |
| Incident response | **NOT CERTIFIED** | **no formal IR/on-call/postmortem process (OPS-INC-01)**; framework proposed |
| Business continuity | **CERTIFIED w/ conditions** | DR executed (RTO 10.4 s); **no auto failover (BC-01), no disaster-comms (BC-02)** |
| Support readiness | **CERTIFIED w/ conditions** | broad operator/admin/user/training docs; needs index + escalation/SLA |
| Operational governance | **CONDITIONAL** | strong code change-control + audit capability; **no access-review/on-call/maintenance-window** |

## Blocking findings (must close before production)
- **OPS-INC-01 (HIGH):** no incident-response/on-call/postmortem + no alerting.
- **OPS-DEP-01 (HIGH):** production deploy not automated (stub).
- **OPS-DEP-02 (HIGH):** no executed rollback drill.

## Certification statement
Operational **foundations and documentation are real and substantial** (CI gates,
health probes, runbooks, DR drill, Prometheus/Grafana, rich docs), but operational
**processes are immature** (detect/respond/deploy/rollback/failover/access-review).
Aggregate operational maturity **~2.4/5**; Incident Response scored **1/5**.

**Operations: CERTIFIED (PASS WITH CONDITIONS)** — IR/alerting + deploy/rollback
automation blocking before production.
