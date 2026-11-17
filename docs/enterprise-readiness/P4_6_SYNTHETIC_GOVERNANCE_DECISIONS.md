# P4.6 — Synthetic-Pilot Governance Decision Records (RGI-01, RGI-02)

**Status:** DECISION-READY PROPOSAL for the LumenAI internal synthetic pilot. **No approval is
created, asserted, or marked approved** by this document or by the AI workflow. RGI-01 (synthetic)
and RGI-02 (internal reviewer framework) remain **OPEN** until an authorized LumenAI authority
records a decision in §C. This adapts `P4_5_INSTITUTIONAL_AUTHORIZATION_APPROVAL.md` to the
synthetic context **without weakening** any control.

**Implemented floor vs. proposed policy (read first).** P4.3 (#177) implemented a fail-closed
**structural/value** floor only (`cohort_readiness.py` value validation; `valid_statistical_signoff`).
Authenticity/applicability **resolution against a trusted source of truth is policy not yet
implemented**. For the synthetic pilot, the "source of truth" is a **LumenAI-controlled** provenance
record rather than an external IRB — but it must still be an authenticated, auditable record, not a
mere well-formed string.

---

## A. RGI-01 (synthetic) — LumenAI-controlled synthetic-data authorization

**Scope change from P4.5:** the approving authority is a **LumenAI data-governance owner** (not an
external IRB), and the permitted purpose is **internal synthetic research only**. Everything else
about the control is preserved.

**Key constraint — do not over-claim.** This record **must not assert that a dataset's synthetic
status is verified** on the basis of a label alone. "Synthetic" is a **content classification that
requires evidence** (generation method, generator identity/version, absence of real-image
derivation, no-PHI check). A dataset whose synthetic status is asserted but not evidenced is
treated as **unverified ⇒ not permitted** (fail-closed). The dataset manifest
(`P4_6_SYNTHETIC_DATASET_MANIFEST.md`) is where that evidence is recorded.

**Synthetic authorization record — required fields:**
LumenAI approving authority (authenticated); research tenant identity; dataset identity + **generation
provenance** (generator/tool, version, seed/config, operator); **content classification**
(synthetic-research) **with supporting evidence**; **ownership** (LumenAI-owned) + **licensing /
use-rights** (LumenAI internal research); permitted research purpose(s); retention + disposal terms;
authorization validity (effective/expiry); **verification-evidence reference** (resolvable,
tamper-evident — links to the manifest entry); revocation status; append-only audit trail;
enforcement responsibility (who enforces at cohort build and at use).

**Verification (required controls — preserved, fail-closed):**
1. **Existence/authenticity** — resolve the dataset's authorization against the **LumenAI provenance
   record**; reject if absent or signature/provenance fails.
2. **Synthetic-status evidence** — the manifest entry must evidence synthetic generation and
   **no real-image derivation / no PHI**; absence ⇒ deny. *A label of "synthetic" is never
   sufficient on its own.*
3. **Applicability** — exact match of research tenant, dataset, and purpose to the requested
   operation; **no normalization** that could alias distinct tenants.
4. **Temporal/revocation** — within validity window and non-revoked **at check time** (at cohort
   build, not only at grant).
5. **Authority** — the LumenAI approving authority is authenticated and authorized for that research
   tenant.
6. **Fail-closed** — any missing/invalid/unresolvable field denies; real-data paths remain BLOCKED.

**Registry requirement for the synthetic pilot:** a **LumenAI-controlled provenance/authorization
record** (signed-record ledger or equivalent) is required before any synthetic dataset is used; it
may be internal, but it must be authenticated and auditable. Until it exists and is wired to cohort
build, synthetic datasets are admitted **only** via the manual, evidenced manifest gate, and the
value-floor in `cohort_readiness.py` stays in force.

**What this does NOT grant:** this record covers **synthetic, LumenAI-owned** data only. It confers
**no** authorization for real patient data or institution-controlled data — that remains the
**external IRB-style** RGI-01 in `P4_5_INSTITUTIONAL_AUTHORIZATION_APPROVAL.md`, still **OPEN**.

## B. RGI-02 — Internal research reviewer framework

**Scope change from P4.5:** reviewers are **internal LumenAI research reviewers** with delegated
authority. Separation of duties and authenticated, scope-bound, execution-time approval are
**preserved**.

**Internal reviewer roles (proposed):**
| Role | Authority (delegated by) | Approval scope | Separation-of-duties rule |
|---|---|---|---|
| Synthetic Data-Governance Owner | Release Authority | RGI-01 synthetic dataset authorization | Not the generator/author of the dataset being authorized |
| Research Methodology Reviewer | Release Authority | RGI-10 metric convention; scientific sign-off for any reported synthetic metric | Must be qualified in anomaly-detection/segmentation metrics; not the implementer of the metric code under review |
| Internal Security Reviewer (non-author) | Release Authority | advisory QA only — **cannot** satisfy SEC-175-01 (see §note) | Must not have authored #171–#178 or prior reviews |
| Release Authority | LumenAI executive sponsor | final pilot GO/HOLD/NO-GO (synthetic scope) | Distinct from the reviewers whose records they confirm |

**Identity verification & delegated authority:** each reviewer's identity is authenticated (e.g.,
SSO-backed account bound to the role), and their authority is **explicitly delegated and recorded**
by the Release Authority; a reviewer acting outside recorded scope is invalid.

