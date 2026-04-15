from __future__ import annotations

import json
from collections import Counter
from sqlalchemy.orm import Session

from app.db import models
from app.packet_release_governance import release_governance_status


def _safe_json(value: str | None) -> dict:
    if not value:
        return {}
    try:
        return json.loads(value)
    except Exception:
        return {}


def _packet_row(packet: models.LeadershipPacket, status: dict) -> dict:
    return {
        "packet_id": packet.id,
        "title": packet.title,
        "packet_type": packet.packet_type,
        "briefing_id": packet.briefing_id,
        "allowed": status.get("allowed", False),
        "reason": status.get("reason", ""),
        "release": status.get("release"),
        "holds": status.get("holds", []),
        "override": status.get("override"),
        "created_at": packet.created_at.isoformat() if packet.created_at else None,
    }


def packet_status(db: Session, tenant_id: str, packet_id: int) -> dict:
    packet = (
        db.query(models.LeadershipPacket)
        .filter(
            models.LeadershipPacket.id == packet_id,
            models.LeadershipPacket.tenant_id == tenant_id,
        )
        .first()
    )
    if not packet:
        return {"detail": "Leadership packet not found"}

    status = release_governance_status(db, tenant_id, packet_id)

    latest_delivery = (
        db.query(models.LeadershipPacketDelivery)
        .filter(
            models.LeadershipPacketDelivery.tenant_id == tenant_id,
            models.LeadershipPacketDelivery.packet_id == packet_id,
        )
        .order_by(models.LeadershipPacketDelivery.id.desc())
        .first()
    )

    latest_release = (
        db.query(models.PacketRelease)
        .filter(
            models.PacketRelease.tenant_id == tenant_id,
            models.PacketRelease.packet_id == packet_id,
        )
        .order_by(models.PacketRelease.id.desc())
        .first()
    )

    return {
        **_packet_row(packet, status),
        "latest_delivery": {
            "id": latest_delivery.id,
            "delivery_status": latest_delivery.delivery_status,
            "delivery_channel": latest_delivery.delivery_channel,
            "delivery_target": latest_delivery.delivery_target,
            "created_at": latest_delivery.created_at.isoformat() if latest_delivery.created_at else None,
            "result_json": latest_delivery.result_json,
        } if latest_delivery else None,
        "latest_release_row": {
            "id": latest_release.id,
            "status": latest_release.status,
            "requested_by": latest_release.requested_by,
            "approver_email": latest_release.approver_email,
            "reviewed_at": latest_release.reviewed_at.isoformat() if latest_release.reviewed_at else None,
        } if latest_release else None,
    }


def readiness(db: Session, tenant_id: str) -> dict:
    packets = (
        db.query(models.LeadershipPacket)
        .filter(models.LeadershipPacket.tenant_id == tenant_id)
        .order_by(models.LeadershipPacket.id.desc())
        .all()
    )

    items = []
    counts = Counter()

    for packet in packets:
        status = release_governance_status(db, tenant_id, packet.id)
        row = _packet_row(packet, status)

        latest_delivery = (
            db.query(models.LeadershipPacketDelivery)
            .filter(
                models.LeadershipPacketDelivery.tenant_id == tenant_id,
                models.LeadershipPacketDelivery.packet_id == packet.id,
            )
            .order_by(models.LeadershipPacketDelivery.id.desc())
            .first()
        )

        latest_release = (
            db.query(models.PacketRelease)
            .filter(
                models.PacketRelease.tenant_id == tenant_id,
                models.PacketRelease.packet_id == packet.id,
            )
            .order_by(models.PacketRelease.id.desc())
            .first()
        )

        release_status = latest_release.status if latest_release else "missing"
        delivery_status = latest_delivery.delivery_status if latest_delivery else "not_sent"

        if row["allowed"] and release_status == "approved":
            readiness_state = "ready"
        elif row["override"]:
            readiness_state = "override_active"
        elif row["holds"]:
            readiness_state = "held"
        elif release_status == "pending":
            readiness_state = "pending_release"
        elif release_status == "rejected":
            readiness_state = "rejected"
        else:
            readiness_state = "blocked"

        counts[readiness_state] += 1
        counts[f"delivery_{delivery_status}"] += 1

        items.append({
            **row,
            "readiness_state": readiness_state,
            "release_status": release_status,
            "delivery_status": delivery_status,
        })

    return {
        "counts": dict(counts),
        "items": items,
    }


def exceptions(db: Session, tenant_id: str) -> dict:
    data = readiness(db, tenant_id)
    items = []

    for item in data["items"]:
        if item["readiness_state"] in {"held", "blocked", "pending_release", "rejected", "override_active"} or item["delivery_status"] in {"failed", "blocked"}:
            exception_type = []
            if item["holds"]:
                exception_type.append("active_hold")
            if item["override"]:
                exception_type.append("override_active")
            if item["release_status"] == "pending":
                exception_type.append("pending_release")
            if item["release_status"] == "rejected":
                exception_type.append("release_rejected")
            if item["delivery_status"] == "failed":
                exception_type.append("delivery_failed")
            if item["delivery_status"] == "blocked":
                exception_type.append("delivery_blocked")
            if item["release_status"] == "missing":
                exception_type.append("release_missing")

            items.append({
                **item,
                "exception_types": exception_type,
            })

    return {
        "count": len(items),
        "items": items,
    }


def dashboard_summary(db: Session, tenant_id: str, tenant_name: str) -> dict:
    ready = readiness(db, tenant_id)
    exc = exceptions(db, tenant_id)

    recent_holds = (
        db.query(models.PacketReleaseHold)
        .filter(models.PacketReleaseHold.tenant_id == tenant_id)
        .order_by(models.PacketReleaseHold.id.desc())
        .limit(10)
        .all()
    )

    recent_overrides = (
        db.query(models.PacketReleaseOverride)
        .filter(models.PacketReleaseOverride.tenant_id == tenant_id)
        .order_by(models.PacketReleaseOverride.id.desc())
        .limit(10)
        .all()
    )

    recent_releases = (
        db.query(models.PacketRelease)
        .filter(models.PacketRelease.tenant_id == tenant_id)
        .order_by(models.PacketRelease.id.desc())
        .limit(10)
        .all()
    )

    return {
        "tenant_id": tenant_id,
        "tenant_name": tenant_name,
        "readiness_counts": ready["counts"],
        "exception_count": exc["count"],
        "recent_exceptions": exc["items"][:10],
        "recent_holds": [
            {
                "id": x.id,
                "packet_id": x.packet_id,
                "hold_type": x.hold_type,
                "reason": x.reason,
                "is_active": x.is_active,
                "created_at": x.created_at.isoformat() if x.created_at else None,
            }
            for x in recent_holds
        ],
        "recent_overrides": [
            {
                "id": x.id,
                "packet_id": x.packet_id,
                "override_type": x.override_type,
                "status": x.status,
                "approved_by": x.approved_by,
                "created_at": x.created_at.isoformat() if x.created_at else None,
            }
            for x in recent_overrides
        ],
        "recent_releases": [
            {
                "id": x.id,
                "packet_id": x.packet_id,
                "status": x.status,
                "requested_by": x.requested_by,
                "approver_email": x.approver_email,
                "created_at": x.created_at.isoformat() if x.created_at else None,
            }
            for x in recent_releases
        ],
    }
