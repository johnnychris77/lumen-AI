"""TRC-001 — authenticated, research-only intake API (owner attestation + ingestion).

A protected HTTP surface over the existing fail-closed owner-attestation and intake
workflow (`research/lens_vision/scientific_authorization.py`,
`research/lens_vision/trc001_intake.py`). It adds NO new storage and NO authorization
bypass — it is a thin, verified entry point:

* **Authentication (requirements 1-2):** every action requires a cryptographically
  verified OIDC bearer token. Missing / expired / invalid / development / demo /
  application-local JWT credentials are rejected. Actor, role, subject and tenant are
  derived ONLY from the verified token + authorized tenant membership — never from
  arbitrary request fields.
* **Owner attestation (requirements 3-4):** records an owner self-attestation, bound to
  the verified declarant (actor + session subject), with an explicit signing action,
  ownership assertion, permissible research use, retention authorization, withdrawal
  procedure and the exact two image SHA-256 hashes. It is recorded accurately as
  owner-attested — never as independent verification or institutional approval.
* **Intake (requirements 5-7):** invokes the existing hardened runner with
  ``authorization_basis="owner_attested"`` using the verified context, restricted to the
  server-configured research dataset and approved private kit location (never a
  client-supplied path). Ground-truth stays unknown, pending review, training-ineligible.

The research stack is imported lazily inside handlers so importing ``app`` never pulls the
research modules at startup.
"""
from __future__ import annotations

import json
import os

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.context import AuthContext, build_oidc_auth_context
from app.auth.jwks_validator import (
    JWKSSignatureValidationError,
    validate_jwt_signature_with_jwks,
)
from app.auth.jwt_validator import (
    JWTValidationError,
    map_claims_to_auth_context_payload,
    validate_jwt_claims,
)
from app.auth.tenant_membership import require_enabled_tenant_membership
from app.deps import get_db
from app.enterprise_auth import (
    _extract_bearer_token,
    get_oidc_audience,
    get_oidc_issuer,
    is_demo_mode,
)
from app.models.governance_approval import GovernanceApproval
from app.models.retained_image import RetainedImage
from app.services.enterprise_audit_service import record_enterprise_audit_event

router = APIRouter(tags=["trc001-research"])

# request_type string shared with research.lens_vision.scientific_authorization
# (kept as a local literal so this app module does not import the research stack to read
# a constant). It MUST match REQ_OWNER_ATTESTATION there.
REQ_OWNER_ATTESTATION = "research_owner_attestation"
_APPROVED = "approved"
_WITHDRAWN = "withdrawn"
_HEX = set("0123456789abcdef")


def trc001_dataset_id() -> str:
    """Server-configured TRC-001 research dataset id (never client-supplied)."""
    return os.getenv("TRC001_DATASET_ID", "TRC-001").strip() or "TRC-001"


def trc001_kit_dir() -> str:
    """Server-configured approved private kit location (never client-supplied)."""
    return os.getenv("TRC001_PRIVATE_KIT_DIR", "").strip()


def require_verified_oidc_context(
    request: Request, db: Session = Depends(get_db),
) -> AuthContext:
    """Dependency: require a cryptographically verified OIDC bearer token and derive the
    research operator identity from it + authorized tenant membership. Fail-closed.

    Rejects (401/403): demo mode, unconfigured OIDC, missing/expired/invalid tokens, and
    development / application-local JWTs (no app-signing-secret fallback is consulted —
    only an OIDC-issuer-signed token verified via JWKS is accepted)."""
    if is_demo_mode():
        raise HTTPException(status_code=403, detail="Demo mode is not permitted for TRC-001 research intake.")
    issuer = get_oidc_issuer()
    audience = get_oidc_audience()
    if not issuer or not audience:
        raise HTTPException(
            status_code=401,
            detail="Verified OIDC authentication is required for TRC-001 research intake (OIDC not configured).",
        )
    token = _extract_bearer_token(request)  # 401 when missing/malformed Authorization header
    try:
        claims = validate_jwt_signature_with_jwks(token)
        validated = validate_jwt_claims(claims, expected_issuer=issuer, expected_audience=audience)
    except (JWKSSignatureValidationError, JWTValidationError) as exc:
        raise HTTPException(status_code=401, detail=f"Invalid or unverified OIDC token: {exc}") from exc
    payload = map_claims_to_auth_context_payload(validated)
    if not str(payload.get("subject") or "").strip():
        raise HTTPException(status_code=401, detail="Verified token is missing a subject ('sub') claim.")
    # Authorized tenant membership (raises 403 when the actor is not an enabled member).
    require_enabled_tenant_membership(db, tenant_id=payload["tenant_id"], user_email=payload["actor"])
    return build_oidc_auth_context(
        actor=payload["actor"], role=payload["role"], tenant_id=payload["tenant_id"],
        tenant_name=payload["tenant_name"], subject=payload["subject"],
        issuer=payload["issuer"], raw_claims=payload["raw_claims"],
    )


