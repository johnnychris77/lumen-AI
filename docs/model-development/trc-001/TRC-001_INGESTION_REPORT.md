# TRC-001 — First Real Instrument Image Ingestion (redacted report)

Status: **BLOCKED** — research-only engineering/provenance exercise (not model training
or clinical validation). Reuses the existing `image_retention_service` / `RetainedImage`
governance; no new image store was built. No instrument-specific data, private intake
ZIP, original images, or retained bytes are committed to git.

## Outcome in this environment

A corrected kit (`TRC-001-Codex-compatible-private-kit.zip`) was expected for this run.
A full filesystem search confirmed **no such kit (or any TRC-001 intake kit / manifest /
operator JPEG) is present** in this environment, and **no authorization governance
records** exist for a TRC-001 dataset. Both prerequisites are therefore unresolved, so —
per the stop condition — **no bytes were loaded or retained and no storage IDs were
created or invented. Successful ingestion was not simulated.**

Determination: **`BLOCKED_AUTHORIZATION`.** With no trusted, authenticated,
tenant-matched actor to supply (and no kit or governance records), the hardened runner
fails closed at the first authorization gate:

- `BLOCKED_AUTHORIZATION` — no trusted authenticated actor; and the required governance
  records (below) do not exist. `auth=None` / untrusted / cross-tenant contexts are refused.
- `BLOCKED_MISSING_INTAKE_KIT` — the manifest + operator JPEG bytes were not supplied
  (reached only once an authenticated actor is present).

Capturing a photograph personally does **not** establish institutional or research-use
permission; the runner fails closed on that basis. Governance approvals were **not**
fabricated and records were **not** created merely to force a successful run.

## Runner hardening applied before ingestion (§2)

`run_trc001_intake` was hardened so that, even when a kit arrives, ingestion is gated by
real authorization and the bytes are validated fail-closed:

1. **Trusted, authenticated, tenant-matched actor required.** The runner calls
   `authorize_tenant_actor` first; `auth=None`, an object that is not an `AuthContext`, an
   actor with no `UserRoleAssignment` record, or a cross-tenant actor is refused with
   `BLOCKED_AUTHORIZATION` **before the kit or manifest is read**.
2. **Path-traversal / absolute-path rejection.** Each manifest `filename` is resolved
   through `_safe_kit_path`, which rejects absolute paths, `~` expansion, NUL bytes, and
   any path that `realpath`-escapes the private kit directory. Only files that resolve
   **inside** the kit directory are opened.
3. **Actual dimension validation.** When the manifest declares `width`/`height` (or a
   `dimensions`/`size` pair), the **decoded** JPEG size must match exactly or the image is
   rejected and never retained.
4. **Retention authorized by an approval, not `consent=True` alone.** A dataset-scoped
   `research_retention_authorization` `GovernanceApproval` (reviewed by an authenticated
   approver) must resolve before any `retain_image` call; absent it the run is
   `BLOCKED_AUTHORIZATION`. `consent=True` remains only a service precondition.
5. **Explicit tenant-access authorization test.** Ingestion success requires an explicit
   predicate — authenticated actor tenant == ingestion tenant == stored row tenant — and
   does **not** rely on a storage query returning a row. The cross-tenant visibility query
   is kept only as a secondary defence-in-depth isolation check.

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

The §2 hardening above is covered by negative regression tests (10 total in
`tests/test_trc001_ingestion.py`): `auth=None` refused, cross-tenant actor refused,
retention authorization required (data-authorization + consent alone is insufficient),
a path-traversal manifest filename rejected, and a declared/decoded dimension mismatch
rejected — in every case nothing is retained and no IDs are invented. The authorized
end-to-end test additionally asserts the explicit `tenant_access_authorized` predicate.

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