**Reviewer-approval contract — required fields (preserved):** verified reviewer identity; role +
delegated authority; scope of approval; dataset + checkpoint association; **explicit
approval/rejection semantics** (not a bare id, not `approved: true` alone); decision timestamp;
evidence reference; expiration + revocation; **separation of duties** (reviewer ≠ owner/implementer
of the same artifact); append-only audit; verification **at execution time**.

**Separation of duties — pilot reality:** if one person would hold multiple roles, that **reduces**
separation of duties and must be recorded as a weakness for the Release Authority to weigh; it is
not silently accepted.

**Security-independence note (unchanged and non-negotiable):** an **internal** security reviewer can
provide useful QA but does **not** satisfy **SEC-175-01**, which requires a verified **non-author**
independent reviewer. The author of #176/#177/#178 and the assurance docs (this AI workflow) cannot
self-approve. SEC-174-02 and SEC-175-01 remain **OPEN**; see
`P4_6_INDEPENDENT_SECURITY_REVIEW_REQUEST.md`.

---

## C. Unsigned decision records (to be completed by the authorized authority — DO NOT prepopulate)

### RGI-01 (synthetic) — LumenAI synthetic-data authorization decision
| Field | Value |
|---|---|
| Approving authority (name / role) | |
| Authority authenticated (how) | |
| Research tenant / dataset / purpose | |
| Synthetic status evidenced? (manifest ref) | |
| Ownership + licensing confirmed (LumenAI internal research) | |
| Decision (Approve synthetic-only / Defer / Reject) | |
| Conditions / required provenance controls | |
| Effective / expiry / retention | |
| Date | |
| Signature or authenticated approval reference | |

### RGI-02 — Internal reviewer-framework decision
| Field | Value |
|---|---|
| Approving authority (name / role) | |
| Authority authenticated (how) | |
| Reviewer roles + delegated scopes | |
| Identity-verification method | |
| Separation-of-duties confirmation | |
| Decision (Approve / Defer / Reject) | |
| Conditions | |
| Date | |
| Signature or authenticated approval reference | |

*No approval is issued here. RGI-01 (synthetic) and RGI-02 remain OPEN until an authorized LumenAI
authority records a decision above. Synthetic status is not treated as verified without manifest
evidence. The external-IRB RGI-01 (real/institutional data) and SEC-174-02/SEC-175-01 remain OPEN
and are not affected by this record.*
