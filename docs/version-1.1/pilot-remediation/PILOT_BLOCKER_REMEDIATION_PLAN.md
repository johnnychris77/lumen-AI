# LPR-DIR-028 — Pilot Blocker Remediation Plan (Workstream 1)

Actionable, verifiable remediation work packages for every Pilot-Blocking item identified
in LPR-DIR-027 (PILOT ENTRY DENIED). **This is a plan. It closes nothing.** No blocker is
marked closed here; closure requires objective, demonstrated evidence recorded in
`PILOT_ENTRY_EVIDENCE_TRACKER.md`.

**Owners are role titles**, not named individuals (none are assigned in-repo). "Estimated
Completion" is a relative work-effort estimate (business days of focused effort once
started), **not** a commitment date — several items depend on external parties and cannot
be scheduled from engineering alone.

## Pilot-Blocking work packages

### WP-01 — Managed, backed-up database (closes SCAL-01 at pilot scope)
- **Description:** Replace single-container Postgres (SPOF) with a managed Postgres instance
  with automated backups for the pilot environment.
- **Root cause:** `docker-compose`/single-pod Postgres; no HA, no managed backups.
- **Required work:** Provision managed Postgres (or HA pair); enable PITR/automated
  snapshots; wire connection via secrets; run migrations to head `e7b2f4a86c31`.
- **Owner:** Release Engineering Director (with DevSecOps Director).
- **Dependencies:** Cloud/account + WP-06 secrets management.
- **Target evidence:** Managed-DB connection proof; a successful `alembic upgrade head`
  transcript; a backup snapshot listing + a restore test transcript.
- **Verification method:** Restore drill (see WP-05) reads back seeded data; RPO/RTO measured.
- **Estimated completion:** 3–5 days (post account access).

### WP-02 — Alerting + incident response / on-call (closes OPS-INC-01)
- **Description:** Provision alert routing and a documented on-call/IR path for safety and
  availability events.
- **Root cause:** No alert routing, no on-call rotation, no IR runbook wired to signals.
- **Required work:** Connect metrics/health to an alerting backend; define alert rules
  (error rate, latency, DB, contamination-safety fail-closed events); publish on-call
  rotation; wire the IR runbook (OPERATIONAL_RUNBOOKS.md §Incident Response).
- **Owner:** DevSecOps Director (with COO for on-call staffing).
- **Dependencies:** WP-03 monitoring stack.
- **Target evidence:** A test alert fired → received by on-call; signed on-call schedule.
- **Verification method:** Synthetic alert drill; screenshot/log of delivery + acknowledgement.
- **Estimated completion:** 3–4 days.

### WP-03 — Real deployment path (closes OPS-DEP-01)
- **Description:** Replace the stub `deploy.yml` (echoes kubectl, lines 148–186) with a real
  rollout to the managed pilot environment.
- **Root cause:** Deploy job only prints example commands; no cluster/target wired.
- **Required work:** Stand up the target (k8s/Helm already in `helm/lumenai`, `k8s/`);
  parameterize image + secrets; implement real `kubectl/helm` apply + `rollout status`;
  gate on health check.
- **Owner:** Release Engineering Director.
- **Dependencies:** WP-01, WP-06, a built+pushed container image (integrity gap from LPR-DIR-026).
- **Target evidence:** A green deploy run that brings up a healthy instance (readiness 200).
- **Verification method:** Post-deploy smoke test hits `/health` + one authenticated route.
- **Estimated completion:** 4–6 days.

### WP-04 — Executed rollback drill (closes OPS-DEP-02)
- **Description:** Perform and record a rollback of a deployed version on the managed env.
- **Root cause:** No rollback has ever been executed; only asserted schema-compatible by
  construction.
- **Required work:** Deploy version A, deploy version B, roll back to A; confirm data +
  service integrity; record timings.
