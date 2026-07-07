from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Request
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.authz import require_roles
from app.deps import get_db
from app.db import models
from app.enterprise_auth import get_request_tenant_id

router = APIRouter(tags=["analytics"])

# "supervisor" is a distinct assignable role (see admin_users.ASSIGNABLE_ROLES)
# from "spd_manager" — both review inspections/baselines and need real KPIs
# rather than falling back to demo values.
_READ_ROLES = ("admin", "spd_manager", "supervisor", "operator", "viewer")
_FINDING_TYPES = ("blood", "bone", "tissue", "debris", "corrosion", "crack")


def _scoped(db: Session, *, role: str, tenant_id: str):
    """Every non-admin role is always scoped to a real tenant_id — never an
    unfiltered, platform-wide query. `tenant_id` is resolved by the caller
    with the same header/default-tenant fallback every other route in this
    app uses, so "unresolved" never means "skip the filter"; only an
    explicit `admin` role sees across tenants."""
    query = db.query(models.Inspection)
    if role != "admin":
        query = query.filter(models.Inspection.tenant_id == tenant_id)
    return query


@router.get("/analytics/kpi-summary")
def kpi_summary(
    request: Request,
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

    role = getattr(current_user, "role", "")
    tenant_id = getattr(current_user, "tenant_id", None) or get_request_tenant_id(request)

    # Counted at the database with COUNT(*)/DISTINCT rather than
    # materializing every matching Inspection row in Python — this endpoint
    # is polled by dashboards and the notification loop, so it must stay
    # cheap regardless of tenant history size.
    base = _scoped(db, role=role, tenant_id=tenant_id)

    total_inspections = base.count()
    high_risk_findings = base.filter(models.Inspection.risk_score >= 70).count()
    open_findings = base.filter(models.Inspection.status == "pending").count()
    images_collected = base.filter(models.Inspection.has_image.is_(True)).count()
    high_risk_instruments = (
        base.filter(models.Inspection.risk_score >= 70)
        .with_entities(models.Inspection.instrument_type)
        .distinct()
        .count()
    )
    finding_tally = {
        ft: base.filter(models.Inspection.detected_issue == ft).count()
        for ft in _FINDING_TYPES
    }

    # "This week" needs a timezone-safe comparison — SQLite can hand back a
    # naive datetime for a DateTime(timezone=True) column depending on
    # driver/version. Compared in Python on just the created_at column
    # (not full row objects) rather than in SQL, to stay portable.
    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)
    created_ats = base.with_entities(models.Inspection.created_at).all()
    inspections_this_week = sum(
        1 for (ts,) in created_ats
        if ts is not None and (ts if ts.tzinfo is not None else ts.replace(tzinfo=timezone.utc)) >= week_ago
    )

    # Baseline library is platform-wide (no tenant_id column) — same for every tenant.
    baseline_q = db.query(BaselineLibraryEntry)
    total_baselines = baseline_q.count()
    baselines_approved = baseline_q.filter(BaselineLibraryEntry.approval_status == "approved").count()
    baselines_pending = baseline_q.filter(BaselineLibraryEntry.approval_status == "pending").count()
    vendor_submissions = baseline_q.filter(BaselineLibraryEntry.baseline_type == "vendor").count()
    baseline_coverage_pct = (
        round(baselines_approved / total_baselines * 100, 1) if total_baselines else 0.0
    )

    capas = capa_summary()

    # The `users` table's physical schema can differ from the current ORM
    # mapping (the legacy login path in auth_simple._verify_user queries it
    # with raw SQL against username/password_hash columns) — a schema-agnostic
    # raw COUNT(*) never 500s the whole endpoint over this one optional field.
    try:
        total_users = db.execute(text("SELECT COUNT(*) FROM users")).scalar()
    except Exception:
        total_users = None

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
        # Nested shape some existing dashboards (ExecutiveCommandCenterPage,
        # CustomerSuccessDashboard) already read — kept alongside the flat
        # fields above rather than replacing them, so no caller regresses.
        "finding_categories": finding_tally,
        "total_baselines": total_baselines,
        "baselines_approved": baselines_approved,
        "baseline_coverage_pct": baseline_coverage_pct,
        "baselines": {
            "total": total_baselines,
            "approved": baselines_approved,
            "pending": baselines_pending,
            "vendor_submissions": vendor_submissions,
            "approval_rate": baseline_coverage_pct,
        },
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
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "spd_manager", "supervisor")),
):
    # Platform admins (role=="admin") see all rows; everyone else is always
    # scoped to their own resolved tenant — never left unfiltered.
    role = getattr(current_user, "role", "")
    tenant_id = getattr(current_user, "tenant_id", None) or get_request_tenant_id(request)

    rows = _scoped(db, role=role, tenant_id=tenant_id).all()

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
