from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.db import models
from app.report_delivery import deliver_report


DEFAULT_POLICIES = {
    "pending_packet_release": 24,
    "active_release_hold": 48,
    "blocked_packet_delivery": 4,
    "failed_packet_delivery": 4,
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _age_hours(dt) -> int:
    if not dt:
        return 0
    age = _now() - dt
    return max(0, int(age.total_seconds() // 3600))


def _compact(value: Any) -> str:
    return json.dumps(value, default=str)[:4000]


def get_policy(db: Session, tenant_id: str, tenant_name: str, policy_key: str):
    row = (
        db.query(models.GovernanceSlaPolicy)
        .filter(
            models.GovernanceSlaPolicy.tenant_id == tenant_id,
            models.GovernanceSlaPolicy.policy_key == policy_key,
            models.GovernanceSlaPolicy.is_enabled == True,
        )
        .order_by(models.GovernanceSlaPolicy.id.desc())
        .first()
    )
    if row:
        return row

    return models.GovernanceSlaPolicy(
        tenant_id=tenant_id,
        tenant_name=tenant_name,
        policy_key=policy_key,
        threshold_hours=DEFAULT_POLICIES.get(policy_key, 24),
        escalation_channel="",
        escalation_target="",
        is_enabled=True,
        notes="Default runtime policy",
    )


def _existing_open_event(db: Session, tenant_id: str, policy_key: str, resource_type: str, resource_id: int):
    return (
        db.query(models.GovernanceSlaEvent)
        .filter(
            models.GovernanceSlaEvent.tenant_id == tenant_id,
            models.GovernanceSlaEvent.policy_key == policy_key,
            models.GovernanceSlaEvent.resource_type == resource_type,
            models.GovernanceSlaEvent.resource_id == resource_id,
            models.GovernanceSlaEvent.status == "open",
        )
        .first()
    )


def create_sla_event(
    db: Session,
    *,
    tenant_id: str,
    tenant_name: str,
    policy,
    resource_type: str,
    resource_id: int,
    age_hours: int,
    details: dict,
):
    existing = _existing_open_event(db, tenant_id, policy.policy_key, resource_type, resource_id)
    if existing:
        return existing, False

    severity = "critical" if age_hours >= policy.threshold_hours * 2 else "warning"

    row = models.GovernanceSlaEvent(
        tenant_id=tenant_id,
        tenant_name=tenant_name,
        policy_key=policy.policy_key,
        resource_type=resource_type,
        resource_id=resource_id,
        severity=severity,
        age_hours=age_hours,
        status="open",
        escalation_channel=policy.escalation_channel,
        escalation_target=policy.escalation_target,
        details_json=_compact(details),
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    if policy.escalation_channel and policy.escalation_target:
        deliver_report(policy.escalation_channel, policy.escalation_target, {
            "tenant_id": tenant_id,
            "tenant_name": tenant_name,
            "report_type": "governance_sla_escalation",
            "resource_type": resource_type,
            "resource_id": resource_id,
            "policy_key": policy.policy_key,
            "age_hours": age_hours,
            "severity": severity,
        })

    return row, True


def evaluate_pending_releases(db: Session, tenant_id: str, tenant_name: str) -> list[dict]:
    policy = get_policy(db, tenant_id, tenant_name, "pending_packet_release")
    rows = (
        db.query(models.PacketRelease)
        .filter(
            models.PacketRelease.tenant_id == tenant_id,
            models.PacketRelease.status == "pending",
        )
        .all()
    )

    results = []
    for row in rows:
        age = _age_hours(row.created_at)
        if age >= policy.threshold_hours:
            event, created = create_sla_event(
                db,
                tenant_id=tenant_id,
                tenant_name=tenant_name,
                policy=policy,
                resource_type="packet_release",
                resource_id=row.id,
                age_hours=age,
                details={
                    "packet_id": row.packet_id,
                    "packet_title": row.packet_title,
                    "requested_by": row.requested_by,
                    "status": row.status,
                },
            )
            results.append({"resource_type": "packet_release", "resource_id": row.id, "event_id": event.id, "created": created})
    return results


def evaluate_active_holds(db: Session, tenant_id: str, tenant_name: str) -> list[dict]:
    policy = get_policy(db, tenant_id, tenant_name, "active_release_hold")
    rows = (
        db.query(models.PacketReleaseHold)
        .filter(
            models.PacketReleaseHold.tenant_id == tenant_id,
            models.PacketReleaseHold.is_active == True,
        )
        .all()
    )

    results = []
    for row in rows:
        age = _age_hours(row.created_at)
        if age >= policy.threshold_hours:
            event, created = create_sla_event(
                db,
                tenant_id=tenant_id,
                tenant_name=tenant_name,
                policy=policy,
                resource_type="packet_release_hold",
                resource_id=row.id,
                age_hours=age,
                details={
                    "packet_id": row.packet_id,
                    "hold_type": row.hold_type,
                    "reason": row.reason,
                    "placed_by": row.placed_by,
                },
            )
            results.append({"resource_type": "packet_release_hold", "resource_id": row.id, "event_id": event.id, "created": created})
    return results


def evaluate_deliveries(db: Session, tenant_id: str, tenant_name: str) -> list[dict]:
    results = []

    for status, policy_key in [("blocked", "blocked_packet_delivery"), ("failed", "failed_packet_delivery")]:
        policy = get_policy(db, tenant_id, tenant_name, policy_key)
        rows = (
            db.query(models.LeadershipPacketDelivery)
            .filter(
                models.LeadershipPacketDelivery.tenant_id == tenant_id,
                models.LeadershipPacketDelivery.delivery_status == status,
            )
            .all()
        )

        for row in rows:
            age = _age_hours(row.created_at)
            if age >= policy.threshold_hours:
                event, created = create_sla_event(
                    db,
                    tenant_id=tenant_id,
                    tenant_name=tenant_name,
                    policy=policy,
                    resource_type="leadership_packet_delivery",
                    resource_id=row.id,
                    age_hours=age,
                    details={
                        "packet_id": row.packet_id,
                        "schedule_id": row.schedule_id,
                        "delivery_status": row.delivery_status,
                        "delivery_channel": row.delivery_channel,
                        "delivery_target": row.delivery_target,
                    },
                )
                results.append({
                    "resource_type": "leadership_packet_delivery",
                    "resource_id": row.id,
                    "event_id": event.id,
                    "created": created,
                })

    return results


def run_sla_evaluation(db: Session, tenant_id: str, tenant_name: str) -> dict:
    pending = evaluate_pending_releases(db, tenant_id, tenant_name)
    holds = evaluate_active_holds(db, tenant_id, tenant_name)
    deliveries = evaluate_deliveries(db, tenant_id, tenant_name)

    return {
        "tenant_id": tenant_id,
        "tenant_name": tenant_name,
        "pending_releases": pending,
        "active_holds": holds,
        "deliveries": deliveries,
        "created_count": sum(1 for x in pending + holds + deliveries if x.get("created")),
        "evaluated_count": len(pending) + len(holds) + len(deliveries),
    }


def sla_dashboard(db: Session, tenant_id: str, tenant_name: str) -> dict:
    events = (
        db.query(models.GovernanceSlaEvent)
        .filter(models.GovernanceSlaEvent.tenant_id == tenant_id)
        .order_by(models.GovernanceSlaEvent.id.desc())
        .limit(200)
        .all()
    )

    counts = Counter()
    for row in events:
        counts[row.status] += 1
        counts[row.severity] += 1
        counts[row.policy_key] += 1

    open_events = [x for x in events if x.status == "open"]

    return {
        "tenant_id": tenant_id,
        "tenant_name": tenant_name,
        "counts": dict(counts),
        "open_count": len(open_events),
        "open_events": [
            {
                "id": x.id,
                "policy_key": x.policy_key,
                "resource_type": x.resource_type,
                "resource_id": x.resource_id,
                "severity": x.severity,
                "age_hours": x.age_hours,
                "status": x.status,
                "details_json": x.details_json,
                "created_at": x.created_at.isoformat() if x.created_at else None,
            }
            for x in open_events[:50]
        ],
    }
