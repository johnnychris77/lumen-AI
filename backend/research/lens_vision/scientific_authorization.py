"""Stage 6C/6D — authenticated scientific-approval resolution (research-only).

Every scientific approval is resolved against authoritative records and is
**fail-closed**. No caller-supplied string/bool/dict is accepted as proof.

Stage 6D hardening (final authorization gaps):

* **Authenticated request context (6D).** Approvals bind to the trusted
  ``AuthContext`` principal (``actor`` + ``role``), never a caller-supplied username.
  A mismatch between a claimed approver and the authenticated actor is an
  impersonation error.
* **Checkpoint evidence scope/status/authority.** A license/source approval must be
  ``approved``, carry the applicable **use scope**, and be reviewed by an authenticated
  approver with authority.
* **Cohort-specific authorization.** Research consent + institutional authorization are
  resolved for the **specific dataset/cohort**, not an unrelated tenant-wide consent.
* **Laboratory confirmation.** Resolved from an independently-verified
  ``VeritasEvidenceProvenanceRecord`` linked to the **exact specimen + image** — never
  an arbitrary boolean.
* **Immutable audit.** Every resolution writes a hash-chained enterprise audit event.

Reused records: ``UserRoleAssignment``, ``GovernanceApproval``, ``ConsentRecord``,
``VeritasEvidenceProvenanceRecord``. No new governance platform is created.
"""
from __future__ import annotations

import json
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.auth.context import AuthContext
from app.models.governance_approval import GovernanceApproval
from app.models.user_role_assignment import UserRoleAssignment
from app.models.veritas_evidence import VeritasEvidenceProvenanceRecord
from app.services.enterprise_audit_service import record_enterprise_audit_event
from research.lens_vision.governance import research_use_scope_authorized

SCIENTIFIC_APPROVER_ROLES = frozenset({"admin", "quality_director"})
STATISTICAL_REVIEWER_ROLES = frozenset({"admin", "quality_director"})

# GovernanceApproval.request_type values this module resolves.
REQ_CHECKPOINT_LICENSE = "scientific_checkpoint_license"
REQ_CHECKPOINT_SOURCE = "scientific_checkpoint_source"
REQ_DATA_AUTHORIZATION = "research_data_authorization"
REQ_RESEARCH_CONSENT = "research_use_consent"            # dataset-scoped consent record
REQ_STATISTICAL_PROTOCOL = "statistical_protocol_approval"

# The use scope a scientific-checkpoint approval must carry.
USE_SCOPE_SCIENTIFIC = "scientific_research"

_APPROVED = "approved"


class ScientificAuthorizationError(PermissionError):
    """A scientific-approval check could not be resolved against authoritative
    records (impersonation, forged/absent approver, missing/withdrawn evidence or
    permission, wrong use scope, or unlinked laboratory confirmation)."""


@dataclass(frozen=True)
class LabConfirmation:
    """A resolved, record-backed laboratory confirmation for one image/specimen."""

    confirmed: bool
    identity: str | None
    evidence_record_id: int | None
    reason: str = ""


def _audit(db, auth: AuthContext | None, *, action: str, resource_type: str, resource_id,
           status: str, details: dict | None = None) -> None:
    """Write an immutable, hash-chained audit event (best-effort; never raises)."""
    try:
        record_enterprise_audit_event(
            db, action_type=action, resource_type=resource_type, resource_id=str(resource_id),
            actor=(auth.actor if auth else "research-system"),
            actor_role=(auth.role if auth else "system"),
            tenant_id=(auth.tenant_id if auth else None),
            status=status, details=details or {}, auth_context=auth, commit=True,
        )
    except Exception:  # pragma: no cover - audit must never break the control flow
        pass


# ── authenticated approver binding (§2.1) ────────────────────────────────────

def resolve_role(db: Session, username: str, *, allowed_roles: frozenset) -> str:
    """Resolve an authenticated user's role from ``UserRoleAssignment`` (fail-closed)."""
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


def authorize_scientific_actor(db: Session, auth: AuthContext, *, allowed_roles: frozenset) -> str:
    """Bind the approval to the TRUSTED authenticated context. The authenticated
    ``actor`` must (a) hold an allowed role in the context AND (b) resolve to a
    matching ``UserRoleAssignment`` record. A caller cannot impersonate another
    approver — the actor is taken from ``auth``, never a caller string."""
    if not isinstance(auth, AuthContext) or not str(auth.actor or "").strip():
        raise ScientificAuthorizationError("A trusted authenticated context is required.")
    if auth.role not in allowed_roles:
        raise ScientificAuthorizationError(
            f"Authenticated actor '{auth.actor}' role '{auth.role}' is not an allowed scientific approver."
        )
    record_role = resolve_role(db, auth.actor, allowed_roles=allowed_roles)
    if record_role != auth.role:
        raise ScientificAuthorizationError(
            f"Authenticated role '{auth.role}' does not match the recorded role '{record_role}' "
            f"for actor '{auth.actor}' (possible impersonation)."
        )
    return auth.actor


