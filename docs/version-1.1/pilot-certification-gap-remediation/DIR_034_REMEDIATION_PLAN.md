# LPR-DIR-034 — Pilot Certification Gap Remediation Plan

**Program:** LumenAI Version 1.1 Delivery — Horizon 1 (Clinical Pilot Entry)
**Predecessor gate:** LPR-DIR-033 → **PILOT ENTRY NOT CERTIFIED**
**Status of this document:** DRAFT — remediation plan only. This document
authorizes *no* pilot activity. It defines the gaps that must be closed, the
objective evidence each requires, and the sequence to close them.

## 0. Honesty mandate (binding on every workstream)

- Implementation is not verification. Documentation is not evidence.
  Configuration is not operational capability.
- A gate closes only on **objective evidence produced by execution** —
  logs, measured metrics, signed records, artifacts — not on assertions that
  a capability *exists* or *would work*.
- No production, clinical, GA, or regulatory claim may be made anywhere on the
  basis of this plan or its completion. No FDA clearance or regulatory approval
  is claimed or implied.
- Every gate below carries an explicit **"Rejected evidence"** line naming the
  artifacts that do **not** count, because in prior directives such artifacts
  were repeatedly offered in place of real evidence.

## 1. Why we are here (root cause of the DIR-033 NOT CERTIFIED)

DIR-033 found that the roadmap asserted operational readiness the repository
could not substantiate. Every operational and clinical gate was backed by
*prepared* material (plans, harnesses, dev runs) rather than *executed*
evidence, because the sandbox development environment **cannot provision a
production-representative environment** (risk **RR-10**): no reachable Docker
daemon, no managed PostgreSQL, no multi-replica orchestration, no usable cloud
credentials. Engineering hardening has continued to land on `main`
(schema back-fill, SECRET_KEY fail-closed, RES-01 leader election, the PERF-07
load-test *tool*), but none of it closes an operational or clinical gate.

**The master dependency:** DIR-034 cannot complete inside the sandbox. It
requires a real, authorized, production-representative environment to be
provisioned first (Workstream 0). Until WS0 is satisfied, WS1–WS4 are blocked.

## 2. Open gates carried forward from DIR-033

| # | Gate | DIR-033 state | Closes in |
|---|------|---------------|-----------|
| G1 | Operational capability executed (deploy/rollback/DR/alerting) | ❌ not executed (RR-10) | WS1 |
| G2 | Production-scale performance validated (load/stress/soak) | ❌ tool only, dev baseline only | WS2 |
| G3 | Clinical model validated for pilot use | ❌ candidate model; no completed site validation | WS3 |
| G4 | Environment authorization decision signed | ❌ DIR-031A record UNSIGNED/PENDING | WS0 |
| G5 | Independent pilot-entry certification | ❌ NOT CERTIFIED | WS5 (final) |

## 3. Workstreams

### WS0 — Environment authorization & provisioning (unblocks everything)

**Objective:** A named, authorized, production-representative environment
exists and is under change control.

**Required evidence (all):**
1. **Signed** DIR-031A Authorization Decision Record (closes G4) — named
   accountable owner, scope, data-handling terms, BAA status.
2. Provisioned managed PostgreSQL (not SQLite), reachable, with credentials
   held in a secret manager — evidenced by a connection + `alembic upgrade head`
   log against that database.
3. Multi-replica application deployment (≥2 replicas) reachable over TLS —
   evidenced by `/health` and `/ready` 200s from each replica and the RES-01
   leader row showing exactly one holder.
4. Infrastructure-as-code / deployment manifest committed and applied, with the
   applied revision recorded.

**Rejected evidence:** render.yaml/compose files alone; a local uvicorn+SQLite
run; screenshots of a config page; "the environment is provisionable."

**Dependency:** none — this is the entry workstream. **Blocks WS1–WS3.**

---

### WS1 — Operational capability execution (closes G1)

**Objective:** Prove the platform can be deployed, rolled back, recovered, and
observed on the WS0 environment.

**Required evidence (all):**
1. **Deploy:** a clean deploy to the WS0 environment from a tagged commit —
   deployment log + post-deploy `/ready` 200 across replicas.
2. **Rollback:** a deliberate rollback to the previous revision — log showing
   the revision change and service continuity, with measured time-to-rollback.
3. **Disaster recovery:** backup taken, environment destroyed or DB dropped,
   restore executed — with **measured RTO and RPO** and a post-restore data
   integrity check (row counts / hash-chain continuity on `audit_logs`).
4. **Alerting:** an induced failure (e.g. DB unreachable) that fires a real
   alert to a real channel — evidenced by the alert payload and timestamp.
5. **Scheduler safety under scale-out (RES-01 in production):** logs from ≥2
   replicas showing exactly one leader running the schedulers and a
   demonstrated failover when the leader is killed.

**Rejected evidence:** the DR *procedure* doc without an executed run; a dev
backup/restore on SQLite; "alerting is configured" without a fired alert.

**Dependency:** WS0.

---

### WS2 — Production-scale performance validation (closes G2)

**Objective:** Establish real p95/p99 latency, throughput ceilings, and
stability using the PERF-07 harness against the WS0 environment.

**Required evidence (all):**
1. **Load:** PERF-07 run against WS0 (managed Postgres, ≥2 replicas) at a
   representative authenticated read/write mix — JSON report with per-endpoint
   p50/p95/p99 and throughput, plus the target environment stamped in.
2. **Stress:** concurrency ramped to failure — the report identifying the knee
   (throughput plateau) and the SLO-breach point.
3. **Soak:** a multi-hour run at sustained load — evidence of no memory growth /
   leak and stable latency over time.
