# TRC-001 Authenticated Research Intake API (research-only)

A protected HTTP surface over the existing fail-closed owner-attestation + intake workflow
(`research/lens_vision/scientific_authorization.py`, `research/lens_vision/trc001_intake.py`).
It adds **no** new storage and **no** authorization bypass. Router:
`app/routes/trc001_research.py`, registered in `app/main.py` under `API_PREFIX` (`/api`).

## Authentication (all endpoints)

Every endpoint depends on `require_verified_oidc_context`, which requires a
**cryptographically verified OIDC bearer token** and derives identity only from it:

- Rejected with **401**: missing / malformed `Authorization` header; any token not
  signature-verified against the configured OIDC issuer via JWKS; expired/invalid claims;
  development tokens; application-local `/auth/login` JWTs (no app-signing-secret fallback
  is consulted here); and requests when OIDC is not configured (`OIDC_ISSUER_URL` /
  `OIDC_AUDIENCE` unset).
- Rejected with **403**: demo mode (`DEMO_MODE=1`); an actor who is not an enabled member
  of the token's tenant (`require_enabled_tenant_membership`).
- `actor`, `role`, `tenant_id`, `tenant_name` and `subject` come **only** from the verified
  token + tenant membership — never from request fields.

## Server configuration (never client-supplied)

- `TRC001_DATASET_ID` — research dataset id (default `TRC-001`).
- `TRC001_PRIVATE_KIT_DIR` — absolute path to the approved private kit directory.
- `RETAIN_INSPECTION_IMAGES=1` — enable retention for the isolated research env only.

Clients cannot supply a dataset id, tenant, or file path; any such body fields are ignored.

## Endpoints

### POST `/api/research/trc001/owner-attestation`

Record an owner self-attestation for the configured dataset. Requires an explicit signing
action; the declarant is bound to the verified `actor` + session `subject`.

Request body:
```json
{
  "ownership_asserted": true,
  "permissible_research_use": "independent nonclinical LumenAI research",
  "retention_authorized": true,
  "withdrawal_procedure": "how the owner withdraws; triggers deletion",
  "image_sha256": ["<64-hex>", "<64-hex>"],
  "owner_signing_acknowledged": true
}
```
Validation: `owner_signing_acknowledged`, `ownership_asserted`, `retention_authorized`
must be `true`; `image_sha256` must be exactly two valid SHA-256 hex digests (**422**
otherwise). Stored as a `GovernanceApproval(request_type="research_owner_attestation",
status="approved", requested_by=reviewed_by=<actor>)` whose payload records
`attestation_signed`, `declarant_actor`, `declarant_subject`,
`independent_ownership_verified=false`, `institutional_approved=false`. An immutable audit
event is written **atomically** with the attestation: both are committed in a single
transaction, and if the audit write fails the whole transaction is rolled back (`500`), so
no approved attestation can persist without its required audit evidence.

Response `200`:
```json
{
  "attestation_id": 123, "status": "recorded", "basis": "owner_attested",
  "institutional_approved": false, "independent_ownership_verified": false,
  "dataset_id": "TRC-001", "declarant": "<actor>", "image_sha256": ["…","…"],
  "note": "Owner self-attestation only; not independent verification or institutional approval."
}
```

### POST `/api/research/trc001/owner-attestation/withdraw`

Withdraw **all** of the authenticated owner's currently-approved attestations for the
dataset — bound to the authenticated **actor AND session subject** (not just the most
recent) — so no previously approved attestation remains usable afterwards. `404` if none
active for this actor+subject.

Governed deletion: delete only explicitly attributed TRC-001 images with matching
**tenant, dataset, actor and verified IdP subject**. New image bytes and attribution
are committed together at intake; cross-owner/dataset SHA deduplication cannot
transfer image ownership. Unrelated owners/datasets/subjects and unscoped historical
rows are preserved. Deletion verification counts only this exact scope after commit,
so it must not be interpreted as verification that every historical TRC-001 image
was deleted. Legacy/unattributed records require separate governance review.

Response `200`:
```json
{
  "status": "withdrawn", "attestation_ids": [12, 13, 14], "dataset_id": "TRC-001",
  "retained_images_deleted": [101, 102], "retained_images_remaining": 0,
  "retained_images_deletion_verified": true, "note": "…"
}
```

### POST `/api/research/trc001/intake`

Run the existing hardened runner with `authorization_basis="owner_attested"` using the
verified context, the server-configured dataset, and the server-configured kit directory.
`409` if `TRC001_PRIVATE_KIT_DIR` is not configured. The runner is fail-closed: it
re-resolves the owner attestation (verified session, declarant subject match, exact image
hashes, retention + non-withdrawn), verifies each image's hash/dimensions, retains via
`retain_image`, and verifies retrieval + tenant access.

Response `200` = the intake report (`IntakeReport.to_dict()`), e.g.
`{"status": "INGESTED"|"BLOCKED_AUTHORIZATION"|"BLOCKED_MISSING_INTAKE_KIT"|…,
"imported_count": 0|2, "authorization_basis": "owner_attested", "images": [...]}`.
Both images always remain `ground_truth_status="unknown"`, `baseline_review="pending_review"`,
`research_training_eligible=false`.

## Security limitations / notes

- Owner self-attestation authorizes **research intake/retention of the owner's own
  privately controlled nonclinical assets only**. It is explicitly **not** institutional
  approval, independent ownership verification, or scientific ground truth; it never makes
  an image eligible for verified-normal training, scientific metrics, or clinical use.
- OIDC verification depends on correct deployment config (`OIDC_ISSUER_URL`,
  `OIDC_AUDIENCE`, reachable JWKS). With OIDC unconfigured, all endpoints 401 (fail-closed).
- The subject binding assumes the IdP issues a stable `sub`; attestation-to-session
  identity matching is only as strong as the IdP's subject guarantees.
- Private photographs and credentials are never read, logged, committed, or returned by
  these endpoints; the kit lives only at the server-configured path.

## Schema migration for scoped retention

Alembic revision `e8b2c6d49f10` adds `retained_images.research_dataset_id`,
`research_owner_subject`, and `research_attestation_id`. Apply it to the local
research database before running the updated API. Existing rows receive blank/null
provenance; there is deliberately no automatic ownership backfill.
