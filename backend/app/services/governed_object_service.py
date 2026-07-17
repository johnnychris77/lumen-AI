"""Project Foundation (GPAE) — governed object storage service.

Wraps the existing byte-transport layer (``app.services.object_storage``)
with the Foundation Sprint 1 governance contract:

  * every stored object gets a permanent registry row (``GovernedObject``)
    with Object ID, SHA-256, uploader, tenant, retention policy, storage
    URI and version;
  * identical bytes are never stored twice for the same tenant (SHA-256
    dedup — a re-registration returns the existing row and audits the hit);
  * every register / verified read / integrity failure / supersession is
    written to the hash-chained audit trail via
    ``record_enterprise_audit_event`` (this service never writes its own
    audit table);
  * reads re-verify SHA-256 against the registry before returning bytes —
    a mismatch fails closed with ``GovernedObjectIntegrityError`` and is
    audited, mirroring ``baseline_image_library_service``.

Tenant isolation: every query in this module filters on ``tenant_id``;
an object registered by one tenant is invisible to every other tenant.
"""
from __future__ import annotations

import hashlib
import io
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models.governed_object import (
    OBJECT_CATEGORIES,
    RETENTION_POLICIES,
    STATUS_ACTIVE,
    STATUS_SUPERSEDED,
    GovernedObject,
)
from app.services import object_storage
from app.services.enterprise_audit_service import record_enterprise_audit_event


class GovernedObjectError(ValueError):
    """Invalid input to the governed object store."""


class GovernedObjectNotFoundError(LookupError):
    """No object with that ID exists for this tenant."""


class GovernedObjectIntegrityError(RuntimeError):
    """Stored bytes no longer match the registered SHA-256."""


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _to_dict(obj: GovernedObject, *, deduplicated: bool = False) -> dict[str, Any]:
    return {
        "object_id": obj.object_id,
        "tenant_id": obj.tenant_id,
        "sha256": obj.sha256,
        "size_bytes": obj.size_bytes,
        "content_type": obj.content_type,
        "original_filename": obj.original_filename,
        "object_category": obj.object_category,
        "uploaded_at": obj.uploaded_at.isoformat() if obj.uploaded_at else None,
        "uploader": obj.uploader,
        "retention_policy": obj.retention_policy,
        "storage_backend": obj.storage_backend,
        "storage_uri": obj.storage_uri,
        "version": obj.version,
        "supersedes_object_id": obj.supersedes_object_id,
        "status": obj.status,
        "last_verified_at": obj.last_verified_at.isoformat() if obj.last_verified_at else None,
        "integrity_intact": obj.integrity_intact,
        "deduplicated": deduplicated,
    }


def register_object(
    db: Session,
    *,
    tenant_id: str,
    data: bytes,
    object_category: str,
    uploader: str = "system",
    content_type: str = "application/octet-stream",
    original_filename: str = "",
    retention_policy: str = "retain_indefinitely",
    supersedes_object_id: str = "",
) -> dict[str, Any]:
    """Register bytes in the governed store.

    Returns the registry record as a dict. If the exact bytes are already
    registered for this tenant, no second copy is written — the existing
    record is returned with ``deduplicated=True`` and the hit is audited.
    """
    if not data:
        raise GovernedObjectError("Cannot register an empty object.")
    if object_category not in OBJECT_CATEGORIES:
        raise GovernedObjectError(
            f"Unknown object_category {object_category!r}; expected one of {OBJECT_CATEGORIES}."
        )
    if retention_policy not in RETENTION_POLICIES:
        raise GovernedObjectError(
            f"Unknown retention_policy {retention_policy!r}; expected one of {RETENTION_POLICIES}."
        )
    if not tenant_id:
        raise GovernedObjectError("tenant_id is required.")

    sha256 = hashlib.sha256(data).hexdigest()

    existing = (
        db.query(GovernedObject)
        .filter(GovernedObject.tenant_id == tenant_id, GovernedObject.sha256 == sha256)
        .first()
    )
    if existing is not None:
        record_enterprise_audit_event(
            db,
            action_type="governed_object_dedup_hit",
            resource_type="governed_object",
            resource_id=existing.object_id,
            actor=uploader,
            tenant_id=tenant_id,
            details={"sha256": sha256, "object_category": object_category},
        )
        return _to_dict(existing, deduplicated=True)

    object_id = f"GOBJ-{uuid.uuid4().hex}"
    object_key = f"governed/{tenant_id}/{sha256[:2]}/{sha256}"
    stored = object_storage.save_upload_file(
        file_obj=io.BytesIO(data),
        file_name=original_filename or object_id,
        object_key=object_key,
        content_type=content_type,
    )

    version = 1
    if supersedes_object_id:
        prior = (
            db.query(GovernedObject)
            .filter(
                GovernedObject.tenant_id == tenant_id,
                GovernedObject.object_id == supersedes_object_id,
            )
            .first()
        )
        if prior is None:
            raise GovernedObjectNotFoundError(
                f"supersedes_object_id {supersedes_object_id!r} not found for this tenant."
            )
        prior.status = STATUS_SUPERSEDED
        version = prior.version + 1

    record = GovernedObject(
        object_id=object_id,
        tenant_id=tenant_id,
        sha256=sha256,
        size_bytes=len(data),
        content_type=content_type,
        original_filename=original_filename,
        object_category=object_category,
        uploaded_at=_now(),
        uploader=uploader,
        retention_policy=retention_policy,
        storage_backend=stored.backend,
        storage_uri=stored.storage_uri,
        version=version,
        supersedes_object_id=supersedes_object_id,
        status=STATUS_ACTIVE,
    )
    db.add(record)
    db.flush()

    record_enterprise_audit_event(
        db,
        action_type="governed_object_registered",
        resource_type="governed_object",
        resource_id=object_id,
        actor=uploader,
        tenant_id=tenant_id,
        details={
            "sha256": sha256,
            "size_bytes": len(data),
            "object_category": object_category,
            "retention_policy": retention_policy,
            "storage_backend": stored.backend,
            "version": version,
            "supersedes_object_id": supersedes_object_id,
        },
    )
    db.commit()
    db.refresh(record)
    return _to_dict(record)


