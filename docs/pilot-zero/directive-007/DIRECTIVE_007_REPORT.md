# LPZ-DIR-007 — Directive Report: Baseline Governance & Digital Twin Framework

## Executive summary

Directive 007 establishes the **governance framework** for Digital Twins, baseline
images, baseline evolution, and reference management — how LumenAI creates,
approves, versions, maintains, and retires trusted references for reusable
surgical instruments. It delivers ten standards (Digital Twin model, baseline
classification, creation workflow, approval, versioning, comparison, lifecycle,
Digital Twin governance, reference architecture, and this report), each grounded
in the baseline/twin code already present in the repository so the framework is
auditable against reality.

Every baseline used in future computer-vision workflows will have documented
**provenance, review history, approval records, and lifecycle governance**, and
will be built **only on human-approved (ACTIVE) Ground Truth** — no baseline from
unreviewed images. This directive is **governance and documentation only**: no new
AI functionality, no model training, no hospital deployment workflow, and no
unsupported clinical/regulatory claim. No application code was modified.

## Digital Twin model

`DIGITAL_TWIN_MODEL.md` defines the logical twin: immutable Digital Twin/Instrument
UUID (UDI-derived, never fabricated), manufacturer/model/family/type, serial/tray/
lumen/anatomical-region context, and linked inspection/image/annotation/Ground
Truth/baseline history, plus lifecycle status, version, audit history, and a
**reserved** relationship slot for future AI outputs (not populated here).

## Baseline categories

`BASELINE_CLASSIFICATION_STANDARD.md` defines Manufacturer Reference, Pilot Zero
Candidate, Approved Development, Engineering, Research, Site Approved, Retired, and
Historical baselines — each with purpose, approval authority, permitted uses,
restrictions, and lifecycle. Only Approved/Published categories serve as live
references; candidates and research baselines never enter the production
comparison path; site baselines are tenant-scoped.

## Approval workflow

`BASELINE_CREATION_WORKFLOW.md` and `BASELINE_APPROVAL_STANDARD.md` define:
Image Acquisition → Annotation → Ground Truth → Engineering Review → Clinical
Review (if applicable) → Baseline Candidate → Approval → Digital Twin Association →
Reference Publication. A baseline record carries UUID, source images, Ground Truth
version, reviewer, approver, timestamp, confidence, status, evidence references,
version, and approval rationale. **No baseline from unreviewed images**; approval
is evidence-gated and subject to separation of duties.

## Versioning strategy

`BASELINE_VERSIONING_STANDARD.md` requires immutable UUID, major/minor versions,
parent linkage, effective/superseded dates, mandatory revision reason, evidence
references, approval history, and retirement status. **No baseline is
overwritten**; historical versions remain retrievable, and each inspection records
the exact baseline **version** it compared against.

## Lifecycle

`BASELINE_LIFECYCLE_STANDARD.md` defines Draft → Candidate → Under Review →
Approved → Published → Superseded → Retired → Archived, with entry/exit criteria,
allowed actions, and required approvals per state — mapping onto the implemented
`BASELINE_IMAGE_STATES` validated state machine (`DRAFT → PENDING_REVIEW →
APPROVED → ACTIVE → {SUSPENDED, SUPERSEDED} → ARCHIVED`, plus `REJECTED`). Only
Published baselines are live references; nothing leaves Archived.

## Governance

`DIGITAL_TWIN_GOVERNANCE.md` defines ownership (tenant-scoped, program-owned
standard, stewarded records), update-by-composition (never overwrite), revision
authority, and the twin's relationships to inspection history, Ground Truth,
baseline versions, future AI outputs (reserved), audit history, and evidence
packages — with tenant isolation, no PHI, and AI-as-advisory invariants.

## Reference architecture

`REFERENCE_ARCHITECTURE.md` shows the end-to-end chain Instrument → Inspection →
Image → Metadata → Annotation → Ground Truth → Baseline → Digital Twin → Evidence
Library → Future AI Models → Future Clinical Decision Support, with per-layer
provenance guarantees and fail-closed/immutability/separation-of-duties/audit
cross-cutting rules. The two bottom layers are **reserved** and out of scope here.

## Validation procedures (test requirements) & expected outcomes

Documentation-only directive — these are the validation procedures a future
authorized implementation change must satisfy. No tests were added or modified.

