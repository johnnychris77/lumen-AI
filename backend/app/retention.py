from __future__ import annotations

from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session

from app.db import models


DEFAULT_RETENTION_DAYS = {
    "inspection": 365,
    "audit_log": 365,
    "evidence_pack": 730,
    "digest_delivery": 365,
}


def get_retention_policy(db: Session, tenant_id: str, tenant_name: str, artifact_type: str) -> dict:
    row = (
        db.query(models.RetentionPolicy)
        .filter(
            models.RetentionPolicy.tenant_id == tenant_id,
            models.RetentionPolicy.artifact_type == artifact_type,
            models.RetentionPolicy.is_enabled == True,
        )
        .order_by(models.RetentionPolicy.id.desc())
        .first()
    )

    if row:
        return {
            "tenant_id": row.tenant_id,
            "tenant_name": row.tenant_name,
            "artifact_type": row.artifact_type,
            "retention_days": row.retention_days,
            "legal_hold_enabled": row.legal_hold_enabled,
            "notes": row.notes,
            "source": "policy",
        }

    return {
        "tenant_id": tenant_id,
        "tenant_name": tenant_name,
        "artifact_type": artifact_type,
        "retention_days": DEFAULT_RETENTION_DAYS.get(artifact_type, 365),
        "legal_hold_enabled": False,
        "notes": "",
        "source": "default",
    }


def compute_retention_metadata(db: Session, tenant_id: str, tenant_name: str, artifact_type: str) -> dict:
    policy = get_retention_policy(db, tenant_id, tenant_name, artifact_type)
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(days=int(policy["retention_days"]))

    return {
        **policy,
        "evaluated_at": now.isoformat(),
        "expires_at": expires_at.isoformat(),
        "deletion_blocked": bool(policy["legal_hold_enabled"]),
    }