4. **Horizontal-scaling curve:** the sweep repeated at 1/2/N replicas showing
   throughput scales with replicas (validating the RES-01-enabled model).
5. A recorded pass/fail against explicit pilot SLOs (define the SLOs as part of
   this workstream, e.g. p95 < X ms at Y req/s, error rate < Z%).

**Rejected evidence:** the dev single-process SQLite baseline already recorded
in `docs/production-readiness/perf-07-load-test/`; the harness existing without
a WS0 run.

**Dependency:** WS0.

---

### WS3 — Clinical model & workflow validation (closes G3)

**Objective:** Move the vision model from *candidate* to *validated for pilot
use* under the existing shadow-validation and clinical-review-board governance,
on real (non-synthetic) site data.

**Required evidence (all):**
1. A prospective **shadow-mode** run at the pilot site (AI advisory, human
   decides) over a pre-registered case volume, with ground truth collected.
2. Computed validation metrics (sensitivity/specificity, calibration, error
   analysis) against ground truth — meeting pre-registered acceptance
   thresholds set **before** the run.
3. **Clinical Review Board** sign-off on the validation package (real data),
   recorded as a signed decision.
4. Confirmation that safety invariants hold on the live path: contamination
   fail-closed states, `human_review_required: true` on correlation outputs, no
   causation language, hospital anonymization in any cross-site intelligence.
5. Model promotion recorded through the existing candidate→validated gate with
   the model card updated to reflect the site validation.

**Rejected evidence:** metrics computed on synthetic/demo data; the training-set
evaluation already in the model card; "the model is available" without a
site-data validation package; a shadow *harness* without a completed run.

**Dependency:** WS0 (a real environment holding real, consented site data under
the signed authorization). Tenant isolation and consent records must be
verified before any site data is ingested.

---

### WS4 — Security & data-governance confirmation on the live environment

**Objective:** Re-confirm the non-negotiable security constraints hold on the
WS0 environment (not just in unit tests).

**Required evidence (all):**
1. SECRET_KEY / AUTH_MODE production guards observed firing correctly on the
   live config (strong secret present; weak/unset would fail-closed).
2. Tenant data isolation verified on the live multi-tenant deployment — a
   cross-tenant read attempt denied, evidenced by request/response + audit
   event.
3. Every intelligence-sharing action produces an audit event; `audit_logs`
   hash chain verified continuous on the production DB.
4. Secrets are stored in a secret manager and API keys are hash-only
   (SHA-256), never retrievable — evidenced by inspection.
5. No PHI in demo data / image metadata on the live environment.

**Rejected evidence:** the passing unit-test suite alone (necessary, not
sufficient); a security policy doc without a live check.

**Dependency:** WS0. Runs alongside WS1–WS3.

---

### WS5 — Independent pilot-entry re-certification (closes G5, final gate)

**Objective:** An independent reviewer re-runs the DIR-033 certification
checklist against the WS0–WS4 **evidence** and issues a determination.

**Required evidence:**
1. An evidence index linking every gate G1–G4 to its executed artifact (log,
   metric report, signed record) with commit/run references.
2. Independent verification that each artifact is execution-derived, not
   prepared — applying the DIR-033 WS7 rule ("reject documentation presented as
   deployment").
3. A signed determination: **PILOT ENTRY CERTIFIED** / **CERTIFIED WITH
   CONDITIONS** / **NOT CERTIFIED**.

**Dependency:** WS0–WS4 complete.

## 4. Sequence

```
WS0 (authorize + provision)  ──►  WS1 (operational execution)  ─┐
        │                          WS2 (performance validation) ─┤─►  WS5
        │                          WS3 (clinical validation)    ─┤   (re-certify)
        └────────────────────────► WS4 (security confirmation)  ─┘
```

WS0 is strictly first. WS1–WS4 run in parallel once WS0 holds. WS5 is last and
gates pilot entry.

## 5. Overall exit criteria (to reach GO)

Pilot entry is **GO** only when all of the following are true, each backed by
execution evidence indexed in WS5:

- [ ] G4 — Authorization decision **signed** (WS0)
- [ ] Production-representative environment **provisioned** and under change
      control (WS0)
- [ ] G1 — Deploy, rollback, DR (with measured RTO/RPO), and alerting all
      **executed** on that environment (WS1)
- [ ] RES-01 leader election demonstrated correct under real scale-out (WS1)
- [ ] G2 — Load / stress / soak **run** against the real environment and
      **passing pre-registered SLOs** (WS2)
- [ ] G3 — Clinical shadow validation **completed** on real site data with
      Clinical Review Board sign-off; model promoted candidate→validated (WS3)
- [ ] WS4 security/data-governance constraints **confirmed live**
- [ ] G5 — Independent re-certification issues **PILOT ENTRY CERTIFIED** (WS5)

Any unmet box ⇒ **NO-GO**. Partial completion is not conditional GO unless WS5
explicitly issues CERTIFIED WITH CONDITIONS naming the residual risk and its
compensating control.

## 6. What this plan explicitly does not do

- It does not provision the environment — that is an authorized human/infra
  action (WS0) that cannot occur in the development sandbox (RR-10).
- It does not claim any gate is closable by writing more code or docs here.
- It makes no production, clinical, GA, or regulatory claim, and asserts no FDA
  clearance or regulatory approval.

## 7. Immediate next action

Execute **WS0**: obtain the signed DIR-031A authorization and provision the
production-representative environment. No WS1–WS5 evidence can be produced
before WS0 holds. Until then, the pilot determination remains **NO-GO**.
