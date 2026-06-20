from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.authz import require_roles
from app.deps import get_db
from app.db import models

router = APIRouter(tags=["analytics"])


@router.get("/analytics/powerbi")
def powerbi_dataset(
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "spd_manager")),
):
    # Platform admins (role=="admin" with no tenant_id) see all rows;
    # everyone else is scoped to their own tenant.
    tenant_id = getattr(current_user, "tenant_id", None)
    role = getattr(current_user, "role", "")

    query = db.query(models.Inspection)
    if role != "admin" and tenant_id:
        query = query.filter(models.Inspection.tenant_id == tenant_id)

    rows = query.all()

    return [
        {
            "inspection_id": r.id,
            "instrument_type": r.instrument_type,
            "detected_issue": r.detected_issue,
            "material_type": r.material_type,
            "confidence": r.confidence,
            "status": r.status,
            "timestamp": r.created_at,
        }
        for r in rows
    ]
