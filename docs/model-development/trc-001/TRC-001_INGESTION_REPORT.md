# TRC-001 — First Real Instrument Image Ingestion (redacted report)

Status: **BLOCKED** — research-only engineering/provenance exercise (not model training
or clinical validation). Reuses the existing `image_retention_service` / `RetainedImage`
governance; no new image store was built. No instrument-specific data, private intake
ZIP, original images, or retained bytes are committed to git.

## Outcome in this environment

The private intake kit **`TRC-001-private-intake-kit.zip` is not present** in this
environment, and **no authorization governance records** exist for a TRC-001 dataset.
Both prerequisites are therefore unresolved, so — per the stop condition — **no bytes
were loaded or retained and no storage IDs were created or invented.**

- `BLOCKED_MISSING_INTAKE_KIT` — the manifest + operator JPEG bytes were not supplied.
- `BLOCKED_AUTHORIZATION` — the required governance records (below) do not exist.

Capturing a photograph personally does **not** establish institutional or research-use
permission; the runner fails closed on that basis.

## Per-image status (actual)

| Field | TRC-001-EXT-001 | TRC-001-BORE-001 |
|---|---|---|
| Modality | external_camera | borescope (display photograph, **not** a raw export) |
| Source | operator captured | operator captured |
| Reference status | — | provisional baseline (**not** a manufacturer baseline) |
| Original file SHA-256 | not available (kit absent) | not available (kit absent) |
| Image dimensions | not available | not available |
| Authorization outcome | **BLOCKED** | **BLOCKED** |
| Ingestion attempted | **no** | **no** |
| Ingestion successful | **no** | **no** |
| RetainedImage ID | **none** (not created) | **none** (not created) |
| Original vs stored checksum | n/a | n/a |
| Retrieval verification | n/a | n/a |
| Tenant isolation result | n/a | n/a |
| ground_truth_status | **unknown** | **unknown** |
| Baseline review | **pending_review** | **pending_review** |
| Research-training eligibility | **false** | **false** |

Both images link to the same physical trocar (`TRC-001`) with distinct image identities
and modalities. Neither is auto-labelled normal/clean/corroded/contaminated.

## Missing documentation (required before ingestion)

1. The private intake kit: `TRC-001-private-intake-kit.zip` (provisional manifest + the
   two operator JPEG files + their SHA-256 hashes).
2. Institutional data-authorization record (`GovernanceApproval`,
   `request_type = research_data_authorization`, `target_resource_id = <TRC-001 dataset>`,
   `status = approved`, authenticated reviewer).
3. Dataset-scoped research-use consent record (`GovernanceApproval`,
   `request_type = research_use_consent`, same dataset id).
4. Tenant research-use `ConsentRecord` (granted, not withdrawn).
5. Image-use rights + instrument-source permission for the operator-captured trocar.
6. Research retention authorization for the isolated research environment
   (`RETAIN_INSPECTION_IMAGES` enabled there).

## What WAS verified (ingestion pathway, real services)

The ingestion machinery was proven end-to-end with a **real, non-mocked** integration
test (`tests/test_trc001_ingestion.py`) using **locally-generated JPEG bytes** (not the
operator photos): a genuine `retain_image` call persists a `RetainedImage` row on the real
(SQLite) DB, the stored bytes are retrieved and decode cleanly, the stored SHA-256 matches
the stored bytes (accounting for EXIF stripping), and the row is isolated to its owning
tenant. The test also confirms the runner returns `BLOCKED_MISSING_INTAKE_KIT` /
`BLOCKED_AUTHORIZATION` and retains nothing when prerequisites are absent, and that an
`unknown`-ground-truth image is rejected by the verified-normal-only fitting gate.

## Research safeguards (both images)

- ground_truth_status = **unknown**; baseline review = **pending_review**;
  research-training eligibility = **false**.
- Excluded from verified-normal PaDiM/PatchCore fitting and normal calibration cohorts
  (the experiment raises `NormalOnlyViolation` for any non-`verified_normal` sample).
- Not added to manufacturer-approved baseline libraries, scientific accuracy reporting,
  clinical model serving, or instrument-release decisions.
- The borescope image is recorded as a **display photograph**, never claimed to be a raw
  borescope export.

## To complete TRC-001 (operator steps)

Supply the private intake kit to the isolated research environment, create records 2–6
above, then run (never committing the kit or bytes):

```
run_trc001_intake(db, kit_dir="<private kit path>", tenant_id="<tenant>",
                  dataset_id="<TRC-001 dataset>", auth=<authenticated approver context>)
```

Success criterion is met only when both photographs are **authorized, hash-verified,
genuinely retained and retrievable** — reported with their real `RetainedImage` IDs.
Until then this report stands as the explicit blocker.
