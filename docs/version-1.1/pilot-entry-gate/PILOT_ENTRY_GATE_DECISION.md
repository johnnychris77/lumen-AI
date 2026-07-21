# LPR-DIR-027 — Pilot Entry Gate Decision (Workstream 8)

## Mandatory-gate roll-up (evidence-based)

| Gate | Result | Blocking? |
|---|---|---|
| WS1 Release Candidate verified | ✅ IRC-1 `5c22345` verified on baseline | No |
| WS2 Blockers classified | ❌ **5 Pilot-Blocking items OPEN** (SCAL-01, OPS-INC-01, OPS-DEP-01, OPS-DEP-02, GATE-RW) | **Yes** |
| WS3 Operational readiness | ❌ **NOT CERTIFIED** — no managed env, deploy stub, no rollback drill, no alerting | **Yes** |
| WS4 Clinical workflow readiness | ❌ **NOT MET** — no site, sponsor, equipment, training, competency | **Yes** |
| WS5 Data governance | ⚠️ software controls present; **unexercised on real data** | Partial |
| WS6 AI governance | ⚠️ software controls present + human review enforced; **model clinical performance not certified** | Partial |
| WS7 Executive authorization | ❌ **all six approvals PENDING** | **Yes** |

## Decision test

- **All mandatory gates passed?** ❌ No — WS2, WS3, WS4, WS7 fail.
- **Remaining risks acceptable?** ❌ No — pilot-blocking operational/clinical risks are open
  and safety-relevant (no alerting/IR, no rollback drill, no managed environment).
- **Pilot execution authorized?** ❌ **No.**

## Determination

> ## ⛔ PILOT ENTRY DENIED
> IRC-1 is a verified, code-clean Internal Release Candidate with the CRITICAL closed and
> AI/data-governance software controls present — but **four mandatory entry gates are
> unsatisfied**: pilot-blocking operational readiness (managed environment, deploy path,
> executed rollback, alerting/IR), clinical workflow readiness (site, sponsor, equipment,
> trained/assessed operators), and **all six executive authorizations (PENDING)**. Planning
> is **not** converted into execution. No pilot is authorized.

## Required corrective actions (to re-evaluate the gate)

1. **Stand up a managed pilot environment** (backed-up Postgres, real deploy path) —
   closes SCAL-01/OPS-DEP-01 at pilot scope.
2. **Provision alerting + on-call/incident response** — closes OPS-INC-01.
3. **Execute a rollback drill** on that environment — closes OPS-DEP-02.
4. **Select + contract a pilot site and named clinical sponsor.**
5. **Qualify imaging equipment; load site-specific baselines; populate Digital Twins.**
6. **Train operators and complete competency assessment; define site escalation.**
7. **Obtain and document all six executive approvals** against a written pilot protocol.
8. (Recommended before production, not strictly pilot-gating) close SEC-H-01/02, PERF-07,
   RES-01.

Only after items 1–7 are satisfied and re-verified may this gate be re-run. No production
authorization; no clinical or regulatory claims.
