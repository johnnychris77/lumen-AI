from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
from typing import Any

from fastapi import HTTPException

from app.core.object_authorization import ProtectedObject, require_object_permission
from app.core.principal import Principal


@dataclass(frozen=True)
class EvidenceBundle:
    bundle_id: str
    tenant_id: str
    workflow_type: str
    manifest_hash: str
    vendor_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class EvidenceAuditEvent:
    actor_user_id: str
    tenant_id: str
    evidence_bundle_id: str
    action: str
    workflow_type: str
    authorization_result: str
    timestamp: str


READ_ACTIONS = {"read", "view", "download", "verify"}
WRITE_ACTIONS = {"generate", "regenerate", "delete", "modify"}


def _access_denied() -> HTTPException:
    return HTTPException(
        status_code=403,
        detail={
            "error": {
                "code": "ACCESS_DENIED",
                "message": "You do not have permission to access this resource.",
                "status_code": 403,
            }
        },
    )


def build_manifest_hash(manifest: dict[str, Any]) -> str:
    canonical = repr(sorted(manifest.items())).encode("utf-8")
    return sha256(canonical).hexdigest()


def verify_evidence_manifest_hash(bundle: EvidenceBundle, manifest: dict[str, Any]) -> bool:
    return build_manifest_hash(manifest) == bundle.manifest_hash


def require_evidence_permission(
    principal: Principal,
    bundle: EvidenceBundle,
    action: str = "download",
    principal_vendor_id: str | None = None,
) -> None:
    protected_object = ProtectedObject(
        object_id=bundle.bundle_id,
        tenant_id=bundle.tenant_id,
        workflow_type="evidence" if bundle.workflow_type != "vendor" else "vendor",
        vendor_id=bundle.vendor_id,
    )

    if principal.has_role("auditor") and action in WRITE_ACTIONS:
        raise _access_denied()

    mapped_action = "read" if action in READ_ACTIONS else "update"

    require_object_permission(
        principal=principal,
        protected_object=protected_object,
        action=mapped_action,
        principal_vendor_id=principal_vendor_id,
    )


def create_evidence_audit_event(
    principal: Principal,
    bundle: EvidenceBundle,
    action: str,
    authorization_result: str,
) -> EvidenceAuditEvent:
    return EvidenceAuditEvent(
        actor_user_id=principal.user_id,
        tenant_id=principal.tenant_id,
        evidence_bundle_id=bundle.bundle_id,
        action=action,
        workflow_type=bundle.workflow_type,
        authorization_result=authorization_result,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
