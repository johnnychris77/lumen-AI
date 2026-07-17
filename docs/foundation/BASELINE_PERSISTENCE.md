# Baseline Persistence

## Contract (Atlas, pre-existing; verified this sprint)

Every image-backed baseline is a `BaselineImageLink` carrying: baseline
entry linkage, **approved LCID image references** (never raw unpinned
files), Digital Twin linkage where applicable, anatomy zone, inspection
view, manufacturer/instrument model context, the full approval history
(DRAFT → PENDING_REVIEW → APPROVED → ACTIVE, each transition audited),
and supersession chains (activating a replacement marks the prior link
superseded — never deleted).

Access integrity: `load_and_verify_baseline_bytes` re-verifies SHA-256 on
**every** baseline read and fails closed on mismatch
(`ImageIdentityMismatchError`), logging the access either way.

Legacy metadata-only baselines remain explicitly marked
**`IMAGE_EVIDENCE_MISSING`** (Atlas backfill) — they are never silently
treated as image-backed evidence, and the resolution hierarchy will not
serve them as comparator baselines.

## Foundation Sprint 1 status

Objective met by existing Atlas enforcement; this sprint added
PostgreSQL executed evidence (the five Atlas tables migrated via
`c1d4a7f2b8e6` and ran under the suite on PostgreSQL 16) and
backup/restore coverage (baseline rows restored intact in the DR
exercise).

## Honest limitations

Zero ACTIVE baseline links exist in any persistent environment — ACTIVE
links are created only inside test runs. The persistence layer is ready;
a real baseline library requires real facility images through the Atlas
lifecycle (`docs/controlled-production/FINAL_RELEASE_DECISION.md`, step 2).
