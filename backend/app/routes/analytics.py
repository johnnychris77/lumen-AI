from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.authz import require_roles
from app.deps import get_db
from app.db import models

router = APIRouter(tags=["analytics"])

_READ_ROLES = ("admin", "spd_manager", "operator", "viewer")
_FINDING_TYPES = ("blood", "bone", "tissue", "debris", "corrosion", "crack")


@router.get("/analytics/kpi-summary")
def kpi_summary(
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_READ_ROLES)),
):
    """Cross-page executive KPI summary, computed from real stored data.

    Was previously called by ~15 frontend pages (dashboards, executive
    consoles, notifications) with no backend route at all, always 404ing —
    every caller already treats each field as optional and falls back to a
    demo value, so nothing crashed, but no real number was ever shown.

    Fields that aren't honestly computable yet (active-user counts, review
    turnaround time, login frequency, adoption rate) are simply omitted
    rather than fabricated.
    """
    from app.models.baseline_library import BaselineLibraryEntry
    from app.services.capa_service import capa_summary

    tenant_id = getattr(current_user, "tenant_id", None)
    role = getattr(current_user, "role", "")

    query = db.query(models.Inspection)
    if role != "admin" and tenant_id:
        query = query.filter(models.Inspection.tenant_id == tenant_id)
    rows = query.all()

    total_inspections = len(rows)
    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)

    def _created_at_aware(r) -> datetime | None:
        # SQLite can hand back a naive datetime for a DateTime(timezone=True)
        # column depending on driver/version — normalize before comparing so
        # this never raises on an offset-naive vs. offset-aware mismatch.
        if r.created_at is None:
            return None
        return r.created_at if r.created_at.tzinfo is not None else r.created_at.replace(tzinfo=timezone.utc)

    inspections_this_week = sum(
        1 for r in rows
        if (ts := _created_at_aware(r)) is not None and ts >= week_ago
    )

    high_risk_findings = sum(1 for r in rows if r.risk_score >= 70)
    open_findings = sum(1 for r in rows if r.status == "pending")
    images_collected = sum(1 for r in rows if r.has_image)
    high_risk_instruments = len({r.instrument_type for r in rows if r.risk_score >= 70})

    finding_tally = dict.fromkeys(_FINDING_TYPES, 0)
    for r in rows:
        if r.detected_issue in finding_tally:
            finding_tally[r.detected_issue] += 1

    # Baseline library is platform-wide (no tenant_id column).
    baselines = db.query(BaselineLibraryEntry).all()
    total_baselines = len(baselines)
    baselines_approved = sum(1 for b in baselines if b.approval_status == "approved")
    baseline_coverage_pct = (
        round(baselines_approved / total_baselines * 100, 1) if total_baselines else 0.0
    )

    capas = capa_summary()
    total_users = db.query(models.User).count()

    return {
        "total_inspections": total_inspections,
        "inspections_this_week": inspections_this_week,
        "high_risk_findings": high_risk_findings,
        "open_findings": open_findings,
        "review_backlog": open_findings,
        "images_collected": images_collected,
        "high_risk_instruments": high_risk_instruments,
        "blood_findings": finding_tally["blood"],
        "bone_findings": finding_tally["bone"],
        "tissue_findings": finding_tally["tissue"],
        "debris_findings": finding_tally["debris"],
        "corrosion_findings": finding_tally["corrosion"],
        "crack_findings": finding_tally["crack"],
        "total_baselines": total_baselines,
        "baselines_approved": baselines_approved,
        "baseline_coverage_pct": baseline_coverage_pct,
        "total_capas": capas["total"],
        "open_capas": capas["open"],
        "completed_capas": capas["closed"],
        "total_users": total_users,
        "human_review_required": True,
        "note": (
            "Computed from real stored data. Fields not yet computable (active-user "
            "counts, adoption rate, review turnaround time, login frequency) are "
            "omitted rather than fabricated."
        ),
    }


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
