# Model Registry Persistence

## What exists (built across Lens/Genesis/Shadow sprints; verified here)

`ModelRegistryEntry` (`model_registry_entries`) stores, per trained model
version: `model_id` + `model_version`, artifact path + **SHA-256
checksum** (verified at every load by the live inference adapter — a
mismatch disables serving), architecture description, preprocessing and
calibration references, `dataset_version` / `dataset_version_id` (frozen
dataset linkage), Ground Truth provenance, training configuration
fingerprint, evaluation/calibration/error-analysis report linkage, Model
Card fields, approval state, and the 5-stage promotion ladder
(`Experimental → Candidate → Validated Candidate → Pilot → Production`)
with evidence-gated transitions in
`app/services/ml/candidate_promotion.py`.

## New this sprint

1. **Single-active-Production invariant** (Foundation Objective 4: "Only
   one active production model is permitted"): `promote_candidate` now
   refuses to promote a model to `Production` while another registry row
   holds that stage — the incumbent must first be explicitly rolled back
   (an audited human decision). Verified by
   `tests/test_gpae_foundation.py::TestSingleActiveProductionModel`.
2. **PostgreSQL evidence**: the registry schema (including the Lens
   artifact-integrity columns) migrated and exercised on PostgreSQL 16.
3. **Backup coverage**: registry rows travel with database backups;
   artifact files travel in the `model_artifacts.tar.gz` component of
   `scripts/gpae_backup_restore.py` (executed — see
   `DISASTER_RECOVERY.md`, which also demonstrated checksum detection of
   a corrupted artifact and its restoration from backup).

## Rollback

`candidate_stage` transitions are ordinary registry updates guarded by
the promotion service and audited; historical predictions retain the
`model.version` they were produced with (Sprint-2 result contract), so a
rollback never rewrites history.

## Honest limitations

* No model has ever reached `Candidate` or beyond in any persistent
  environment — the only trained model is `Experimental` (synthetic
  data). The registry and its invariants are ready; the governed evidence
  to populate them with a production model does not yet exist.
* Registry rows in this repository's environments live in dev/test
  databases; a standing registry requires the managed PostgreSQL
  deployment described in `POSTGRESQL_MIGRATION.md`.
