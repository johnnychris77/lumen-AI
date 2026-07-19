# LPR-DIR-016 — Production Checklist (Phase 5)

A comprehensive pre-production operational checklist. **Status legend:** ✅ done ·
⚠️ partial · ❌ missing/blocking. **No production authorization is granted** — this
checklist enumerates what must be true first.

## Deployment
- [⚠️] CI builds + tests + security gates on every PR — ✅ present
- [❌] Automated, verified production rollout (deploy job currently **echoes**
  kubectl — OPS-DEP-01)
- [❌] Executed production **rollback drill** (only demo rollback runs — OPS-DEP-02)
- [❌] Production environment **approval gate** (OPS-DEP-04)
- [⚠️] Single authoritative IaC (four divergent descriptors — ENV-01)
- [✅] Versioned immutable image release (GHCR tags — release-ghcr.yml)

## Security (inherited — blocking)
- [❌] **SEC-C-01** webhook fail-open → cross-tenant injection (CRITICAL, Phase 3)
- [❌] **SEC-H-01/02** remove HS256 secret fallbacks + **startup secret validation**
- [⚠️] Container runs as **root** (SEC-INF-01)
- [✅] SHA-256-only secret storage; secret-scan gated; 0 CVEs

## Monitoring
- [✅] Liveness/readiness probes (DB hard-gate)
- [❌] Latency/error/pool metrics (thin `/metrics` — OPS-OBS-01)
- [❌] SLOs + error budgets (MON-01)
- [❌] Alert rules → on-call (MON-02)
- [❌] Distributed tracing (OPS-OBS-03)

## Backup / Continuity
- [✅] Backup + **restore executed** (measured RTO 10.4 s)
- [❌] Automated DB **failover** (single Postgres SPOF — BC-01)
- [⚠️] WAL/PITR for tight RPO (DR-02)
- [❌] Disaster-**communication** plan (BC-02)
- [⚠️] Recurring DR-drill cadence / game-day (BC-03)

## Logging / Audit
- [✅] Hash-chained tamper-evident audit + chain-verification
- [⚠️] Logging consistency (`print` vs logger; silent excepts — OPS-OBS-04)
- [❌] Scheduled audit-review cadence (OPS-GOV-05)
- [⚠️] Audit-reconciliation runbook (commit-without-audit AR-16 — RB-02)

## Runbooks
- [✅] Deploy/DB/DR/backup/evidence/staging-smoke runbooks exist
- [❌] Tenant-recovery (RB-01), auth-outage (RB-04) runbooks
- [⚠️] Reconcile stale runbooks (RB-05)

## Support
- [✅] Operator/admin/user/training docs exist
- [⚠️] Consolidated support index + freshness (SUP-01)
- [❌] Support→on-call escalation + SLA (SUP-02)

## Training / Communications
- [⚠️] Training material present; delivery/competency not evidenced (SUP-04)
- [❌] On-call rotation + escalation policy (OPS-GOV-04/OPS-INC-01)
- [❌] Incident severity matrix + comms plan (OPS-INC-01)
- [❌] Access-review cadence (OPS-GOV-03)

## Performance (inherited — Phase 4)
- [❌] Production **load/stress test** executed (PERF-07)
- [❌] HA Postgres + multi-worker + pool tuning (SCAL-01)
- [❌] Scheduler leader-election (RES-01)

---

**Summary:** substantial ✅/⚠️ foundations (CI gates, health probes, DR drill,
runbooks, docs) but **multiple ❌ blocking items** across deployment automation,
inherited security (1 CRITICAL), monitoring/alerting, failover, incident/on-call, and
performance load-testing. **The ❌ items must be closed before production
authorization.**
