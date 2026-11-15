# TRC-001 — First Real Instrument Image Ingestion (redacted report)

Status: **BLOCKED** — research-only engineering/provenance exercise (not model training
or clinical validation). Reuses the existing `image_retention_service` / `RetainedImage`
governance; no new image store was built. No instrument-specific data, private intake
ZIP, original images, or retained bytes are committed to git.

## Outcome in this environment

The private intake kit is now present and **both operator photographs verify exactly
against their manifest** (SHA-256, byte size, and 1152×1536 dimensions all match; both
decode as valid JPEG). The borescope image is a display photograph, not a raw export.

Real ingestion nonetheless **cannot proceed in this disposable cloud environment**:

- **`BLOCKED_RESEARCH_DATABASE`** — there is no authorized, isolated research PostgreSQL
  bound here (`DATABASE_URL` unset; nothing on :5432; no admin/secrets-manager handoff).
  Provisioning the operator's research database must happen on their authorized local
  machine, not in a disposable cloud coding environment, and must never target production.
- Consequently there is no governance store in which a genuine authenticated owner could
  record an authorization, so ingestion is not attempted and no IDs are invented.

A new **owner-attested authorization basis** was added to the runner (see below) so that,
once the local research database and a genuine authenticated owner declaration exist, the
owner's privately controlled nonclinical assets can be ingested — without ever implying
institutional approval or scientific ground truth.

### Owner-attested authorization basis (privately controlled nonclinical assets)

`run_trc001_intake(..., authorization_basis="owner_attested")` resolves authorization from
an approved, non-withdrawn `GovernanceApproval(request_type="research_owner_attestation")`
authored by the **authenticated owner**, covering **exactly** the two image SHA-256s and
asserting ownership + permissible research use + retention + a withdrawal procedure
(`resolve_owner_attestation`). It is deliberately distinct from institutional approval
(`institutional_approved=False`) and from independent scientific verification
(`scientifically_verified=False`); ground truth stays `unknown`, baseline `pending_review`,
and both images remain training-ineligible. A manually constructed `AuthContext` with no
backing `UserRoleAssignment` cannot establish authority. Negative tests cover forged/
non-`AuthContext` contexts, cross-tenant actors, missing attestation, withdrawn
attestation, unauthorized retention, and image-hash mismatch.

### Verified-session hardening for owner self-attestation (Step 1)

Because, for owner self-attestation, the actor is the sole authority, the attestation path
additionally requires a VERIFIED authenticated session (`authorize_verified_owner`):

- `auth_provider` must be a verified provider (`oidc`) with a non-empty session `subject`;
  a locally-constructed / dev `AuthContext` — even one naming an **existing legitimate
  owner account** — is refused.
- The attestation must record a genuine signing action (`attestation_signed`), name the
  declarant (`declarant_actor`) with `requested_by == reviewed_by == authenticated actor`,
  and bind the declarant's session `subject`; at ingestion the presented session subject
  must match (a forged context with the right username but a different subject is refused).
- Unsupported `authorization_basis` values are rejected, never silently treated as
  institutional. Institutional approval rules are unchanged for institution-controlled
  datasets. Owner self-attestation is explicitly **not** independent ownership
  verification (`independent_ownership_verified = False`).

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
| Original file SHA-256 | `98ab44ed…fb09` (verified vs manifest) | `a8e35f5e…567f` (verified vs manifest) |
| Image dimensions | 1152×1536 (verified) | 1152×1536 (verified) |
| Authorization outcome | **pending** (see blocker below) | **pending** (see blocker below) |
| Ingestion attempted | **no** (no bound research DB) | **no** (no bound research DB) |
| Ingestion successful | **no** | **no** |
| RetainedImage ID | **none** (not created) | **none** (not created) |
| Original vs stored checksum | n/a (not retained) | n/a (not retained) |
| Retrieval verification | n/a (not retained) | n/a (not retained) |
| Tenant isolation result | n/a (not retained) | n/a (not retained) |
| ground_truth_status | **unknown** | **unknown** |
| Baseline review | **pending_review** | **pending_review** |
| Research-training eligibility | **false** | **false** |

