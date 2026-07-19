# LPR-DIR-012 — Data Ownership & Authority

For each major data object: system of record (SoR), creating/modifying/approving
authority, deletion & retention rule, versioning & immutability rule, tenant scope,
audit requirement, downstream consumers. One authoritative SoR per object.

| Object | System of Record | Create | Modify | Approve | Delete / Retain | Versioning / Immutability | Tenant scope | Audit |
|---|---|---|---|---|---|---|---|---|
| User | `app.models.user.User` | Admin/registration | Admin/self (limited) | Admin | Soft-deactivate; retain | — | Tenant-linked | Yes |
| Authenticated Principal | derived (`security.principal`) | System (per request) | n/a (ephemeral) | n/a | n/a | n/a | Per request | Yes (auth events) |
| Tenant | tenant model | Platform/bootstrap | Platform admin | Platform | Retain | — | Self | Yes |
| Role / Permission | `TenantMembership` + guards | Admin | Admin | Security approver | Retain | — | Tenant | Yes |
| Instrument / Tray | instrument registry (LCID identity) | Registration | Registration | — | Retain | Identity immutable | Tenant | Yes |
| Inspection / Session | inspection models | Operator | State machine only | Supervisor (disposition) | Retain | State-machine transitions | Tenant | Yes |
| Image | `RetainedImage` | Ingestion | **Immutable bytes** | — | Retain; hash-verified | `image_sha256`; immutable | Tenant | Yes |
| Image Metadata | dataset/registry capture fields | Ingestion | Validation only | — | Retain | Pinned to image | Tenant | Yes |
| Annotation | `Annotation` / `AnnotationVersion` | Annotator | New version only | Reviewer | Retain | **Append-only** | Tenant | Yes |
| Ground Truth | `Annotation` GT (ACTIVE) | Reviewer | Supersede (new version) | GT Approver | Retain | **Immutable; never overwritten** | Tenant | Yes |
| Baseline | `BaselineLibraryEntry` / `BaselineImageLink` | Builder | Supersede | Baseline Approver | Retain | **Append-only lifecycle** | Tenant | Yes |
| Digital Twin | `digital_twin_id` identity (LCID) | Registration | Compose (link), not overwrite | Steward | Retain | Identity immutable; history composed | Tenant | Yes |
| Observation / Finding | decision engine result contract | System (advisory) | Human review | Reviewer | Retain | Human-authoritative | Tenant | Yes |
| Human Review | review/adjudication records | Reviewer | — | Supervisor | Retain | Immutable decision record | Tenant | Yes |
| Evidence Package | compliance evidence bundle | System | — | — | Retain | Checksummed; audit-chain-immutable | Tenant | Yes |
| Audit Event | `enterprise_audit_service` | System | **None (append-only)** | — | Retain | **Hash-chained, tamper-evident** | Tenant | Self |
| Dataset | `DatasetVersion` / `DatasetRegistryEntry` | Curator | New version only *(intended)* | Dataset Approver | Retain | **Immutability NOT enforced — see DA-01** | Tenant | Yes |
| Dataset Manifest | dataset release/build | System | — | Dataset Approver | Retain | Sealed at publication (planned hash) | Tenant | Yes |
| Candidate Model | `ModelRegistryEntry` | ML Eng | New version only | Model Approver | Retain | Frozen artifact + checksum | Tenant | Yes |
| Model Version | `model_version` | ML Eng | — | Model Approver | Retain | Append-only lineage | Tenant | Yes |
| Experiment | training run id + config | ML Eng | Append/amend | Reviewer | Retain | Append-only (first-class record planned) | Tenant | Yes |
| Report | reporting/evidence release | System | — | — | Retain | Generated from governed records | Tenant | Yes |

## Competing-source resolution

* **Image bytes:** `RetainedImage` is the sole SoR; all other modules reference it —
  **no competing store**.
* **Audit:** `enterprise_audit_service` is the single SoR; the deprecated
  `app.audit` shim delegates to it (not a competing SoR, but a second call path to
  retire — B-01).
* **Digital Twin:** identity SoR is LCID (`digital_twin_id`); a governed aggregate
  record is a Future enhancement but does not create a competing identity.
* **Tenant authority:** `TenantMembership` is authoritative; a request header may
  *request* a tenant context but never *grant* authority.

## Findings

* Every major object has **one authoritative SoR** (acceptance criterion met).
* Immutability/append-only is **verified** for image bytes, annotation, GT,
  baseline, model, and audit (tests verify audit + baseline + annotation).
* **DA-01 (MAJOR) — dataset "immutable after approval" is NOT enforced (code-confirmed).**
  A frozen `DatasetVersion` does not lock its entries: `dataset_builder.build_training_dataset`
  writes `DatasetRegistryEntry.split_assignment` and the image-quality path updates
  `image_quality`, **neither checking the parent version's `frozen` flag**. A user can
  therefore change the contents/metadata behind a frozen dataset, invalidating
  reproducibility and model lineage. This corrects the prior "Immutable after
  approval" assertion to a tracked governance gap (see `ARCHITECTURE_RISK_REGISTER.md`).
* Deletion is retention-first (soft-deactivate/retain) across governed objects,
  preserving evidence lineage and immutable history.
