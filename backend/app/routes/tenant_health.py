"""P14: Customer health score API."""
from __future__ import annotations

import hashlib
import random
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.deps import get_db
from app.enterprise_auth import require_enterprise_auth

router = APIRouter(prefix="/api/tenant", tags=["tenant-health"])


def _seed(s: str) -> random.Random:
    h = hashlib.md5(s.encode()).hexdigest()[:8]  # noqa: S324
    return random.Random(int(h, 16))


def _compute_health_score(
    login_activity: int,
    inspection_volume: int,
    override_rate: float,
    support_tickets: int,
) -> dict:
    """Compute health score from components (each worth 25 pts)."""
    # login_activity_score: 0-25 (full score at >= 20 logins/month)
    login_score = min(25, int(login_activity / 20 * 25))

    # inspection_volume_score: 0-25 (full score at >= 500 inspections)
    inspection_score = min(25, int(inspection_volume / 500 * 25))

    # override_rate_score: 0-25 (full at <= 5%, decreases above)
    if override_rate <= 5.0:
        override_score = 25
    elif override_rate >= 30.0:
        override_score = 0
    else:
        override_score = int(25 * (1 - (override_rate - 5.0) / 25.0))

    # engagement_score: 0-25 (low support tickets = high engagement score)
    if support_tickets == 0:
        engagement_score = 25
    elif support_tickets >= 10:
        engagement_score = 0
    else:
        engagement_score = int(25 * (1 - support_tickets / 10))

    total = login_score + inspection_score + override_score + engagement_score

    if total >= 70:
        tier = "green"
    elif total >= 40:
        tier = "yellow"
    else:
        tier = "red"

    return {
        "score": total,
        "tier": tier,
        "components": {
            "login_activity_score": login_score,
            "inspection_volume_score": inspection_score,
            "override_rate_score": override_score,
            "engagement_score": engagement_score,
        },
    }


@router.get("/health-score")
def tenant_health_score(
    request: Request,
    db: Session = Depends(get_db),
) -> dict:
    auth = require_enterprise_auth(request)
    tenant_id = auth.tenant_id

    # Try to load from DB first
    try:
        from app.models.tenant_health import TenantHealthScore
        record = (
            db.query(TenantHealthScore)
            .filter(TenantHealthScore.tenant_id == tenant_id)
            .order_by(TenantHealthScore.id.desc())
            .first()
        )
        if record is not None:
            result = _compute_health_score(
                record.login_activity,
                record.inspection_volume,
                record.override_rate,
                record.support_tickets,
            )
            result["computed_at"] = record.computed_at.isoformat()
            result["data_source"] = "db"
            return result
    except Exception:
        pass

    # Fallback: seeded mock
    rng = _seed(f"health:{tenant_id}")
    login_activity = rng.randint(5, 40)
    inspection_volume = rng.randint(100, 1000)
    override_rate = round(rng.uniform(1.0, 20.0), 1)
    support_tickets = rng.randint(0, 8)

    result = _compute_health_score(login_activity, inspection_volume, override_rate, support_tickets)
    result["computed_at"] = datetime.now(timezone.utc).isoformat()
    result["data_source"] = "mock"
    return result
