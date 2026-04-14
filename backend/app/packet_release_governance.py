from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.db import models


DEFAULT_ATTESTATION = (
    "I attest that this packet has been reviewed for audience appropriateness, "
    "data accuracy, and release readiness, and may be distributed to the approved recipients."
)


def _compact(value: Any) -> str:
    return json.dumps(value, default=str)[:4000]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def log_release_history(
    db: Session,
    *,
    tenant_id: str,
    tenant_name: str,
    release_id: int,
    packet_id: int,
    action_type: str,
    actor_email: str,
    actor_role: str,
    details: dict,
):
    row = models.PacketReleaseHistory(
        tenant_id=tenant_id,
        tenant_name=tenant_name,
        release_id=release_id,
        packet_id=packet_id,
        action_type=action_type,
        actor_email=actor_email,
        actor_role=actor_role,
        details_json=_compact(details),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_release_for_packet(db: Session, tenant_id: str, packet_id: int):
    return (
        db.query(models.PacketRelease)
        .filter(
            models.PacketRelease.tenant_id == tenant_id,
            models.PacketRelease.packet_id == packet_id,
        )
        .order_by(models.PacketRelease.id.desc())
        .first()
    )


def release_allows_delivery(db: Session, tenant_id: str, packet_id: int) -> dict:
    row = get_release_for_packet(db, tenant_id, packet_id)
    if not row:
        return {
            "allowed": False,
            "reason": "No packet release request found",
            "status": "missing",
        }
    if row.status != "approved":
        return {
            "allowed": False,
            "reason": f"Packet release status is {row.status}",
            "status": row.status,
            "release_id": row.id,
        }
    return {
        "allowed": True,
        "reason": "",
        "status": row.status,
        "release_id": row.id,
    }


def request_packet_release(
    db: Session,
    *,
    tenant_id: str,
    tenant_name: str,
    packet_id: int,
    packet_title: str,
    audience_type: str,
    requested_by: str,
    requested_role: str,
    attestation_required: bool = True,
    attestation_text: str = "",
):
    row = models.PacketRelease(
        tenant_id=tenant_id,
        tenant_name=tenant_name,
        packet_id=packet_id,
        packet_title=packet_title,
        audience_type=audience_type,
        requested_by=requested_by,
        requested_role=requested_role,
        status="pending",
        approver_email="",
        approver_role="",
        approval_notes="",
        attestation_required=attestation_required,
        attestation_text=attestation_text or DEFAULT_ATTESTATION,
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    log_release_history(
        db,
        tenant_id=tenant_id,
        tenant_name=tenant_name,
        release_id=row.id,
        packet_id=packet_id,
        action_type="requested",
        actor_email=requested_by,
        actor_role=requested_role,
        details={"audience_type": audience_type, "attestation_required": attestation_required},
    )
    return row


def approve_packet_release(
    db: Session,
    *,
    release_id: int,
    tenant_id: str,
    approver_email: str,
    approver_role: str,
    approval_notes: str,
):
    row = (
        db.query(models.PacketRelease)
        .filter(
            models.PacketRelease.id == release_id,
            models.PacketRelease.tenant_id == tenant_id,
        )
        .first()
    )
    if not row:
        raise ValueError("Packet release not found")

    row.status = "approved"
    row.approver_email = approver_email
    row.approver_role = approver_role
    row.approval_notes = approval_notes
    row.reviewed_at = _now()
    db.add(row)
    db.commit()
    db.refresh(row)

    log_release_history(
        db,
        tenant_id=row.tenant_id,
        tenant_name=row.tenant_name,
        release_id=row.id,
        packet_id=row.packet_id,
        action_type="approved",
        actor_email=approver_email,
        actor_role=approver_role,
        details={"approval_notes": approval_notes, "attestation_text": row.attestation_text},
    )
    return row


def reject_packet_release(
    db: Session,
    *,
    release_id: int,
    tenant_id: str,
    approver_email: str,
    approver_role: str,
    approval_notes: str,
):
    row = (
        db.query(models.PacketRelease)
        .filter(
            models.PacketRelease.id == release_id,
            models.PacketRelease.tenant_id == tenant_id,
        )
        .first()
    )
    if not row:
        raise ValueError("Packet release not found")

    row.status = "rejected"
    row.approver_email = approver_email
    row.approver_role = approver_role
    row.approval_notes = approval_notes
    row.reviewed_at = _now()
    db.add(row)
    db.commit()
    db.refresh(row)

    log_release_history(
        db,
        tenant_id=row.tenant_id,
        tenant_name=row.tenant_name,
        release_id=row.id,
        packet_id=row.packet_id,
        action_type="rejected",
        actor_email=approver_email,
        actor_role=approver_role,
        details={"approval_notes": approval_notes},
    )
    return row
