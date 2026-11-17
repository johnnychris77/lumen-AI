# P4.4 — Institutional Governance Decision Package (RGI-01, RGI-02)

**Status:** DECISION PACKAGE for authorized institutional decision-makers. **Nothing here is
an approval.** No institutional authorization or reviewer approval is created, asserted, or
marked approved by this document or by this AI workflow. These remain **OPEN** governance
findings and are release-blocking until an authorized human authority records a disposition.

Context: P4.3 (PR #177) implemented fail-closed **structural** validation for authorization
values (RGI-01) and statistical sign-off (RGI-02). The **verification of authenticity and
applicability against a trusted registry** — i.e., proving an authorization/approval actually
exists, is genuine, unrevoked, and scoped to the requested operation — is the governance layer
specified below. It is deliberately NOT self-certified in code.

---

## RGI-01 — Institutional Authorization

### Proposed authorization record (schema)

| Field | Meaning | Validation requirement |
|---|---|---|
| `institution_id` | Issuing institution identity | Resolves to a known institution in the authorization registry |
| `tenant_id` | Tenant the authorization is granted to | Must equal the requesting operation's tenant (exact match, no normalization) |
| `research_cohort_id` / `dataset_id` | Dataset or cohort the grant covers | Must equal the requested cohort/dataset |
| `permitted_research_purpose` | Allowed purpose(s) | Requested operation's purpose ∈ permitted set |
| `data_rights_status` | Rights disposition | Must be an explicit *granted* state; `denied`/`revoked`/unknown fail closed |
| `retention_authorization` | Retention disposition | Must be an explicit *active/authorized* state; `purged`/`expired` fail closed |
| `authorization_reference` | Stable reference id | Must resolve to a stored, authentic authorization record (not a free-form string) |
| `effective_date` / `expiration_date` | Validity window | `effective ≤ now < expiration` |
| `revocation_status` | Revoked? | Must be non-revoked at check time |
| `evidence_provenance` | Where the evidence came from | A resolvable, tamper-evident evidence reference (e.g., signed document id / ledger entry) |
| `approving_authority` | Who granted it | An authenticated authority with institutional signing authority |

### How the system must verify it (required controls)
1. **Existence & authenticity** — resolve `authorization_reference` against a trusted
   authorization registry/ledger; reject if absent or signature/provenance fails.
2. **Applicability** — exact match of `tenant_id`, `dataset_id`/cohort, and purpose to the
   requested operation; **no string normalization** that could alias distinct tenants.
3. **Temporal & revocation** — within validity window and non-revoked at check time (checked
   at cohort-build time, not only at grant time, so a later revocation blocks use).
4. **Authority** — `approving_authority` authenticated and authorized to grant for that
   institution/tenant.
5. **Fail-closed** — any missing/invalid/unresolvable field denies; never infer approval.

### What P4.3 already enforces (code floor) vs. what this decision adds
- **Enforced now:** rejects present-but-invalid values (`data_rights=denied`,
  `retention_status=purged`, unknown) — a value-level floor, not self-certification.
- **This decision adds:** the **registry/ledger resolution** of `authorization_reference`
  (authenticity + applicability + revocation), which requires an institutional source of truth
  and a canonical vocabulary. That source and vocabulary are an **institutional decision**.

### Decision options
| Option | Description | Risk |
|---|---|---|
| **A (recommended)** | Stand up an authorization registry/ledger; cohort build resolves + validates each reference against it, fail-closed | Build/operate a registry; must be authoritative and access-controlled |
| B | Accept well-formed references now, defer registry resolution | **Unverified authorizations could gate real cohorts** — not acceptable for real data |
| C | Keep research permanently BLOCKED for real data until A exists | Zero risk; no real benchmarking |

**Recommended control:** Option A before any real-image cohort; until then, Option C holds
(all real benchmarks remain BLOCKED). Do **not** adopt B for real data.

---

## RGI-02 — Authorized Scientific Reviewer

### Proposed reviewer-approval contract (schema)

| Field | Meaning | Validation requirement |
|---|---|---|
| `reviewer_id` | Verified reviewer identity | Authenticated identity, resolved in an authorized-reviewer registry |
| `institution_id` / `tenant_scope` | Scope of the reviewer's authority | Must cover the requested tenant/institution |
| `reviewer_role` / `authority` | Role granting sign-off authority | Role authorized to approve scientific adequacy |
| `dataset_scope` / `checkpoint_scope` | What the approval covers | Must match the dataset + checkpoint + intended use being gated |
| `approval_decision` | Explicit decision | Must be an affirmative `approved` (not truthiness; `rejected`/`false` fail) |
| `decision_timestamp` | When decided | Present; within any validity policy |
| `evidence_reference` | Supporting evidence | Resolvable reference to the review record |
| `revocation_status` / `expiration` | Still valid? | Non-revoked, non-expired at check time |
| `audit_history` | Immutable trail | Append-only, hash-chained audit of the decision |

### Required rule
Approval requires **affirmative approval by an authenticated, authorized reviewer whose scope
covers the tenant, dataset, checkpoint, and intended use**, non-revoked at check time. A
non-empty `reviewer_id`, or `approved: true` **alone**, is explicitly **insufficient**.

### What P4.3 already enforces vs. what this decision adds
- **Enforced now (`valid_statistical_signoff`):** requires `approved is True` + a reviewer id,
  and rejects `{"approved": false}` / `{"rejected": true}` / bare-id / revoked — a structural
  floor.
- **This decision adds:** authentication of the reviewer against an **authorized-reviewer
  registry** and binding the approval to the exact tenant/dataset/checkpoint/intended-use, plus
  the immutable audit trail — enforced where those identities are known (the scientific-
  authorization layer).

### Decision options
| Option | Description | Risk |
|---|---|---|
| **A (recommended)** | Authorized-reviewer registry + scope-bound, audited approvals, resolved at use time | Build/operate the registry and audit |
| B | Accept structurally-valid sign-offs without registry/scope binding | A structurally-valid but unauthorized/mis-scoped sign-off could gate metrics |
| C | Keep scientific metric publication BLOCKED until A exists | No scientific publication |

**Recommended control:** Option A before any scientific metric publication; until then Option C
(the metric path labels results non-scientific and `require_scientific` refuses ineligible
checkpoints — see P4.3). Do **not** adopt B for published results.

---

## Governance status (unchanged)
- **RGI-01, RGI-02** — **OPEN**, release-blocking for real data / published metrics until an
  authorized institutional decision records Option A (or an explicit, documented risk
  acceptance).
- No approvals are created here. This AI workflow cannot and does not approve these.