Both images link to the same physical trocar (`TRC-001`) with distinct image identities
and modalities. Neither is auto-labelled normal/clean/corroded/contaminated.

## Remaining prerequisites before ingestion

The kit is present and verified. Ingestion is blocked only on environment + genuine
authorization (none fabricated):

1. An isolated research database bound via `DATABASE_URL`, provisioned on the operator's
   authorized local machine (not a disposable cloud env, not production), with migrations
   applied and `RETAIN_INSPECTION_IMAGES` enabled for that env only.
2. A verifiably authenticated operator/tenant in the identity system (a verified session,
   not a constructed `AuthContext`).
3. One of the two authorization bases for dataset `TRC-001`:
   - **owner-attested** (privately controlled nonclinical asset): an approved,
     non-withdrawn `GovernanceApproval(request_type = research_owner_attestation)` signed by
     the authenticated owner, covering exactly the two image SHA-256s and asserting
     ownership + permissible research use + retention + withdrawal; **or**
   - **institutional**: data-authorization + research-use consent (`GovernanceApproval`s) +
     tenant `ConsentRecord` + a `research_retention_authorization` approval.

Owner-attested authorization is never institutional approval, independent ownership
verification, or scientific ground truth; if policy requires independent review for a use,
that stays a separate unmet gate (`BLOCKED_REVIEW`).

## What WAS verified (ingestion pathway, real services)

- **Kit bytes:** both operator JPEGs verify against the manifest — SHA-256, byte size, and
  1152×1536 dimensions all match; both decode as valid JPEG.
- **Ingestion machinery:** proven end-to-end with **real, non-mocked** integration tests
  (`tests/test_trc001_ingestion.py`, **22 tests**) using **locally-generated JPEG bytes**
  (not the operator photos): a genuine `retain_image` call persists a `RetainedImage` row
  on the real (SQLite) DB; stored bytes are retrieved, decode cleanly, and hash-match
  (accounting for EXIF stripping); the row is tenant-isolated.
- **Negative/safeguard coverage:** `auth=None`; non-`AuthContext`; cross-tenant actor;
  path-traversal manifest filename; dimension mismatch; retention-authorization required
  (institutional); and, for the owner-attested basis — unverified/dev context naming an
  existing owner, forged existing-owner with a wrong session subject, unsigned attestation,
  third-party (non-declarant) record, withdrawn attestation, retention not authorized,
  image-hash mismatch, and an unsupported `authorization_basis`. In every blocked case
  nothing is retained and no IDs are invented. An `unknown`-ground-truth image is rejected
  by the verified-normal-only fitting gate.

## Research safeguards (both images)

- ground_truth_status = **unknown**; baseline review = **pending_review**;
  research-training eligibility = **false**.
- Excluded from verified-normal PaDiM/PatchCore fitting and normal calibration cohorts
  (the experiment raises `NormalOnlyViolation` for any non-`verified_normal` sample).
- Not added to manufacturer-approved baseline libraries, scientific accuracy reporting,
  clinical model serving, or instrument-release decisions.
- The borescope image is recorded as a **display photograph**, never claimed to be a raw
  borescope export.

## To complete TRC-001 (operator steps, on the authorized local machine)

On the operator's local machine (never committing the kit or bytes), provision the
isolated research PostgreSQL, bind `DATABASE_URL`, `alembic upgrade head`, enable
`RETAIN_INSPECTION_IMAGES`, record a genuine authenticated owner attestation for the two
verified hashes, then run:

```
run_trc001_intake(db, kit_dir="<private kit path>", tenant_id="<authenticated tenant>",
                  dataset_id="<TRC-001 dataset>", auth=<verified operator AuthContext>,
                  authorization_basis="owner_attested")
```

Success criterion is met only when both photographs are **authorized, hash-verified,
genuinely retained and retrievable** — reported with their real `RetainedImage` IDs.
Until then this report stands as the explicit blocker (`BLOCKED_LOCAL_EXECUTION` /
`BLOCKED_RESEARCH_DATABASE` in a cloud environment).
