from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.db import models


DEFAULT_READINESS_ITEMS = [
    ("tenant_setup", "Tenant profile created", "customer_admin"),
    ("branding", "Workspace branding configured", "customer_admin"),
    ("distribution_lists", "Executive distribution lists configured", "customer_admin"),
    ("notification_templates", "Notification templates reviewed", "customer_admin"),
    ("sla_policies", "Governance SLA policies configured", "customer_admin"),
    ("release_governance", "Packet release governance validated", "customer_admin"),
    ("leadership_packets", "Leadership packet generation tested", "implementation_team"),
    ("security_access", "Admin roles and tenant access validated", "implementation_team"),
    ("data_isolation", "Tenant data isolation confirmed", "implementation_team"),
    ("go_live_approval", "Go-live approval completed", "executive_sponsor"),
]


DEFAULT_CHECKPOINTS = [
    ("implementation_complete", "Implementation checklist complete"),
    ("security_review", "Security and access review complete"),
    ("governance_review", "Governance and compliance review complete"),
    ("executive_signoff", "Executive sponsor sign-off complete"),
]


def _now():
    return datetime.now(timezone.utc)


def seed_readiness_items(db: Session, tenant_id: str, tenant_name: str) -> None:
    existing = (
        db.query(models.ImplementationReadinessItem)
        .filter(models.ImplementationReadinessItem.tenant_id == tenant_id)
        .count()
    )
    if existing:
        return

    for key, title, owner in DEFAULT_READINESS_ITEMS:
        db.add(models.ImplementationReadinessItem(
            tenant_id=tenant_id,
            tenant_name=tenant_name,
            category="go_live",
            item_key=key,
            title=title,
            owner=owner,
            status="not_started",
            is_required=True,
        ))

    for key, title in DEFAULT_CHECKPOINTS:
        db.add(models.GoLiveCheckpoint(
            tenant_id=tenant_id,
            tenant_name=tenant_name,
            checkpoint_key=key,
            title=title,
            status="pending",
            is_required=True,
        ))

    db.commit()


def readiness_summary(db: Session, tenant_id: str, tenant_name: str) -> dict:
    seed_readiness_items(db, tenant_id, tenant_name)

    items = (
        db.query(models.ImplementationReadinessItem)
        .filter(models.ImplementationReadinessItem.tenant_id == tenant_id)
        .order_by(models.ImplementationReadinessItem.id.asc())
        .all()
    )
    checkpoints = (
        db.query(models.GoLiveCheckpoint)
        .filter(models.GoLiveCheckpoint.tenant_id == tenant_id)
        .order_by(models.GoLiveCheckpoint.id.asc())
        .all()
    )

    required_items = [x for x in items if x.is_required]
    completed_required = [x for x in required_items if x.status == "completed"]
    blocked = [x for x in items if x.status == "blocked"]
    checkpoint_required = [x for x in checkpoints if x.is_required]
    checkpoint_approved = [x for x in checkpoint_required if x.status == "approved"]

    readiness_score = round((len(completed_required) / len(required_items)) * 100, 2) if required_items else 100
    checkpoint_score = round((len(checkpoint_approved) / len(checkpoint_required)) * 100, 2) if checkpoint_required else 100

    go_live_ready = readiness_score == 100 and checkpoint_score == 100 and not blocked

    counts = Counter([x.status for x in items])
    checkpoint_counts = Counter([x.status for x in checkpoints])

    return {
        "tenant_id": tenant_id,
        "tenant_name": tenant_name,
        "readiness_score": readiness_score,
        "checkpoint_score": checkpoint_score,
        "go_live_ready": go_live_ready,
        "blocked_count": len(blocked),
        "item_counts": dict(counts),
        "checkpoint_counts": dict(checkpoint_counts),
        "items": [
            {
                "id": x.id,
                "category": x.category,
                "item_key": x.item_key,
                "title": x.title,
                "owner": x.owner,
                "status": x.status,
                "is_required": x.is_required,
                "blocker_reason": x.blocker_reason,
                "completed_by": x.completed_by,
                "notes": x.notes,
                "created_at": x.created_at.isoformat() if x.created_at else None,
                "updated_at": x.updated_at.isoformat() if x.updated_at else None,
            }
            for x in items
        ],
        "checkpoints": [
            {
                "id": x.id,
                "checkpoint_key": x.checkpoint_key,
                "title": x.title,
                "status": x.status,
                "approved_by": x.approved_by,
                "approved_role": x.approved_role,
                "approval_notes": x.approval_notes,
                "is_required": x.is_required,
                "created_at": x.created_at.isoformat() if x.created_at else None,
                "approved_at": x.approved_at.isoformat() if x.approved_at else None,
            }
            for x in checkpoints
        ],
    }


def complete_item(db: Session, tenant_id: str, item_id: int, actor_email: str, notes: str = ""):
    row = (
        db.query(models.ImplementationReadinessItem)
        .filter(
            models.ImplementationReadinessItem.id == item_id,
            models.ImplementationReadinessItem.tenant_id == tenant_id,
        )
        .first()
    )
    if not row:
        raise ValueError("Readiness item not found")

    row.status = "completed"
    row.completed_by = actor_email
    row.blocker_reason = ""
    row.notes = notes or row.notes
    row.updated_at = _now()
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def block_item(db: Session, tenant_id: str, item_id: int, blocker_reason: str, notes: str = ""):
    row = (
        db.query(models.ImplementationReadinessItem)
        .filter(
            models.ImplementationReadinessItem.id == item_id,
            models.ImplementationReadinessItem.tenant_id == tenant_id,
        )
        .first()
    )
    if not row:
        raise ValueError("Readiness item not found")

    row.status = "blocked"
    row.blocker_reason = blocker_reason
    row.notes = notes or row.notes
    row.updated_at = _now()
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def approve_checkpoint(db: Session, tenant_id: str, checkpoint_id: int, actor_email: str, actor_role: str, notes: str = ""):
    row = (
        db.query(models.GoLiveCheckpoint)
        .filter(
            models.GoLiveCheckpoint.id == checkpoint_id,
            models.GoLiveCheckpoint.tenant_id == tenant_id,
        )
        .first()
    )
    if not row:
        raise ValueError("Go-live checkpoint not found")

    row.status = "approved"
    row.approved_by = actor_email
    row.approved_role = actor_role
    row.approval_notes = notes
    row.approved_at = _now()
    db.add(row)
    db.commit()
    db.refresh(row)
    return row