| # | Validates | Procedure (future) | Expected outcome |
|---|---|---|---|
| 1 | Baseline creation | Create a baseline from images lacking ACTIVE Ground Truth. | Blocked/rejected — no baseline from unreviewed images (fail-closed). |
| 2 | Version creation | Revise an approved baseline (new reference image). | New immutable version (major bump), parent link, reason, effective date; prior version marked Superseded, retained. |
| 3 | Approval workflow | Approve a candidate as approver who authored the annotation/review. | Rejected by separation-of-duties; approval requires an independent approver + evidence + rationale. |
| 4 | Digital Twin linkage | Associate an approved baseline with an instrument twin. | Twin references the baseline version; association is attributable and audited. |
| 5 | Baseline retirement | Retire a Published baseline. | State → Retired/Archived; not selectable for new comparisons; retained for history + reason. |
| 6 | Reference retrieval | Request the current reference for a twin. | Returns the current ACTIVE/Published baseline version only; never a Draft/Retired one. |
| 7 | Audit logging | Perform each lifecycle transition. | Every transition emits an attributable audit event; audit completeness = 100%. |
| 8 | Historical version access | Retrieve a superseded baseline version. | Prior version retrievable, immutable, with effective/superseded dates and lineage. |

## Existing-system gap analysis & migration plan

The repository already implements much of this: models `BaselineLibraryEntry`,
`BaselineImageLink`, `BaselineImageReview`, `BaselineSet`/`BaselineSetMember`,
`BaselineComparisonAccessLog`; a validated lifecycle state machine
(`BASELINE_IMAGE_STATES`); services `baseline_image_library_service`,
`baseline_comparison_service`, `baseline_comparison_scoring_service`,
`baseline_compatibility_service`, `image_similarity_service`, and the
Veritas/Sentinel/Apollo/Oracle twin & baseline services; and Digital Twin identity
via `ml.lcid_service`.

| Gap | Current state | Migration step (future) | Priority |
|---|---|---|---|
| No aggregate Digital Twin record | Twin is a reused `digital_twin_id` string | Add a governed twin aggregate (status, version, reference lists) composed from existing sources | Medium |
| GT-gated baseline creation | Link references GT eligibility, not enforced as precondition | Enforce ACTIVE-GT precondition at baseline approval | High |
| Separation of duties in code | Role-based, not author/reviewer-identity based | Block approver == annotator/reviewer of same evidence | High |
| Baseline **version** in comparison records | Comparisons record baseline id | Pin baseline version into each comparison result | High |
| Category vocabulary | `baseline_type` = manufacturer/vendor/network_contributed | Extend to the 8 governed categories; map deprecated→Retired/Historical | Medium |
| Explicit Candidate & Retired states | Folded into DRAFT / supersession | Surface Candidate and first-class Retired actions | Low |
| Major/minor version semantics | Single `baseline_version` string | Formalize major/minor + mandatory revision reason | Medium |

**No migration step is executed under Directive 007.** Each is a candidate for a
future directive that explicitly authorizes code changes. Per the directive's
constraint, **no new comparison algorithm was implemented** — the existing
comparison machinery is governed, not replaced.

## Risks

| Risk | Impact | Mitigation |
|---|---|---|
| Baseline built on unreviewed images | Untrustworthy reference | GT-gated creation; fail-closed (planned enforcement) |
| Baseline overwrite | Loss of lineage/reproducibility | Append-only versioning; historical retrieval |
| Comparison confident on poor identity/coverage/quality | False assurance | Comparison standard's safety invariant; escalation criteria |
| Self-approval | Weak baseline | Separation-of-duties (matrix + planned code enforcement) |
| Twin identity fabricated | Provenance breach | UDI/barcode-derived identity, never invented |
| Cross-tenant baseline leakage | Isolation breach | Tenant-scoped; audited sharing only |
| Scope creep into AI training/CDS | Violates directive & freeze | Reserved layers; non-goals restated in every doc |

## Dependencies

* **Program:** Directives 001, 002, 004, 005, 006 (all complete).
* **System:** the baseline/twin models, lifecycle state machine, comparison and
  twin services, and LCID identity above.
* **Personnel:** engineering/clinical reviewers, Baseline Approvers, twin stewards
  (Lab Lead), quality auditors, with separation of duties.

## Acceptance criteria

All ten deliverables exist under `docs/pilot-zero/directive-007/`, are internally
consistent and vendor-neutral, make no unsupported clinical/regulatory claim,
enforce "no baseline from unreviewed images" and baseline immutability, keep AI
advisory/reserved, and include validation procedures with expected outcomes plus
an honest gap analysis of the existing system. **Met.**

## Exit criteria (to operate under this framework — future work)

1. GT-gated baseline creation and separation-of-duties enforced in code.
2. Baseline **version** pinned into every comparison and Digital Twin reference.
3. Governed Digital Twin aggregate (status/version/reference lists) available.
4. Validation procedures 1–8 implemented and passing on a clean database.
5. Category vocabulary extended; Candidate/Retired states surfaced.

## Completion status

**LPZ-DIR-007 Baseline Governance & Digital Twin framework: COMPLETE
(documented).** The framework is defined, grounded in the existing system, and
accompanied by a migration plan and validation procedures. **Code enforcement of
the migration steps is NOT started (by design — deferred to a future authorized
directive).** No AI was created or trained, no comparison algorithm was added, and
no unsupported clinical or regulatory claim is made.
