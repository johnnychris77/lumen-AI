# LPR-DIR-028 — Operational Runbooks (Workstream 4)

Runbooks for operating the pilot environment. **These are procedures to be executed on a
provisioned managed environment; drafting them here does NOT constitute execution.** A
runbook is "proven" only when its drill has been run and recorded (evidence tracker).

---

## 1. Deployment
**Trigger:** approved release commit (currently IRC-1 `5c22345`).
1. Confirm target env healthy; confirm secrets present (`SECRET_KEY`, webhook + Stripe
   secrets, DB URL).
2. Build + push container image; record digest.
3. `alembic upgrade head` against managed DB (expect `e7b2f4a86c31`).
4. Deploy via Helm/kubectl (single replica for pilot); `kubectl rollout status`.
5. Smoke test: `/health` 200 + one authenticated route + a signed webhook (expect 200).
6. Record image digest, commit SHA, migration head, smoke result.
**Rollback if any step fails:** §2.

## 2. Rollback
1. Identify last-known-good release (image digest + commit).
2. Redeploy prior image; `rollout status`.
3. Verify: no forward-only migration was applied (V1.1 adds none — schema-compatible).
4. Smoke test green; confirm DB integrity (row counts / hashes).
5. Record MTTR + before/after versions.

## 3. Incident Response
**Severity triage:** SEV1 (patient-safety-relevant / data integrity / outage), SEV2
(degraded), SEV3 (minor).
1. Alert fires → on-call acknowledges (target ack time defined per SEV).
2. Declare incident; open timeline; assign incident commander.
3. Contain: for tenant/safety concerns, rely on fail-closed webhook + `human_review_required`
   invariants; disable affected integration via missing secret if needed.
4. Diagnose using logs/metrics; mitigate; verify.
5. Post-incident review + corrective actions.
**Escalation:** on-call → DevSecOps Director → CISO/CTO (SEV1 also → Clinical Ops for
safety-relevant events).

## 4. System Recovery
1. Assess scope (app vs DB vs infra).
2. App: redeploy last-known-good (§2). DB: restore from snapshot (§6).
3. Re-run smoke tests; confirm audit hash-chain continuity.
4. Record RTO achieved.

## 5. Monitoring Response
- **High error rate / latency:** inspect recent deploy; roll back if correlated (§2).
- **DB saturation:** check connections/slow queries; scale managed DB per plan.
- **Safety fail-closed spike** (webhook 503/decision fail-closed): verify secret/tenant
  config; treat as SEV2+ if unexpected.
- Each alert maps to a documented action + owner.

## 6. Data Recovery
1. Identify recovery point (snapshot).
2. Restore to a clean instance; verify integrity (row counts, audit chain, evidence hashes).
3. Measure + record RPO/RTO.
4. Cut over or export as required; record chain-of-custody.

## 7. Support Escalation
Tier 1 (site super-user) → Tier 2 (Clinical Ops) → Tier 3 (Engineering on-call) →
Director/Exec for SEV1. Clinical/safety concerns always parallel-notify Clinical Operations
Director + CMTO.

---

## Honest caveat
Every runbook above is **unproven until drilled** on the managed environment. Deployment,
rollback, incident response, recovery, and data recovery each require an **executed drill
with recorded evidence** (OPS-DEP-01/02, OPS-INC-01, WP-04/WP-05) before the corresponding
Pilot Entry Gate can be considered for closure.
