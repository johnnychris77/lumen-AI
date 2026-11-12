# Stage 4 — Pre-Merge Safety Hardening

Focused hardening of the Stage 4 provenance work before merge (PR #162, commit
`f9edf93`). Preserves the Stage 4 architecture and all previously passing
functionality; adds **no** new clinical detectors, model architectures, or
commercial features. Not merged, not deployed.

## Security findings addressed

### 1. Live serving could be driven by a trained Candidate alone
`live_inference_adapter.load_active_model` gated only on
`candidate_stage >= Candidate`, ignoring every human-led governance signal — so a
model that was merely trained and marked Candidate would serve live clinical
inference with no clinical review, model approval, or deployment authorization.

- **Fix:** serving now additionally requires `clinical_review_status == approved`,
  `approval_status in {pilot, validated}`, and
  `deployment_status in {shadow, deployed}`, returning a new
  `HEALTH_NOT_AUTHORIZED` state otherwise. The stage gate is kept as
  defense-in-depth.
- Both registration pathways reviewed: Project Lens (`register_lens_model`) and
  Genesis (`run_full_candidate_pipeline`) both set `approval_status=experimental`
  and never set the review/deployment signals, so neither can auto-authorize
  serving.

### 2. Cross-tenant `RetainedImage` access
`register_image` accepted `retained_image_id` + `image_sha256` without verifying
tenant ownership or hash identity, and candidate-training image sourcing queried
`RetainedImage` by id with **no tenant filter**.

- **Fix:** `verify_retained_image_for_registration` (called from the
  dataset-registration route and unknown-finding promotion) requires the
  referenced image to exist, belong to the authenticated tenant (cross-tenant →
  404, existence never confirmed), and match the declared SHA-256 (mismatch →
  409). Candidate-training sourcing is now tenant-scoped so another tenant's
  bytes can never enter a training run.

### 3. Provenance approval accepted weak inputs
`set_provenance_classification` had an optional `tenant_id`, trusted an arbitrary
`actor_role` string, and accepted blank source/rights evidence.

- **Fix:** `tenant_id` is now mandatory and must match the entry; approval
  requires a non-empty authenticated actor and an authorized governance role;
  clinical (`real_clinical`) approval requires verified supporting source **and**
  rights evidence (new `ProvenanceEvidenceError`) rather than arbitrary/blank
  strings.

### 4. Split grouping could produce misleading independent validation
Grouping picked a single key (serial → inspection → per-sample), so same-specimen
images under different inspections, same-session images, and repeated images
could straddle the train/test boundary; an identity-less cohort trivially
reported "leakage-free."

- **Fix:** `dataset_split` now union-finds over all strong identities —
  instrument serial (when enabled), inspection, **specimen**, **session**, and
  identical-image SHA — so no such set straddles the split. It emits
  `grouping_reliable` / `independent_validation_reliable` (+ `grouping_is_reliable()`
  helper and `ungrouped_sample_count`) so a cohort lacking real grouping identity
  is flagged rather than passing as clean independent validation.

## Migration verification (executed)

`backend/scripts/verify_provenance_migration_c3e7a9b14d20.py` runs the **actual**
`upgrade()`/`downgrade()` against a representative pre-Stage-4
`dataset_registry_entries` table populated with legacy rows: **18/18 checks** —

- guard no-op when the table is absent;
- upgrade adds all 9 columns + 2 indexes;
- fail-closed backfill (`legacy_unverified` / `pending`) with **no legacy row
  relabelled clinical**;
- legacy data preserved; second upgrade idempotent;
- downgrade drops the columns/indexes and preserves all legacy data.

This closes the previously-noted limitation that the add-columns/backfill/rollback
path had not been executed end-to-end (the Postgres CI already exercises the
standalone `upgrade head → downgrade -1 → upgrade head` guard path).

Run it from a directory other than `backend/` (so the local `backend/alembic`
package does not shadow the installed alembic distribution):

```bash
python /home/user/lumen-AI/backend/scripts/verify_provenance_migration_c3e7a9b14d20.py
```

## Test evidence (executed)

- `pytest tests/test_stage4_safety_hardening.py -q` → **22 passed** (new
  regression suite: serving-authorization bypass, cross-tenant/SHA registration,
  provenance authority + evidence, specimen/session/repeat-image split grouping +
  reliability flag).