class OwnerAttestationRequest(BaseModel):
    """Owner self-attestation body. Identity is NOT taken from here — only the verified
    token supplies actor/subject/tenant. These fields carry only the owner's declaration."""

    ownership_asserted: bool = Field(..., description="Owner asserts private ownership/use rights.")
    permissible_research_use: str = Field(..., min_length=1)
    retention_authorized: bool = Field(..., description="Owner authorizes private research retention.")
    withdrawal_procedure: str = Field(..., min_length=1)
    image_sha256: list[str] = Field(..., min_length=2, max_length=2)
    owner_signing_acknowledged: bool = Field(..., description="Explicit owner signing action.")


def _normalize_hashes(values: list[str]) -> list[str]:
    cleaned = sorted({str(h).strip().lower() for h in values if str(h).strip()})
    if len(cleaned) != 2 or not all(len(h) == 64 and set(h) <= _HEX for h in cleaned):
        raise HTTPException(status_code=422, detail="image_sha256 must be exactly two valid SHA-256 hex digests.")
    return cleaned


@router.post("/research/trc001/owner-attestation")
def record_owner_attestation(
    body: OwnerAttestationRequest,
    auth: AuthContext = Depends(require_verified_oidc_context),
    db: Session = Depends(get_db),
):
    """Record an owner self-attestation for the configured TRC-001 dataset (requirement 3-4).

    Requires an explicit owner signing action; binds the declarant to the verified
    actor + session subject; records ownership + permissible use + retention + withdrawal +
    the two image hashes. Recorded accurately as owner-attested, NOT independent or
    institutional. Response never implies verification beyond the owner's own declaration."""
    if not body.owner_signing_acknowledged:
        raise HTTPException(status_code=422, detail="An explicit owner signing action is required.")
    if not body.ownership_asserted:
        raise HTTPException(status_code=422, detail="ownership_asserted must be true.")
    if not body.retention_authorized:
        raise HTTPException(status_code=422, detail="retention_authorized must be true.")
    hashes = _normalize_hashes(body.image_sha256)
    dataset_id = trc001_dataset_id()
    payload = {
        "ownership_asserted": True,
        "permissible_research_use": body.permissible_research_use.strip(),
        "retention_authorized": True,
        "withdrawal_procedure": body.withdrawal_procedure.strip(),
        "attestation_signed": True,              # explicit owner signing action
        "declarant_actor": auth.actor,           # from verified token, not request body
        "declarant_subject": auth.subject,       # from verified session, not request body
        "independent_ownership_verified": False,  # owner self-attestation is NOT independent
        "institutional_approved": False,
        "image_sha256": hashes,
    }
    row = GovernanceApproval(
        tenant_id=auth.tenant_id, tenant_name=auth.tenant_name,
        request_type=REQ_OWNER_ATTESTATION, target_resource="dataset",
        target_resource_id=dataset_id, requested_by=auth.actor, status=_APPROVED,
        reviewed_by=auth.actor, requested_payload=json.dumps(payload),
    )
    # Atomic: the approved attestation and its audit event persist together or not at all.
    # The audit event is written with commit=False in the SAME transaction, then a single
    # commit flushes both. If audit construction/write fails, the whole transaction is
    # rolled back so no approved record can persist without its required audit evidence.
    db.add(row)
    try:
        db.flush()  # assign row.id without committing
        record_enterprise_audit_event(
            db, action_type="trc001_owner_attestation_recorded", resource_type="research_dataset",
            resource_id=dataset_id, actor=auth.actor, actor_role=auth.role, tenant_id=auth.tenant_id,
            status="success",
            details={"attestation_id": row.id, "basis": "owner_attested",
                     "independent_ownership_verified": False, "institutional_approved": False},
            auth_context=auth, commit=False,
        )
        db.commit()
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Owner attestation not recorded: audit evidence could not be written (atomic rollback).",
        ) from exc
    return {
        "attestation_id": row.id, "status": "recorded", "basis": "owner_attested",
        "institutional_approved": False, "independent_ownership_verified": False,
        "dataset_id": dataset_id, "declarant": auth.actor, "image_sha256": hashes,
        "note": "Owner self-attestation only; not independent verification or institutional approval.",
    }


