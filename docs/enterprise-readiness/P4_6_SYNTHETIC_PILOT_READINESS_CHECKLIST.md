# P4.6 — Synthetic Pilot Readiness Checklist

**Purpose:** the operational gate the designated pilot operator and Release Authority use before the
synthetic pilot may start. **Every item must be PASS with recorded evidence.** Unchecked or failing
items keep the pilot on **HOLD**. This checklist verifies controls are *in force in the pilot
environment*; it does **not** substitute for the independent security review (SEC-175-01) or the
governance decisions — those are separate gates listed in §9.

**Evidence columns are intentionally blank** — the operator records the evidence reference and the
verifier; the AI workflow does not pre-pass any item. Code locations reference the combined
integration content (`7c0f679` via #178).

---

## 1. Checklist

| # | Area | Control to confirm (in the pilot environment) | Evidence ref | Verified by / date | Result |
|---|------|-----------------------------------------------|--------------|--------------------|--------|
| 1 | **Authentication** | OIDC-only research access; **no** `dev-token`/bypass; malformed token → **401 not 500** (`trc001_research.py::require_verified_oidc_context`, SEC-176 #7) | | | ☐ |
| 2 | **Authentication** | No reintroduced hardcoded `Bearer dev-token` anywhere in the pilot config/code path | | | ☐ |
| 3 | **Tenant isolation** | Cross-tenant image read/write impossible; `assert_image_bytes_readable` tenant check active; cohort/query scoping enforced | | | ☐ |
| 4 | **Tenant isolation** | Research tenant(s) are LumenAI-owned synthetic tenants; no shared data across tenants | | | ☐ |
| 5 | **Artifact access** | Artifact store uses injective **hex** encoding; non-hex/legacy refs rejected (return None), path-traversal (`../`) rejected (RGI-04, C-09/C-10); atomic writes | | | ☐ |
| 6 | **Artifact access** | No pre-existing `artifact://` legacy artifacts in the pilot environment (filesystem inventory, RK-04); if any found, offline re-key run **before** start | | | ☐ |
| 7 | **Audit logging** | Denied-access decisions durably recorded in hash-chained append-only `audit_logs` and survive request teardown/rollback (SEC-174-01, C-08) | | | ☐ |
| 8 | **Audit logging** | Every intelligence-sharing / access decision produces an audit event; hospital/cross-tenant identities anonymized where applicable | | | ☐ |
| 9 | **Benchmark integrity** | `research_execution_only` / `require_scientific` gating forces non-scientific checkpoints to `scientifically_valid=False`; metrics not published as scientific (RGI-03, C-13) | | | ☐ |
| 10 | **Benchmark integrity** | Authorization/approval **value** validation in force (`cohort_readiness` rejects `denied`/`purged`/`{"approved":false}`; `valid_statistical_signoff`) (C-14) | | | ☐ |
| 11 | **Benchmark integrity** | Real-data benchmark paths remain **BLOCKED**; only manifest-verified synthetic datasets usable (RK-08) | | | ☐ |
| 12 | **Research-only restrictions** | All outputs labelled research-only / not clinically validated; correlation outputs carry `human_review_required: true`; no causal or FDA language | | | ☐ |
| 13 | **Research-only restrictions** | No clinical/diagnostic/triage output presented as actionable; no production or hospital research path reachable | | | ☐ |
| 14 | **Data admission** | Every dataset in use is `Verified-Permitted` in `P4_6_SYNTHETIC_DATASET_MANIFEST.md`, synthetic status evidenced, no PHI | | | ☐ |
| 15 | **Incident response** | Pilot stop conditions (`CHARTER §4`) documented; operator knows halt+escalate path; on-call/owner named; stop event is recorded as a governance event | | | ☐ |
| 16 | **Incident response** | A detected stop condition triggers immediate HOLD of the affected activity and escalation to Release Authority + Governance Program Lead; resumption requires re-authorization | | | ☐ |
| 17 | **Regression coverage** | Combined security/research regression suites pass in the pilot environment (synthetic) + PG16 where applicable (C-15) | | | ☐ |
| 18 | **Migration integrity** | Single alembic head; migrations applied on the pilot's Postgres engine (SQLite fresh-DB caveat RK-09 noted) (C-12) | | | ☐ |

## 2. Overall readiness determination (DO NOT prepopulate)
| Field | Value |
|---|---|
| All items 1–18 PASS with evidence? | |
| Open exceptions (item # + reason) | |
| Prepared by (operator, role) | |
| Reviewed by (Release Authority) | |
| Date | |
| Determination (READY-pending-approvals / NOT READY) | |

**Even a fully-PASS checklist does not start the pilot.** §9 governance gates must also be recorded.

## 3. Governance gates NOT covered by this checklist (must be separately recorded)
- RGI-01 (synthetic) + RGI-02 decisions — `P4_6_SYNTHETIC_GOVERNANCE_DECISIONS.md`.
- RGI-10 scientific-methodology decision (if any metric reported) — `P4_6_RGI10_METHODOLOGY_DECISION_RECORD.md`.
- **SEC-174-02 + SEC-175-01 independent non-author disposition** — `P4_6_INDEPENDENT_SECURITY_REVIEW_REQUEST.md` (OPEN).
- Release authorization — `P4_6_RELEASE_AUTHORIZATION_RECORD.md`.

*This checklist confirms controls are operating in the environment; it is necessary, not sufficient.
No item is pre-marked PASS. HOLD remains until both this checklist and the §3 gates are recorded.*
