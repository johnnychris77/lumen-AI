# P4.6 — Independent Non-Author Security Review Request (SEC-174-02, SEC-175-01)

**From:** LumenAI Enterprise AI Governance Program (requesting party)
**To:** a qualified, **authorized, non-author** security reviewer (to be named by the Release
Authority)
**Date:** 2026-11-17
**Status:** **REQUEST ONLY.** No disposition is issued here. SEC-174-02 and SEC-175-01 remain
**OPEN**. The author of the code and assurance documents (this AI workflow), LumenAI engineering, CI,
and automated review (Codex) **cannot** satisfy this control. Green CI and automated review are
**supporting evidence, not independent security approval.**

**Independence precondition (SEC-175-01):** the reviewer must **not** have authored PRs #171–#178 or
the prior review documents, and must **declare** this. If you authored any of it, **stop** — you are
not eligible to close this control.

**Why this request exists for the synthetic pilot:** narrowing scope to synthetic data does **not**
remove the independent-security-review requirement. The security controls under review
(authentication, object-level authorization, tenant isolation, audit durability, artifact-store
encoding, out-of-gate byte reads) protect the *mechanism* regardless of whether the data is
synthetic. SEC-175-01 is therefore a **prerequisite** for the synthetic pilot's security axis, not a
waivable item.

**Reviewed content:** combined code `7c0f679` (via #178 `8574a2a`, 7 CI jobs green incl. PG16);
PR #176 `fdaee8e`, #177 `b35e552`. Authoritative detail lives in
`P4_5_INDEPENDENT_SECURITY_REVIEW.md` (control checklist C-01…C-15 + disposition forms) and
`SEC-174-02_DISPOSITION.md`; this request references them rather than restating.

---

## 1. What is requested (written disposition)

A written disposition identifying, per the documented acceptance criteria:
- **Controls independently verified** (which of C-01…C-15, with the reviewer's own evidence).
- **Findings requiring remediation** (new or confirmed).
- **Evidence reviewed** (SHAs, tests executed — synthetic **and** PG16).
- **Residual risks and conditions.**
- **SEC-174-02 disposition** (Option A / B / C) and **SEC-175-01 decision** (PASS / CONDITIONAL PASS
  / FAIL / INSUFFICIENT EVIDENCE).
- **Reviewer identity, qualifications, independence declaration, and date.**

The engineering team's automated test results are **supporting evidence** and are explicitly **not**
presented as independent security approval.

## 2. SEC-174-02 — acceptance criteria (verbatim; do not infer from the ID)

Finding: `training_eligibility_service.compute_training_eligibility` (no tenant filter, no `source`
exclusion) and `research/lens_vision/data_loader.load_research_samples` read `image_bytes` **without**
the central `assert_image_bytes_readable` gate. **Latent** — no HTTP route reaches either today.
Severity **Low**.

- **Option A (gate — recommended):** route both byte reads through `assert_image_bytes_readable`
  (or the `source`-exclusion pattern) **and** add a tenant filter to `compute_training_eligibility`.
  *Acceptance:* a regression test shows (a) research-source rows excluded from both functions, and
  (b) cross-tenant rows unreadable via `compute_training_eligibility`.
- **Option B (quarantine):** guard that raises if either is called in a request context.
  *Acceptance:* a test shows the guard raises for a request-scoped caller.
- **Option C (formal risk acceptance):** written acceptance that both remain unexposed + a tracked
  action to gate before any future exposure. *Acceptance:* signed acceptance + tracking issue.

**Synthetic-pilot note:** even under synthetic-only scope, if either function were wired to a request
path the latent gap would become reachable; the reviewer should state whether the synthetic pilot's
configuration leaves both unreachable, and condition accordingly.

## 3. SEC-175-01 — closure procedure (verbatim)

A **verified non-author** reviewer reviews PRs #171–#175 (and now #176–#178) at their exact heads,
executes the synthetic + PG16 tests, assesses SEC-174-02, and records the decision + independence
declaration in the **Reviewer decision** section of `P3_SECURITY_REVIEW_HANDOFF.md`. **An AI
workflow's self-review does NOT close it.** Automated review and green CI are necessary, not
sufficient.

## 4. Disposition forms (DO NOT prepopulate)

### SEC-174-02 disposition
| Field | Value |
|---|---|
| Reviewer name / org / role | |
| Independence declaration (non-author) | |
| Decision (A / B / C / Other) | |
| Rationale | |
| Follow-up actions + owner | |
| Review date | |
| Disposition status (Open / Accepted / Closed) | |
| Signature / approved review-record reference | |

### SEC-175-01 disposition
| Field | Value |
|---|---|
| Reviewer name / org / role | |
| Independence declaration (did NOT author #171–#178 or prior reviews) | |
| Reviewed SHAs (#176 `fdaee8e` / #177 `b35e552` / #178 `8574a2a`) | |
| Checks executed (synthetic + **PG16**) | |
| Per-control findings (C-01..C-15) | |
| SEC-174-02 disposition referenced | |
| Decision (PASS / CONDITIONAL PASS / FAIL / INSUFFICIENT EVIDENCE) | |
| Conditions | |
| Date | |
| Signature / approved review-record reference | |

## 5. Author-side supporting evidence (not independent approval)
Provided to the reviewer as inputs only: combined full suite **4131 passed / 19 skipped** (SQLite);
combined **PG16 green in CI** on #178; Ruff clean; single alembic head `f1a2b3c4d5e6`; frontend build
green; failing-before-fix regression proof for the P4.1/P4.3 fixes. These do **not** substitute for
the reviewer's independent verification.

---

*No disposition is issued here. SEC-174-02 and SEC-175-01 remain OPEN until a qualified non-author
reviewer records decisions above. The requesting party does not and cannot self-issue this approval.*