def get_object_record(db: Session, *, tenant_id: str, object_id: str) -> dict[str, Any]:
    record = _get(db, tenant_id=tenant_id, object_id=object_id)
    return _to_dict(record)


def _get(db: Session, *, tenant_id: str, object_id: str) -> GovernedObject:
    record = (
        db.query(GovernedObject)
        .filter(GovernedObject.tenant_id == tenant_id, GovernedObject.object_id == object_id)
        .first()
    )
    if record is None:
        raise GovernedObjectNotFoundError(f"Governed object {object_id!r} not found for this tenant.")
    return record


def load_and_verify_object(db: Session, *, tenant_id: str, object_id: str, actor: str = "system") -> bytes:
    """Return the object's bytes after re-verifying SHA-256 against the registry.

    Fails closed: a hash mismatch marks the record ``integrity_intact=False``,
    audits the failure, and raises — corrupted bytes are never returned.
    """
    record = _get(db, tenant_id=tenant_id, object_id=object_id)

    local_path = object_storage.open_stored_object(record.storage_uri)
    try:
        with open(local_path, "rb") as fh:
            data = fh.read()
    except OSError as exc:
        record.integrity_intact = False
        record_enterprise_audit_event(
            db,
            action_type="governed_object_integrity_failed",
            resource_type="governed_object",
            resource_id=object_id,
            actor=actor,
            tenant_id=tenant_id,
            status="failure",
            details={"reason": f"storage read failed: {exc}", "storage_uri": record.storage_uri},
        )
        db.commit()
        raise GovernedObjectIntegrityError(
            f"Governed object {object_id!r} could not be read from storage."
        ) from exc

    actual = hashlib.sha256(data).hexdigest()
    if actual != record.sha256:
        record.integrity_intact = False
        record_enterprise_audit_event(
            db,
            action_type="governed_object_integrity_failed",
            resource_type="governed_object",
            resource_id=object_id,
            actor=actor,
            tenant_id=tenant_id,
            status="failure",
            details={"expected_sha256": record.sha256, "actual_sha256": actual},
        )
        db.commit()
        raise GovernedObjectIntegrityError(
            f"Governed object {object_id!r} failed SHA-256 verification: stored bytes do not "
            "match the registered hash."
        )

    record.last_verified_at = _now()
    record.integrity_intact = True
    record_enterprise_audit_event(
        db,
        action_type="governed_object_accessed",
        resource_type="governed_object",
        resource_id=object_id,
        actor=actor,
        tenant_id=tenant_id,
        details={"sha256": actual, "size_bytes": len(data)},
    )
    db.commit()
    return data


def list_objects(
    db: Session,
    *,
    tenant_id: str,
    object_category: str | None = None,
    status: str | None = STATUS_ACTIVE,
) -> list[dict[str, Any]]:
    query = db.query(GovernedObject).filter(GovernedObject.tenant_id == tenant_id)
    if object_category:
        query = query.filter(GovernedObject.object_category == object_category)
    if status:
        query = query.filter(GovernedObject.status == status)
    return [_to_dict(r) for r in query.order_by(GovernedObject.id.asc()).all()]
