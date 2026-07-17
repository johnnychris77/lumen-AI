# Ground Truth Versioning

## Contract (pre-existing, verified this sprint)

Ground Truth is **append-only**. The annotation database
(`app/models/annotation_database.py` +
`annotation_ground_truth_service`) produces GT through the double-blind
workflow (primary annotation → independent secondary review →
adjudication where needed → ACTIVE Ground Truth), and every change
creates a **new version row** — GT v1 → v2 → v3 — with the full history
retained. Nothing overwrites an ACTIVE GT record; supersession is a new
row plus a status transition, both audited.

Model training records the GT version it consumed
(`ModelRegistryEntry` provenance fields), so any model output can be
traced to the exact GT snapshot behind it.

## Foundation Sprint 1 status

Objective met by existing enforcement (annotation-database suite covers
version creation, supersession, and history retention). This sprint
added PostgreSQL executed evidence (tables migrated and suite-exercised
on PostgreSQL 16) and backup/restore coverage: GT rows were part of the
database that was backed up, dropped, and restored intact in the DR
exercise (`DISASTER_RECOVERY.md`).

## Honest limitations

All GT ever produced in this program's environments annotates declared
synthetic images. The versioning machinery is real and tested; real
clinical Ground Truth does not yet exist (see
`docs/model-development/TRAINING_ELIGIBILITY_REPORT.md`).