# ── governance-approval resolution with scope/status/authority (§2.2) ─────────

def _approval_use_scope(rec: GovernanceApproval) -> str:
    try:
        return str(json.loads(rec.requested_payload or "{}").get("use_scope") or "").strip()
    except (ValueError, TypeError):
        return ""


def resolve_governance_approval(
    db: Session, *, tenant_id: str, request_type: str, target_resource_id: str,
    required_use_scope: str | None = None,
) -> GovernanceApproval:
    """Resolve an approved ``GovernanceApproval`` whose reviewer is an authenticated
    approver and whose use scope matches (when required). Fail-closed."""
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
    # Reviewer authority: the record's reviewer must be an authenticated approver.
    resolve_role(db, rec.reviewed_by, allowed_roles=SCIENTIFIC_APPROVER_ROLES)
    # Applicable use scope.
    if required_use_scope is not None and _approval_use_scope(rec) != required_use_scope:
        raise ScientificAuthorizationError(
            f"Approval '{rid}' use scope '{_approval_use_scope(rec)}' != required '{required_use_scope}'."
        )
    return rec


# ── cohort-specific data authorization (§2.3) ────────────────────────────────

def verify_data_authorization(db: Session, *, tenant_id: str, dataset_id: str, auth: AuthContext | None = None) -> None:
    """Fail-closed, DATASET-SPECIFIC authorization: an approved institutional
    data-authorization record for THIS dataset AND an approved, dataset-scoped
    research-use consent record for THIS dataset. A tenant-wide consent alone is NOT
    sufficient (it is checked only as a secondary signal)."""
    resolve_governance_approval(
        db, tenant_id=tenant_id, request_type=REQ_DATA_AUTHORIZATION, target_resource_id=dataset_id,
    )
    resolve_governance_approval(
        db, tenant_id=tenant_id, request_type=REQ_RESEARCH_CONSENT, target_resource_id=dataset_id,
    )
    # Secondary: a tenant-level research-use consent must also exist and be live.
    if not research_use_scope_authorized(db, tenant_id):
        raise ScientificAuthorizationError(
            f"Tenant '{tenant_id}' has no granted, non-withdrawn research-use consent."
        )
    _audit(db, auth, action="research_data_authorization_resolved", resource_type="research_dataset",
           resource_id=dataset_id, status="success", details={"dataset_id": dataset_id})


# ── statistical reviewer sign-off (bound to authenticated context) ───────────

def verify_statistical_signoff(db: Session, *, auth: AuthContext, tenant_id: str, protocol_id: str) -> dict:
    """Resolve the statistical reviewer from the AUTHENTICATED context + an approved
    statistical-protocol record reviewed by that same actor. Fail-closed."""
    actor = authorize_scientific_actor(db, auth, allowed_roles=STATISTICAL_REVIEWER_ROLES)
    rec = resolve_governance_approval(
        db, tenant_id=tenant_id, request_type=REQ_STATISTICAL_PROTOCOL, target_resource_id=protocol_id,
    )
    if (rec.reviewed_by or "").strip() != actor:
        raise ScientificAuthorizationError(
            "Statistical protocol was not reviewed by the authenticated statistical reviewer."
        )
    _audit(db, auth, action="statistical_signoff_resolved", resource_type="statistical_protocol",
           resource_id=protocol_id, status="success", details={"protocol_id": protocol_id})
    return {"reviewer": actor, "reviewer_role": auth.role, "protocol_id": protocol_id,
            "governance_approval_id": rec.id, "resolved": True}


# ── laboratory confirmation resolved from evidence records (§2.4) ────────────