- **Owner:** Release Engineering Director.
- **Dependencies:** WP-03.
- **Target evidence:** Rollback transcript with before/after health + version + measured MTTR.
- **Verification method:** Post-rollback smoke test green; DB intact.
- **Estimated completion:** 1–2 days (post WP-03).

### WP-05 — Backup + disaster-recovery drill on the pilot env
- **Description:** Execute backup and restore/DR on the managed environment (not a dev run).
- **Root cause:** Backup/DR exist as docs + a prior dev exercise only.
- **Required work:** Take a managed snapshot; restore to a clean instance; verify integrity;
  measure RTO/RPO.
- **Owner:** DevSecOps Director.
- **Dependencies:** WP-01.
- **Target evidence:** Restore transcript + measured RTO/RPO on the pilot-class environment.
- **Verification method:** Restored instance passes smoke test + row-count/hash checks.
- **Estimated completion:** 2–3 days.

### WP-06 — Secrets management + TLS for the pilot env
- **Description:** Provision a secrets store and TLS; supply the fail-closed webhook contract
  (`WEBHOOK_SECRET_*`, `WEBHOOK_TENANT_*`, `STRIPE_WEBHOOK_SECRET`) and a strong `SECRET_KEY`.
- **Root cause:** No managed secrets/TLS for a pilot; webhooks are (correctly) fail-closed
  and require provisioned secrets to function.
- **Owner:** CISO (with DevSecOps Director).
- **Dependencies:** WP-03 environment.
- **Target evidence:** Secrets injected from a store (not literals); TLS cert served; webhook
  smoke test returns 200 on a correctly signed request and 401/503 otherwise.
- **Verification method:** `curl` TLS check; signed vs unsigned webhook test.
- **Estimated completion:** 2–3 days.

### WP-07 — Clinical pilot real-world prerequisites (addresses GATE-RW)
- **Description:** Secure pilot hospital, clinical sponsor, qualified equipment, site
  baselines, populated Digital Twins, trained/assessed operators, site escalation.
- **Root cause:** None exist; these are real-world commitments, not code.
- **Required work:** See `CLINICAL_PILOT_PREPARATION_PLAN.md` (WS3) — the full breakdown.
- **Owner:** Clinical Operations Director + CMTO (business/BD to secure the site).
- **Dependencies:** Executed site agreement + data agreement (external).
- **Target evidence:** Signed site + sponsor agreement; equipment qualification record;
  operator competency sign-offs; escalation SOP acknowledged by the site.
- **Verification method:** Documented, countersigned artifacts in the evidence tracker.
- **Estimated completion:** **Externally dependent** — cannot be estimated from engineering;
  gated on securing a site.

### WP-08 — Executive authorization (addresses WS7 PENDING approvals)
- **Description:** Obtain documented approvals from CTO, CISO, Quality, Clinical, Operations,
  Executive Sponsor against a written pilot protocol.
- **Owner:** Program Director (coordinates); each named role owner (approves).
- **Dependencies:** WP-01..WP-07 evidence (approvers should sign against demonstrated capability).
- **Target evidence:** Six countersigned approval records (see `EXECUTIVE_APPROVAL_PACKAGE.md`).
- **Verification method:** Signed artifacts recorded in the evidence tracker.
- **Estimated completion:** 1–2 days after WP-01..WP-07 evidence exists.

## Cross-reference: production-blocking (NOT pilot-gating, tracked)
SEC-H-01/02 (secret fallbacks / `Settings.validate()` gap), PERF-07 (load test), RES-01
(scheduler leader election) — remediate before production; single-replica pilot does not
require them. Owners: CISO (SEC-H), Release Engineering (PERF-07/RES-01).

## Determination
Every Pilot-Blocking item has a work package with description, root cause, required work,
owner, dependencies, target evidence, verification method, and effort estimate. **No item is
closed.** Closure is tracked objectively in `PILOT_ENTRY_EVIDENCE_TRACKER.md`.
