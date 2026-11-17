# Stage 6D — Real Instrument Evidence Pilot

Status: **research-only.** Reuses Stage 4–6C components (no new AI framework). Extends
Stage 6C (PR #169). No clinical model promotion, technician-facing recommendation,
instrument-release decision, prospective clinical study, or deployment.

> **Decision: `BLOCKED_REAL_IMAGE_BENCHMARK`.** No authorized real surgical-instrument/
> borescope images and no license-and-source-verified scientific checkpoint exist in
> this environment. Per the stop condition, Stage 6D delivers only the **minimal safety
> corrections** (final authorization/ground-truth hardening + the real governed
> ingestion hand-off) plus an **operational acquisition checklist**, and stops. No new
> synthetic performance milestone was created.

## Separation of states

| State | Stage 6D status |
|---|---|
| **Implemented software (tested)** | ✅ Authenticated-context-bound approvals; use-scope/authority checks; dataset-specific authorization; record-backed laboratory confirmation; immutable audit; real ingestion hand-off. |
| **Executed model experiments** | ✅ PaDiM + PatchCore through the governed localizer (coverage 1.0, deterministic) — synthetic / random-weight: pipeline verification only. |
| **Independent scientific validation** | ❌ None — `BLOCKED_REAL_IMAGE_BENCHMARK`. |
| **Prospective clinical authorization** | ❌ None. |

## §2 — Final authorization & ground-truth hardening (minimal safety corrections)

`scientific_authorization.py`, `research_acquisition.py`, `review_record.py`:

1. **Authenticated request context** — approvals bind to the trusted `AuthContext`
   principal (`actor` + `role`); a caller cannot name an approver. A context whose role
   does not match the recorded role, or whose actor has no role record, is an
   **impersonation** error (`authorize_scientific_actor`).
2. **Checkpoint evidence** — license/source approvals must be `approved`, carry the
   applicable **use scope** (`scientific_research`), and be reviewed by an authenticated
   approver with authority.
3. **Cohort-specific authorization** — research consent + institutional authorization
   resolve for the **specific dataset** (dataset-scoped `GovernanceApproval`s), not an
   unrelated tenant-wide consent alone.
4. **Laboratory confirmation** — resolved from an independently-reviewed, approved
   `VeritasEvidenceProvenanceRecord` whose `file_hash` matches the exact image (and
   instrument); the arbitrary `lab_confirmed` boolean was **removed** from
   `build_review_record`.
5. **Immutable audit** — every resolution writes a hash-chained enterprise audit event
   (`record_enterprise_audit_event`).

Regression tests (`test_stage6c_authorization.py`, `test_stage6d_hardening.py`):
impersonation, forged/unapproved/unauthenticated approvals, wrong use scope,
dataset-specific authorization, withdrawn + cross-tenant consent, unreviewed/cross-tenant/
wrong-image laboratory confirmation, and the ingestion hash gate.

## §3–§4 — Controlled cohort + real governed ingestion

`acquire_research_cohort(..., import_images=True)` resolves dataset-specific authorization,
validates each image against the acquisition contract, **verifies supplied bytes' SHA-256
against the registered hash**, and performs the smallest authorized hand-off to the
existing `image_retention_service.retain_image` (EXIF-stripped, deduped, access-controlled
— **no new store, no bypass**). It records the **actual imported count** and resolved
`RetainedImage` storage ids. With no authorized bytes present here, `imported = 0`
honestly. The controlled real-instrument cohort manifest schema (instrument/specimen/
session/batch/modality/rights/hash/annotation-version/review-status, plus `specimen_category`
and `image_bytes`) is defined and validated. Visually normal appearance is never treated
as verified cleanliness; research-only specimens stay segregated from clinical.

## §5–§6 — Models & evaluation

The governed runner gates the real-image benchmark on `assess_scientific_readiness`
(now bound to the authenticated context). All record-backed checks are BLOCKED here
(data authorization, authenticated statistical sign-off, scientific checkpoint —
`smoke_stub` rejected) → **`BLOCKED_REAL_IMAGE_BENCHMARK`**. Random-weight execution
(coverage 1.0, deterministic) is pipeline verification only. No clinical-performance or
independent-validation claim is made.

## External dependencies preventing the pilot (blocker report)

1. Institutional/ethics authorization + dataset-scoped data-use agreement (recorded).
2. Research-use consent (tenant + dataset-scoped) recorded and live.
3. Controlled research-only specimens across the required categories + borescope lumen
   captures, segregated from clinical.
4. Independently-reviewed laboratory reference evidence linked to each specimen/image.
5. A licensed, digest-verified pretrained checkpoint with recorded license + source
   approvals (scientific use scope).
6. Authenticated statistical reviewer + approved statistical protocol.

## Independent scientific-evaluation readiness recommendation

The **software gates and the governed ingestion path are ready**: once items 1–6 exist as
records and authorized images are supplied, `acquire_research_cohort(import_images=True)`
will ingest them through the existing retention service, `assess_scientific_readiness`
will resolve, and the governed PaDiM/PatchCore runner can execute a **protocol-approved
feasibility evaluation** (physical-specimen grouping, frozen calibration thresholds,
modality separation, real denominators + uncertainty + false negatives + confounders).
Recommendation: proceed to **assemble the record-backed authorizations and the first
small controlled cohort** per `OPERATIONAL_ACQUISITION_CHECKLIST.md`; a feasibility cohort
is **not** a substitute for an independent validation cohort, and no clinical claim
follows from it. Stage 6D is authenticated readiness infrastructure — **not** scientific
or clinical validation — and is not validated by its passing tests.