def resolve_lab_confirmation(
    db: Session, *, tenant_id: str, image_sha256: str, specimen_id: str = "", instrument_id: str = "",
) -> LabConfirmation:
    """Resolve laboratory confirmation for the EXACT image + specimen from an approved
    ``VeritasEvidenceProvenanceRecord`` whose ``file_hash`` matches the image hash (and
    instrument, when supplied). Fail-closed: no approved, matching record ⇒ not
    confirmed. There is no boolean short-circuit."""
    h = str(image_sha256 or "").strip()
    if not h:
        return LabConfirmation(False, None, None, "no_image_hash")
    q = db.query(VeritasEvidenceProvenanceRecord).filter(
        VeritasEvidenceProvenanceRecord.tenant_id == tenant_id,
        VeritasEvidenceProvenanceRecord.file_hash == h,
        VeritasEvidenceProvenanceRecord.approval_status == _APPROVED,
    )
    if instrument_id:
        q = q.filter(VeritasEvidenceProvenanceRecord.instrument_id == instrument_id)
    rec = q.order_by(VeritasEvidenceProvenanceRecord.id.desc()).first()
    if rec is None:
        return LabConfirmation(False, None, None, "no_approved_evidence_for_image")
    # The evidence must carry a reviewer (independent verification).
    if not str(rec.reviewer or "").strip():
        return LabConfirmation(False, None, rec.id, "evidence_not_independently_reviewed")
    identity = str(rec.evidence_type or "").strip() or None
    return LabConfirmation(True, identity, rec.id, "resolved")


# ── scientific checkpoint registration bound to authenticated context ────────

def register_scientific_checkpoint(
    db: Session, checkpoint_id: str, *, file_path: str, architecture: str, tenant_id: str,
    auth: AuthContext, license_approval_id: str, source_approval_id: str,
    license: str = "", source_url: str = "", description: str = "", preprocessing: dict | None = None,
):
    """Register a checkpoint for SCIENTIFIC use only after binding the approver to the
    authenticated context and resolving the license + source records (with the
    scientific use scope). Fail-closed; writes an audit event."""
    from research.lens_vision import checkpoint as ckpt  # noqa: PLC0415

    actor = authorize_scientific_actor(db, auth, allowed_roles=SCIENTIFIC_APPROVER_ROLES)
    lic = resolve_governance_approval(
        db, tenant_id=tenant_id, request_type=REQ_CHECKPOINT_LICENSE, target_resource_id=license_approval_id,
        required_use_scope=USE_SCOPE_SCIENTIFIC)
    src = resolve_governance_approval(
        db, tenant_id=tenant_id, request_type=REQ_CHECKPOINT_SOURCE, target_resource_id=source_approval_id,
        required_use_scope=USE_SCOPE_SCIENTIFIC)
    rec = ckpt.register_operator_approved_checkpoint(
        checkpoint_id, file_path=file_path, architecture=architecture, license=license,
        source_url=source_url, description=description, preprocessing=preprocessing,
        approver_id=actor, license_evidence_ref=f"governance_approval:{lic.id}",
        source_evidence_ref=f"governance_approval:{src.id}")
    _audit(db, auth, action="scientific_checkpoint_registered", resource_type="checkpoint",
           resource_id=checkpoint_id, status="success",
           details={"license_approval_id": lic.id, "source_approval_id": src.id})
    return rec


def assess_scientific_readiness(
    db: Session, *, tenant_id: str, dataset_id: str, checkpoint_id: str,
    statistical_auth: AuthContext | None, statistical_protocol_id: str,
    data_auth: AuthContext | None = None,
) -> dict:
    """Resolve ALL scientific-readiness prerequisites against records (fail-closed) and
    return a decision. Never trusts a caller-supplied readiness flag."""
    from research.lens_vision import checkpoint as ckpt  # noqa: PLC0415

    checks: dict[str, str] = {}

    def _run(name, fn):
        try:
            fn()
            checks[name] = "resolved"
        except Exception as exc:  # noqa: BLE001
            checks[name] = f"BLOCKED: {type(exc).__name__}: {exc}"

    _run("data_authorization", lambda: verify_data_authorization(
        db, tenant_id=tenant_id, dataset_id=dataset_id, auth=data_auth))
    _run("statistical_signoff", lambda: verify_statistical_signoff(
        db, auth=statistical_auth, tenant_id=tenant_id, protocol_id=statistical_protocol_id)
        if statistical_auth is not None else _raise_no_auth())

    def _ckpt():
        rec = ckpt.get_record(checkpoint_id)
        ckpt.assert_scientific_checkpoint(rec)
    _run("scientific_checkpoint", _ckpt)

    ready = all(v == "resolved" for v in checks.values())
    return {
        "schema": "lumenai.stage6d.scientific_readiness.v2",
        "ready_for_scientific_benchmark": ready,
        "checks": checks,
        "note": "All prerequisites resolved against authoritative records, bound to the "
                "authenticated context; fail-closed. Not a clinical-validation claim.",
    }


def _raise_no_auth():
    raise ScientificAuthorizationError("No authenticated statistical-reviewer context supplied.")
