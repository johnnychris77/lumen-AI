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
