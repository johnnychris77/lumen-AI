"""DEPRECATED: use app.services.enterprise_audit_service instead.

This module's log_audit_event() used to write audit_logs rows directly and
did not hash-chain them, leaving a gap in tamper-evidence coverage relative
to app.services.enterprise_audit_service.record_enterprise_audit_event() --
which computes a SHA-256 hash per event, chained to the previous event for
the same (resource_type, resource_id), verifiable via
app.services.audit_chain_verification_service.verify_audit_chain().

Every LumenAI audit event -- including cross-hospital intelligence events
(federated aggregation, publish, benchmark queries, cross-hospital data
access) -- must be tamper-evident. log_audit_event() now delegates to the
hash-chained writer internally, so every existing call site gets hash-chain
coverage with no code changes required. New code should call
record_enterprise_audit_event() directly instead of importing from this
module.
"""
from __future__ import annotations

import warnings
from typing import Any

from fastapi import Request
from sqlalchemy.orm import Session

_DEPRECATION_MESSAGE = (
    "app.audit.log_audit_event is deprecated and will be removed. It now "
    "delegates to app.services.enterprise_audit_service.record_enterprise_audit_event "
    "for hash-chained, tamper-evident audit records -- call that function "
    "directly in new code instead of importing from app.audit."
)

# Module-level notice: fires once, the first time anything imports app.audit
# (still every process start, since ~77 route modules do `from app.audit
# import log_audit_event`). log_audit_event() itself also warns on every
# call -- see below -- since a single import-time warning would otherwise
# get lost among the many other imports that happen at app startup.
warnings.warn(_DEPRECATION_MESSAGE, DeprecationWarning, stacklevel=2)


def log_audit_event(
    db: Session,
    *,
    tenant_id: str,
    tenant_name: str,
    actor_email: str,
    actor_role: str,
    action_type: str,
    resource_type: str = "",
    resource_id: str = "",
    status: str = "success",
    request: Request | None = None,
    details: dict[str, Any] | None = None,
    compliance_flag: bool = False,
):
    """DEPRECATED -- call app.services.enterprise_audit_service.record_enterprise_audit_event() instead.

    Kept for backward compatibility with existing call sites. Delegates to
    the hash-chained writer so every event recorded through this function is
    now part of a verifiable tamper-evident chain, closing the gap between
    this module and enterprise_audit_service.py.
    """
    warnings.warn(_DEPRECATION_MESSAGE, DeprecationWarning, stacklevel=2)

    # Imported lazily (not at module top) so that app.audit -- imported by
    # ~77 route modules, some of which may be the first thing to touch
    # app.db/app.models in a given process -- can't trigger the circular
    # import that app.services.enterprise_audit_service -> app.models.audit_log
    # -> app.models (package) -> app.db.base -> app.db -> app.db.models ->
    # app.models.inspection can hit when entered in that order. By call
    # time, a caller already has a `db` Session, so app.db/app.models are
    # guaranteed to be fully initialized.
    from app.services.enterprise_audit_service import record_enterprise_audit_event

    normalized_actor_email = (actor_email or "").strip().lower()

    return record_enterprise_audit_event(
        db,
        action_type=action_type,
        resource_type=resource_type,
        resource_id=str(resource_id or ""),
        actor=normalized_actor_email,
        actor_email=normalized_actor_email,
        actor_role=actor_role or "",
        tenant_id=tenant_id or "default-tenant",
        tenant_name=tenant_name or "Default Tenant",
        status=status,
        compliance_flag=bool(compliance_flag),
        details=details,
        request=request,
        commit=True,
    )
