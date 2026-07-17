# Dataset Registry Persistence

## Contract (pre-existing, verified this sprint)

* **Per-image registry rows** (`DatasetRegistryEntry`): permanent LCID,
  dataset/inspection linkage, capture metadata, review + annotation
  state, split assignment, usage rights, PHI verification, training
  eligibility, retention status.
* **First-class immutable versions** (`DatasetVersion`): once frozen,
  any mutation raises `DatasetVersionFrozenError` — enforced in the
  dataset registry service and exercised constantly by the training
  pipeline suites (freezing is a precondition for training eligibility).
* Each version records creation date, Ground Truth version linkage,
  split version, image count, class distribution, content fingerprint
  (SHA-256), approval state, and training eligibility.

## Foundation Sprint 1 status

Objective met by existing enforcement; this sprint added:

* **PostgreSQL evidence** — the dataset governance tables migrated and
  ran under the full suite on PostgreSQL 16.
* **Backup coverage** — registry/version rows are in every database
  backup; exported dataset files belong in governed object storage
  (`object_category="dataset_export"`), which dedupes and hash-verifies
  them (`OBJECT_STORAGE.md`).

## Honest limitations

The only dataset versions ever frozen in this program contain declared
synthetic images. Immutability, lineage, and eligibility gates are
enforced and tested; a real clinical dataset has never yet passed
through them.