- `pytest tests/ -q` → **3886 passed, 2 skipped**.
- `ruff check app tests` → **All checks passed**.
- Migration script → **18/18**.
- CI on `f9edf93` → green (no third-party check suite running or failing).

## Stage 4 completion — three integration findings resolved

A second pass resolved the three outstanding integration findings before Stage 5.

### F1 — Shadow inference separated from clinically actionable inference
`deployment_status` is now mode-specific in `live_inference_adapter`:
`"deployed"` authorizes technician-facing, clinically actionable output; `"shadow"`
authorizes **silent evaluation only**. The actionable `predict()` path
(`require_actionable=True`, the default) refuses a shadow-only model with the new
`HEALTH_SHADOW_ONLY` state, returning a non-actionable `ai_unavailable` contract.
A dedicated `shadow_evaluate()` loads shadow-or-deployed models for logging via
`shadow_mode.record_shadow_prediction` and never returns an `analysis_status` or
`observation` block (`clinical_recommendation_shown=False`). So a shadow-authorized
model can never surface a clinical recommendation to a technician.

### F2 — Provenance approval tied to verifiable authorized records
`set_provenance_classification` no longer trusts arbitrary strings or caller-supplied
roles:
- **Actor authority** is resolved from the authoritative role store
  (`UserRoleAssignment`), not the passed `actor_role`; a claim that disagrees with
  the authenticated role is rejected, and the audit records the authenticated role.
- **Source evidence** (`source_id`) must resolve to a governed
  `VeritasEvidenceProvenanceRecord` owned by the tenant.
- **Data-rights evidence** (`rights_evidence_ref`) must resolve to a granted,
  non-withdrawn `ConsentRecord` of a data-use type, owned by the tenant.

### F3 — Grouping identities propagated; promotion gated on reliable grouping
Specimen id, instrument identity, inspection (capture session), and image SHA-256 are
carried from the governed registry through `compute_training_eligibility` →
`_to_split_sample` → `dataset_split`. `run_lens_training` now surfaces
`grouping_reliable` and requires **both** verified provenance **and** reliable
grouping for `clinical_promotion_eligible`, so a cohort whose independent validation
cannot be trusted (samples lacking real grouping identity) is never clinically
promotable (`provenance_clinical_promotion_eligible` records the provenance-only
value separately for transparency).

### Added tests (executed)
`tests/test_stage4_safety_hardening.py` now holds **32** tests (the original 22 plus
10 for F1–F3): shadow-only not actionable / shadow-eval loads / deployed stays
actionable; approval rejects unresolvable source, unresolvable/withdrawn rights,
an actor with no authenticated role, and a mismatched role claim; split identities
propagate and the lens run's clinical promotion is blocked without reliable grouping.

## Remaining limitations

- SHA-256 *cryptographic* re-hash of bytes is not enforced at registration (the
  existing suite uses opaque, non-cryptographic hash identifiers pervasively);
  the control enforced is tenant ownership + consistency between the declared
  hash and the retained image's recorded hash. Byte-level hashing remains at the
  retention/ingest layer.
- The `grouping_reliable` signal is surfaced by `dataset_split`; it is not yet
  made a hard training-abort in every pipeline (a non-breaking diagnostic this
  pass), so callers can decide policy.
- A provenance approval UI/route remains out of scope (service + authority +
  evidence + audit are in place).
- Migration add/backfill/rollback was verified on SQLite 3.45; column types are
  portable and server-defaults are plain strings, so the Postgres
  runtime-bootstrap path matches, but a Postgres end-to-end run was not available
  in this environment.
- There is no per-image **capture-session** column on the governed registry/retained
  image; an inspection bounds a capture session in this schema, so `inspection_id`
  carries the session-grouping role. A `session_id` is forwarded if ever present but
  is not fabricated.
- `grouping_reliable` now hard-gates the lens run's `clinical_promotion_eligible`;
  other training pipelines surface the diagnostic but do not yet hard-gate on it.
- A provenance approval **UI/route** remains out of scope; the service enforces the
  verifiable-records contract and is ready for a route to pass authenticated context.
