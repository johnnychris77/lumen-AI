from __future__ import annotations

from sqlalchemy.orm import Session

from app.db import models


def get_distribution_list(db: Session, tenant_id: str, list_id: int):
    return (
        db.query(models.DistributionList)
        .filter(
            models.DistributionList.id == list_id,
            models.DistributionList.tenant_id == tenant_id,
            models.DistributionList.is_enabled == True,
        )
        .first()
    )


def get_enabled_recipients(db: Session, tenant_id: str, list_id: int) -> list[models.DistributionRecipient]:
    return (
        db.query(models.DistributionRecipient)
        .filter(
            models.DistributionRecipient.tenant_id == tenant_id,
            models.DistributionRecipient.list_id == list_id,
            models.DistributionRecipient.is_enabled == True,
        )
        .order_by(models.DistributionRecipient.id.asc())
        .all()
    )


def resolve_delivery_target(db: Session, tenant_id: str, raw_target: str, list_id: int = 0) -> dict:
    if not list_id:
        return {
            "mode": "raw_target",
            "requires_approval": False,
            "target": raw_target,
            "recipients": [],
            "allowed": bool(raw_target),
            "reason": "" if raw_target else "No delivery target configured",
        }

    dl = get_distribution_list(db, tenant_id, list_id)
    if not dl:
        return {
            "mode": "distribution_list",
            "requires_approval": False,
            "target": "",
            "recipients": [],
            "allowed": False,
            "reason": "Distribution list not found or disabled",
        }

    recipients = get_enabled_recipients(db, tenant_id, list_id)
    target = ",".join([r.recipient_email for r in recipients if r.recipient_email])

    return {
        "mode": "distribution_list",
        "distribution_list_id": dl.id,
        "distribution_list_name": dl.name,
        "audience_type": dl.audience_type,
        "requires_approval": bool(dl.requires_approval),
        "target": target,
        "recipients": [
            {
                "id": r.id,
                "email": r.recipient_email,
                "name": r.recipient_name,
                "role": r.recipient_role,
            }
            for r in recipients
        ],
        "allowed": bool(target) and not bool(dl.requires_approval),
        "reason": "Approval required before delivery" if dl.requires_approval else "",
    }
