# LPZ-DIR-007 — Digital Twin Governance

**Purpose:** define how Digital Twins are owned, updated, and related to the rest
of the evidence chain, so that the trusted reference record for each instrument
has clear authority and a complete, auditable set of relationships.

Guardrail: the Digital Twin is a governed data construct. No AI is trained and no
clinical/regulatory claim is made by maintaining a twin.

## Ownership

* **Program ownership:** the Digital Twin Program (this directive's authority)
  owns the twin standard and governance.
* **Record ownership:** each twin is **tenant-scoped**; a tenant owns its
  instrument twins. Cross-tenant visibility requires an explicit, audited sharing
  action, and shared identities are anonymized where required by platform
  security rules.
* **Steward:** a designated Lab Lead / Baseline Approver stewards a twin's
  baseline associations and lifecycle status.

## Updates

* A twin is **updated by composition, not overwrite**: new inspections,
  annotations, Ground Truth, and baseline versions are **linked**, extending the
  twin's history without mutating prior records.
* Identity fields (Digital Twin UUID, instrument identity) are **immutable**.
* Lifecycle status and current-baseline pointer change through attributable,
  audited actions.

## Revision authority

| Action | Authority |
|---|---|
| Create a twin (from a real instrument identity) | Registration / Lab Lead |
| Associate an approved baseline | Baseline Approver / Steward |
| Change current-baseline pointer (supersession) | Baseline Approver |
| Change lifecycle status (e.g., retire a twin) | Program Administrator / Steward |
| Read/audit | Quality Auditor (read-only) |

No single actor both creates the evidence and unilaterally approves its inclusion
in the twin — separation of duties from Directive 006 and this directive applies.

## Relationships

### Relationship to inspection history
Every inspection of the instrument references the twin; the twin accumulates
(links to) its inspection history. Inspections are never rewritten into the twin;
they are referenced.

### Relationship to Ground Truth
The twin links the **ACTIVE** Ground Truth records for its images. Superseded GT
remains in history; the twin points at current GT while retaining lineage.

### Relationship to baseline versions
The twin references its approved baselines and records which **version** is
current. Historical baseline versions remain associated for audit and to
reproduce past comparisons.

### Relationship to future AI outputs
A **reserved** relationship slot links future model outputs to the twin. It is
**not populated under this directive** (no AI trained/added). When populated later,
AI outputs are stored as advisory, attributable records — never as Ground Truth
and never as autonomous dispositions.

### Relationship to audit history
Every change to the twin (association, supersession, status change) emits an
attributable audit event. The twin's full history is reconstructable.

### Relationship to evidence packages
The twin is the anchor from which an **evidence package** (images + metadata +
annotations + GT + baseline versions + audit) can be assembled for a given
instrument and point in time — supporting reproducibility and review.

## Invariants

* **Immutable identity, composed history.** Identity never changes; history grows
  by linkage.
* **Tenant isolation.** Twins do not leak across tenants without an audited
  sharing action.
* **No PHI.** Instruments only.
* **Auditable.** Every relationship change is attributable and logged.
* **AI is advisory.** Future AI outputs relate to the twin as support, never as
  the twin's source of truth.

## Governance note (existing system)

Today the twin is an identity (`digital_twin_id`) consistently reused across
annotations, LCID dataset entries, and the baseline image library, plus
specialist twin services (Apollo/Oracle/Sentinel/`digital_quality_twin`) that read
it. Governance additions recorded for a future authorized change: introduce a
governed aggregate twin record carrying lifecycle status, version, and explicit
reference lists composed from these existing sources; and formalize the reserved
future-AI-output relationship. No code is changed under this directive.
