# P4.5 — Formal Release Readiness Decision

**Reviewed content:** combined code `7c0f679` (via #178 `8574a2a`); PR #176 `fdaee8e`, #177
`b35e552`; `main` `0f2ec588` (unchanged). **Engineering completion is not governance
authorization.** This is a recommendation to the enterprise release authority, not an approval.

## 1. Dimension assessment

| # | Dimension | Finding | Verdict |
|---|-----------|---------|---------|
| 1 | Technical validation | Combined full suite **4131 passed / 19 skipped** (SQLite); combined **PG16 green in CI** (#178); Ruff clean; single alembic head; frontend build ✓ | **GO** (technical) |
| 2 | Security remediation (P4.1 #176) | SEC-176 A/B/C/#1/#3/#7 fixed, fail-closed, regression-tested; D already mitigated; #8 not reproducible | **GO** (technical) — pending independent review (dim 6) |
| 3 | Research benchmark integrity (P4.3 #177) | RGI-01..09,11..13 remediated + tests; RGI-10 preserved (policy) | **GO** (technical) — pending governance (dims 4,5) |
| 4 | Institutional authorization governance (RGI-01/02) | Decision packages prepared; **no authorized approval**; registry policy not implemented | **HOLD** |
| 5 | Scientific methodology governance (RGI-10) | Decision package prepared; **no authorized decision**; implementation preserved | **HOLD** |
| 6 | Independent security review (SEC-175-01) | Package + checklist prepared; **no non-author review performed** (author/CI/Codex insufficient) | **HOLD** |
| 7 | Artifact compatibility | Security-correct; legacy-ref break documented; **conditional on pre-upgrade env inventory** (RK-04) | **HOLD (conditional)** |
| 8 | Operational readiness | Migrations PG-targeted (CI PG16 ✓); no production migration performed; re-key remedy ready | **HOLD** — pending env inventory + ops sign-off |
| 9 | Audit & evidence completeness | Evidence index + chain of custody complete; evidence classes separated; CI green | **GO** (evidence assembled) — reviewer must re-verify [DA] items |
| 10 | Residual risks | RK-01..09 open; no confirmed unresolved P1 **security** defect in code within scope; SEC-174-02 latent/Low | **HOLD** — open POL/ASSURE risks |

## 2. Decision

**Overall recommendation: HOLD** (NO-GO for integration into `main` and for enterprise-pilot
authorization **today**).

**Reasoning (per decision rule):**
- **Not GO:** GO requires *all* required approvals + controls verified. Four governance/assurance
  gates are unmet — RGI-01/02 (dim 4), RGI-10 (dim 5), SEC-175-01 independent review (dim 6), and
  SEC-174-02 disposition — plus the conditional artifact-inventory (dim 7). None can be satisfied
  by engineering, CI, or the author.
- **Not NO-GO:** no *confirmed release-blocking technical defect or unacceptable risk* remains in
  the P4.1/P4.3 code scope — the combined technical validation is green and the open items are
  governance decisions and independent review, not broken code. (The separate upstream #162–#169
  Codex-findings track, RK-07, is a NO-GO for integrating *that* chain until independently
  remediated — but it is outside #176/#177/#178.)
- Therefore: **HOLD** — technically review-ready; decisions and independent assurance outstanding.

**This HOLD lifts to GO only when:** dims 4, 5, 6 have authorized approvals recorded; the
SEC-174-02 disposition is recorded; the artifact-inventory condition (RK-04) is satisfied; and no
new release-blocking finding arises from the independent review.

## 3. Reason log (per dimension verdict)
- Dims 1–3, 9 are **GO on the engineering axis** because the evidence executed and passed; they
  are **not** governance approvals.
- Dims 4–8, 10 are **HOLD** because each depends on a human authority (institutional, scientific,
  independent security, or release/ops) whose decision is not yet recorded. No decision is
  inferred or auto-accepted.

---

# P4.5 — Human Approval Matrix (unsigned)

Four independent authorities. **Leave unknown/unauthorized fields blank. Do not impersonate a
reviewer or mark any decision approved.** Each authority must be distinct and, for security,
**non-author**.

## A. Institutional research / data-governance authority (RGI-01/02)
| Field | Value |
|---|---|
| Reviewer name / role | |
| Authority authenticated (how) | |
| Scope reviewed | RGI-01 authorization registry policy; RGI-02 reviewer framework |
| Evidence references | `P4_5_INSTITUTIONAL_AUTHORIZATION_APPROVAL.md`, `P4_4_INSTITUTIONAL_GOVERNANCE_DECISIONS.md` |
| Decision | |
| Conditions | |
| Date | |
| Signature / authenticated approval reference | |

## B. Scientific-methodology authority (RGI-10)
| Field | Value |
|---|---|
| Reviewer name / role | |
| Qualification / authority | |
| Scope reviewed | Pixel Dice/IoU empty-mask convention |
| Evidence references | `P4_5_SCIENTIFIC_METHODOLOGY_APPROVAL.md`, `P4_4_SCIENTIFIC_METRIC_METHODOLOGY.md` |
| Decision (adopt a / b / c / other) | |
| Reporting conditions | |
| Date | |
| Signature / authenticated approval reference | |

## C. Independent non-author security reviewer (SEC-175-01, SEC-174-02)
| Field | Value |
|---|---|
| Reviewer name / role | |
| Independence declaration (did NOT author #171–#178 / prior reviews) | |
| Reviewed SHAs (#176 `fdaee8e` / #177 `b35e552` / #178 `8574a2a`) | |
| Checks executed (synthetic + **PG16**) | |
| Control findings (C-01..C-15) | |
| SEC-174-02 disposition (A/B/C) | |
| Decision (PASS / CONDITIONAL PASS / FAIL / INSUFFICIENT) | |
| Conditions | |
| Date | |
| Signature / authenticated approval reference | |

## D. Enterprise release authority
| Field | Value |
|---|---|
| Approver name / role | |
| Confirms A + B + C recorded and acceptable | |
| Artifact-inventory condition (RK-04) satisfied | |
| Upstream chain (RK-07) status acknowledged | |
| Final decision (GO / HOLD / NO-GO) | |
| Scope authorized (e.g. integrate to `main` / enterprise pilot) | |
| Conditions | |
| Date | |
| Signature / authenticated approval reference | |

*No field above is prepopulated. Until all required rows are completed by the respective
authorized authorities, integration into `main` and enterprise-pilot authorization remain
**HOLD / NO-GO**.*
