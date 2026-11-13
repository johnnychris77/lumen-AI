"""Stage 6C — authenticated scientific-approval resolution (research-only).

Stage 6B accepted caller-supplied strings/dicts/booleans as proof of scientific
readiness (an ``approver_id`` string, ``license_evidence_ref`` strings, a
``statistical_reviewer_signoff`` dict). Stage 6C closes that gap: every approval is
**resolved against existing authoritative records** and is **fail-closed**. No
caller-supplied flag is ever accepted as sufficient proof.

Reused authoritative records (no new governance platform is created):

* ``UserRoleAssignment`` — authenticated identity + role of an approver/reviewer.
* ``GovernanceApproval`` — a reviewed, status-tracked approval record (license,
  source, institutional data authorization, statistical protocol sign-off).
* ``ConsentRecord`` — research-use permission (granted, not withdrawn).

This module performs authorization resolution only; it never ingests data, downloads
weights, promotes a model, or makes a clinical decision.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.governance_approval import GovernanceApproval
from app.models.user_role_assignment import UserRoleAssignment
from research.lens_vision.governance import research_use_scope_authorized

# Roles (from the existing role vocabulary) authorized to approve scientific use.
SCIENTIFIC_APPROVER_ROLES = frozenset({"admin", "quality_director"})
STATISTICAL_REVIEWER_ROLES = frozenset({"admin", "quality_director"})

# GovernanceApproval.request_type values this module resolves.
REQ_CHECKPOINT_LICENSE = "scientific_checkpoint_license"
REQ_CHECKPOINT_SOURCE = "scientific_checkpoint_source"
REQ_DATA_AUTHORIZATION = "research_data_authorization"
REQ_STATISTICAL_PROTOCOL = "statistical_protocol_approval"

_APPROVED = "approved"


class ScientificAuthorizationError(PermissionError):
    """A scientific-approval check could not be resolved against authoritative
    records (forged/absent approver, missing/withdrawn evidence or permission)."""


def resolve_role(db: Session, username: str, *, allowed_roles: frozenset) -> str:
    """Resolve an authenticated user's role from ``UserRoleAssignment``. Fail-closed:
    raises if the user is unknown or holds no allowed role. A username string alone is
    never proof — it must resolve to a real assignment."""
    uname = str(username or "").strip()
    if not uname:
        raise ScientificAuthorizationError("No approver identity supplied.")
    row = db.query(UserRoleAssignment).filter(UserRoleAssignment.username == uname).first()
    if row is None:
        raise ScientificAuthorizationError(f"Approver '{uname}' is not an authenticated identity.")
    if row.role not in allowed_roles:
        raise ScientificAuthorizationError(
            f"Approver '{uname}' holds role '{row.role}', not one of {sorted(allowed_roles)}."
        )
    return row.role


def resolve_governance_approval(
    db: Session, *, tenant_id: str, request_type: str, target_resource_id: str,
) -> GovernanceApproval:
    """Resolve an approved ``GovernanceApproval`` record, verifying its reviewer is an
    authenticated approver. Fail-closed: raises when no approved record exists or its
    reviewer cannot be resolved. An arbitrary reference string is never accepted."""
    rid = str(target_resource_id or "").strip()
    if not rid:
        raise ScientificAuthorizationError(f"No {request_type} evidence record id supplied.")
    rec = (
        db.query(GovernanceApproval)
        .filter(
            GovernanceApproval.tenant_id == tenant_id,
            GovernanceApproval.request_type == request_type,
            GovernanceApproval.target_resource_id == rid,
            GovernanceApproval.status == _APPROVED,
        )
        .order_by(GovernanceApproval.id.desc())
        .first()
    )
    if rec is None:
        raise ScientificAuthorizationError(
            f"No approved {request_type} record '{rid}' exists for tenant '{tenant_id}'."
        )
    # The record's reviewer must itself be an authenticated approver (not just text).
    resolve_role(db, rec.reviewed_by, allowed_roles=SCIENTIFIC_APPROVER_ROLES)
    return rec


def verify_data_authorization(db: Session, *, tenant_id: str, user_email: str, dataset_id: str) -> None:
    """Fail-closed institutional + research-use authorization for a research dataset:
    an approved institutional-data-authorization ``GovernanceApproval`` AND a granted,
    non-withdrawn research-use ``ConsentRecord`` (reused from Stage 5A governance). A
    withdrawn consent fails here."""
    resolve_governance_approval(
        db, tenant_id=tenant_id, request_type=REQ_DATA_AUTHORIZATION, target_resource_id=dataset_id,
    )
    if not research_use_scope_authorized(db, tenant_id):
        raise ScientificAuthorizationError(
            f"Tenant '{tenant_id}' has no granted, non-withdrawn research-use consent."
        )


def verify_statistical_signoff(
    db: Session, *, reviewer_username: str, tenant_id: str, protocol_id: str,
) -> dict:
    """Resolve a statistical reviewer's authenticated role AND an approved statistical-
    protocol ``GovernanceApproval``. Returns a VERIFIED sign-off dict (resolved from
    records, never the caller's). Fail-closed."""
    role = resolve_role(db, reviewer_username, allowed_roles=STATISTICAL_REVIEWER_ROLES)
    rec = resolve_governance_approval(
        db, tenant_id=tenant_id, request_type=REQ_STATISTICAL_PROTOCOL, target_resource_id=protocol_id,
    )
    if (rec.reviewed_by or "").strip() != str(reviewer_username).strip():
        raise ScientificAuthorizationError(
            "Statistical protocol was not reviewed by the named statistical reviewer."
        )
    return {
        "reviewer": reviewer_username, "reviewer_role": role, "protocol_id": protocol_id,
        "governance_approval_id": rec.id, "resolved": True,
    }


def register_scientific_checkpoint(
    db: Session, checkpoint_id: str, *, file_path: str, architecture: str, tenant_id: str,
    approver_username: str, license_approval_id: str, source_approval_id: str,
    license: str = "", source_url: str = "", description: str = "", preprocessing: dict | None = None,
):
    """Register a checkpoint for SCIENTIFIC use only after resolving the approver's role
    and the license + source ``GovernanceApproval`` records against the database. The
    checkpoint's evidence refs are the resolved record ids, not caller strings.
    Fail-closed — any unresolved check raises before anything is registered."""
    from research.lens_vision import checkpoint as ckpt  # noqa: PLC0415

    resolve_role(db, approver_username, allowed_roles=SCIENTIFIC_APPROVER_ROLES)
    lic = resolve_governance_approval(
        db, tenant_id=tenant_id, request_type=REQ_CHECKPOINT_LICENSE, target_resource_id=license_approval_id,
    )
    src = resolve_governance_approval(
        db, tenant_id=tenant_id, request_type=REQ_CHECKPOINT_SOURCE, target_resource_id=source_approval_id,
    )
    return ckpt.register_operator_approved_checkpoint(
        checkpoint_id, file_path=file_path, architecture=architecture, license=license,
        source_url=source_url, description=description, preprocessing=preprocessing,
        approver_id=approver_username,
        license_evidence_ref=f"governance_approval:{lic.id}",
        source_evidence_ref=f"governance_approval:{src.id}",
    )


def assess_scientific_readiness(
    db: Session, *, tenant_id: str, dataset_id: str, dataset_owner_email: str,
    checkpoint_id: str, statistical_reviewer_username: str, statistical_protocol_id: str,
) -> dict:
    """Resolve ALL scientific-readiness prerequisites against records and return a
    decision. Each prerequisite is checked fail-closed; the result lists what resolved
    and what blocked. Never trusts a caller-supplied readiness flag."""
    from research.lens_vision import checkpoint as ckpt  # noqa: PLC0415

    checks: dict[str, str] = {}

    def _run(name, fn):
        try:
            fn()
            checks[name] = "resolved"
        except Exception as exc:  # noqa: BLE001 - we record the reason
            checks[name] = f"BLOCKED: {type(exc).__name__}: {exc}"

    _run("data_authorization", lambda: verify_data_authorization(
        db, tenant_id=tenant_id, user_email=dataset_owner_email, dataset_id=dataset_id))
    _run("statistical_signoff", lambda: verify_statistical_signoff(
        db, reviewer_username=statistical_reviewer_username, tenant_id=tenant_id,
        protocol_id=statistical_protocol_id))

    def _ckpt():
        rec = ckpt.get_record(checkpoint_id)
        ckpt.assert_scientific_checkpoint(rec)
    _run("scientific_checkpoint", _ckpt)

    ready = all(v == "resolved" for v in checks.values())
    return {
        "schema": "lumenai.stage6c.scientific_readiness.v1",
        "ready_for_scientific_benchmark": ready,
        "checks": checks,
        "note": "All prerequisites resolved against authoritative records; fail-closed. "
                "Readiness here is necessary, not a clinical-validation claim.",
    }
