# P4.5 — Institutional Authorization Approval Package (RGI-01, RGI-02)

**Status:** DECISION-READY PROPOSAL for authorized institutional decision-makers. **No
institutional approval is created, asserted, or marked approved** by this document or by the
AI workflow that produced it. RGI-01 and RGI-02 remain **OPEN** and release-blocking for real
research data / published metrics until an authorized human authority records a decision in the
unsigned records in §4.

**Policy vs. implemented controls (read first).** P4.3 (PR #177) implemented a fail-closed
**structural/value** floor only. The **verification of authenticity and applicability against a
trusted registry** — proving an authorization/approval actually exists, is genuine, unrevoked,
and scoped to the requested operation — is **policy not yet implemented** and requires an
institutional source of truth. This package proposes that policy; it does not implement it.

| | Implemented now [VF] | Proposed policy (this package) [HD] |
|---|---|---|
| RGI-01 | `cohort_readiness.py` rejects present-but-invalid values (`data_rights=denied`, `retention_status=purged`, unknown) | Registry resolution of `authorization_reference`: authenticity + applicability + revocation + authority |
| RGI-02 | `valid_statistical_signoff` requires `approved is True` + reviewer, rejects `{"approved": false}`/`{"rejected": true}`/bare-id | Authenticated reviewer against an authorized-reviewer registry + scope binding + audit |

---

## RGI-01 — Institutional research authorization (decision-ready proposal)

**Approving authority:** an institutional official with signing authority for data-use (e.g.,
IRB/research-governance office), authenticated.

**Authorization record (required fields):** institutional approving authority; tenant identity
+ institution identity; dataset/cohort ownership & provenance; permitted research purpose(s);
data-use rights (explicit granted state); retention + withdrawal terms; authorization validity
(effective/expiry); evidence-verification reference (resolvable, tamper-evident); revocation
status; auditability (append-only trail); enforcement responsibilities (who enforces at
cohort-build and at use).

**Verification (required controls):**
1. **Existence/authenticity** — resolve `authorization_reference` against a trusted
   registry/ledger; reject if absent or provenance/signature fails.
2. **Applicability** — exact match of tenant, dataset/cohort, and purpose to the requested
   operation; **no normalization** that could alias distinct tenants/institutions.
3. **Temporal/revocation** — within validity window and non-revoked **at check time** (at
   cohort build, not only at grant).
4. **Authority** — approving authority authenticated and authorized for that institution/tenant.
5. **Fail-closed** — any missing/invalid/unresolvable field denies.

**Registry requirement:** **YES** — a **verified authorization registry (or signed-record
ledger) is required before any real research data is used.** Until it exists and is wired into
cohort build, real-data research stays BLOCKED.

**Decision options / risks:** (A, recommended) build the registry + fail-closed resolution;
(B) accept well-formed references without resolution — **rejected for real data** (unverified
authorizations could gate real cohorts); (C) keep real-data research BLOCKED until A.
**Dependencies:** institutional source of truth; canonical granted/active vocabulary; access
control on the registry.

---

## RGI-02 — Authorized scientific reviewer verification (framework)

**Reviewer-approval contract (required fields):** verified reviewer identity (authenticated);
role + institutional authority; scope of approval; dataset + checkpoint association; explicit
approval/rejection semantics; decision timestamp; evidence reference; expiration + revocation;
**separation of duties** (the reviewer is not the data owner/implementer of the same artifact);
audit evidence (append-only); verification of approval **at execution time**.

**Required rule:** approval requires **affirmative approval by an authenticated, authorized
reviewer whose scope covers the tenant, dataset, checkpoint, and intended use**, non-revoked at
check time. **A non-empty `reviewer_id`, or `approved: true` alone, is explicitly
insufficient.** Rejection/revocation blocks use.

**Decision options / risks:** (A, recommended) authorized-reviewer registry + scope-bound,
audited, execution-time-resolved approvals; (B) accept structurally-valid sign-offs without
registry/scope — **rejected for published results**; (C) keep scientific metric publication
BLOCKED until A. **Dependencies:** reviewer registry; audit store; separation-of-duties policy.

---

## 4. Unsigned approval records (to be completed by the authorized authority — DO NOT prepopulate)

### RGI-01 — Institutional research-authorization decision
| Field | Value |
|---|---|
| Approving authority (name / org / role) | |
| Authority authenticated (how) | |
| Scope (tenant / institution / dataset / purpose) | |
| Decision (Approve Option A / Defer / Reject) | |
| Conditions / required registry controls | |
| Effective / expiry | |
| Evidence reference | |
| Date | |
| Signature or authenticated approval reference | |

### RGI-02 — Authorized scientific-reviewer-framework decision
| Field | Value |
|---|---|
| Approving authority (name / org / role) | |
| Authority authenticated (how) | |
| Scope (tenant / institution / dataset / checkpoint / use) | |
| Decision (Approve Option A / Defer / Reject) | |
| Separation-of-duties confirmation | |
| Conditions | |
| Date | |
| Signature or authenticated approval reference | |

*No approval is issued here. These remain OPEN until an authorized institutional authority
records a decision above. The AI workflow cannot and does not approve these.*
