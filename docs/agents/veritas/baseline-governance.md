# Project Veritas — Baseline Governance Rules

LumenAI AI Specialist, Sections 3 & 13.

## Three pre-existing, divergent vocabularies

- `BaselineLibraryEntry.approval_status`: pending/approved/deprecated
- `EnterpriseVendorBaselineSubscription`: `baseline_status`/`approval_status`
  with its own `_APPROVED_VALUES` set
- `Inspection.baseline_status`: not_checked/approved_baseline_found/
  pending_baseline_review/no_approved_baseline/baseline_not_available/approved

None matches this brief's seven-status vocabulary (draft / pending_review /
approved / conditionally_approved / superseded / rejected / archived).
Rather than rewrite any of those tables, `VeritasBaselineGovernanceAction`
is a new, **append-only** governance-action log keyed to
`(baseline_source_type, baseline_source_id)`.

## Effective status = latest action

A baseline's canonical Veritas status is the `resulting_status` of its
latest governance action — `veritas_baseline_governance_service.
effective_status`. With no governance history yet, a real, already-approved
baseline (i.e. one `resolve_baseline` returned) is treated as `approved`
rather than defaulting to `pending_review`, since it already passed the
real approval filter; a baseline with no history at all otherwise defaults
to `pending_review`.

## Only approved/conditionally-approved baselines score

`is_usable_for_scoring(status)` gates every downstream readiness
calculation — a `draft`, `pending_review`, `superseded`, `rejected`, or
`archived` baseline never drives a clinical recommendation.

## Every action is its own audit event

`VeritasBaselineGovernanceAction` rows are never edited or deleted — each
`approve`/`conditionally_approve`/`reject`/`supersede`/`archive`/
`request_additional_images` call creates a new row, satisfying "every
action requires an audit event" by construction.

## Baseline Review Workspace (Section 13)

`compare_candidates` lets an authorized reviewer compare multiple baseline
candidates' governance history side by side before approving one.

## API

```
POST /api/veritas/baselines/{source_type}/{source_id}/governance-action
GET  /api/veritas/baselines/{source_type}/{source_id}/governance-history
POST /api/veritas/baselines/compare
```

All governance-action writes are leadership-only (`admin`/`spd_manager`) —
a technician (`operator` role) may never alter baseline governance status.