@router.post("/research/trc001/owner-attestation/withdraw")
def withdraw_owner_attestation(
    auth: AuthContext = Depends(require_verified_oidc_context),
    db: Session = Depends(get_db),
):
    """Withdraw the authenticated owner's attestation(s) for the dataset and run the
    governed deletion of any retained images that were ingested under them.

    * **Revocation (requirement 1):** ALL currently-approved attestations bound to the
      authenticated actor AND session subject are set to ``withdrawn`` — not just the most
      recent — so no previously approved attestation remains usable afterwards.
    * **Governed deletion (requirement 3):** deletes only images explicitly attributed
      to the matching tenant, dataset, owner actor, and verified session subject.
      Other owners, datasets and legacy unscoped images are preserved.
      Deletion is re-queried after commit before it is reported verified.
    """
    from research.lens_vision.trc001_intake import TRC001_INSTRUMENT_ID  # noqa: PLC0415

    dataset_id = trc001_dataset_id()
    candidates = (
        db.query(GovernanceApproval)
        .filter(
            GovernanceApproval.tenant_id == auth.tenant_id,
            GovernanceApproval.request_type == REQ_OWNER_ATTESTATION,
            GovernanceApproval.target_resource_id == dataset_id,
            GovernanceApproval.status == _APPROVED,
            GovernanceApproval.reviewed_by == auth.actor,
        )
        .all()
    )
    # Revocation is bound to the authenticated actor AND session subject.
    withdrawn_ids: list[int] = []
    for rec in candidates:
        try:
            payload = json.loads(rec.requested_payload or "{}")
        except (ValueError, TypeError):
            payload = {}
        if str(payload.get("declarant_actor") or "") != auth.actor:
            continue
        if str(payload.get("declarant_subject") or "") != str(auth.subject or ""):
            continue
        rec.status = _WITHDRAWN
        withdrawn_ids.append(rec.id)
    if not withdrawn_ids:
        raise HTTPException(
            status_code=404,
            detail="No active owner attestation to withdraw for this authenticated actor + subject.",
        )

    # Delete only explicitly attributed images in the requesting owner's scope.
    # Historical rows missing provenance require review, NOT guessed ownership.
    def _retained_query():
        return db.query(RetainedImage).filter(
            RetainedImage.tenant_id == auth.tenant_id,
            RetainedImage.source == "trc001_research_intake",
            RetainedImage.instrument_type == TRC001_INSTRUMENT_ID,
            RetainedImage.uploaded_by == auth.actor,
            RetainedImage.research_dataset_id == dataset_id,
            RetainedImage.research_owner_subject == auth.subject,
        )

    deleted_ids = [r.id for r in _retained_query().all()]
    try:
        for r in _retained_query().all():
            db.delete(r)
        db.flush()
        record_enterprise_audit_event(
            db, action_type="trc001_owner_attestation_withdrawn", resource_type="research_dataset",
            resource_id=dataset_id, actor=auth.actor, actor_role=auth.role, tenant_id=auth.tenant_id,
            status="success",
            details={"attestation_ids": withdrawn_ids, "retained_images_deleted": deleted_ids},
            auth_context=auth, commit=False,
        )
        db.commit()
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Withdrawal not completed: revocation + deletion could not be committed (atomic rollback).",
        ) from exc

    # Verify deletion AFTER commit before claiming it.
    remaining = _retained_query().count()
    deletion_verified = remaining == 0
    return {
        "status": "withdrawn",
        "attestation_ids": withdrawn_ids,
        "dataset_id": dataset_id,
        "retained_images_deleted": deleted_ids,
        "retained_images_remaining": remaining,
        "retained_images_deletion_verified": deletion_verified,
        "note": (
            "Attestation(s) revoked; images attributed to the exact tenant, dataset, "
            "actor and subject deleted and verified. Other or legacy unscoped rows "
            "are not included." if deletion_verified else
            "Attestation(s) revoked; scoped deletion could NOT be verified — "
            "manual governed remediation required before any further intake."
        ),
    }


@router.post("/research/trc001/intake")
def run_trc001_intake_action(
    auth: AuthContext = Depends(require_verified_oidc_context),
    db: Session = Depends(get_db),
):
    """Run the existing fail-closed TRC-001 intake with the verified context (requirement
    5-7). Dataset and private kit location are SERVER-configured — never client-supplied.
    Authorization is resolved by the runner via ``authorization_basis="owner_attested"``;
    this endpoint does not weaken it."""
    kit_dir = trc001_kit_dir()
    if not kit_dir:
        raise HTTPException(
            status_code=409,
            detail="TRC-001 private kit location is not configured on the server (TRC001_PRIVATE_KIT_DIR).",
        )
    from research.lens_vision.trc001_intake import run_trc001_intake  # noqa: PLC0415

    report = run_trc001_intake(
        db, kit_dir=kit_dir, tenant_id=auth.tenant_id, dataset_id=trc001_dataset_id(),
        auth=auth, authorization_basis="owner_attested",
    )
    return report.to_dict()
