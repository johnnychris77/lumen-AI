"""v1.6 — Readiness Dashboard (Deliverable 7) & Enterprise Readiness Analytics
(Deliverable 9).

Aggregates real per-inspection readiness/disposition computations — nothing
here is a separate analysis, just rollups of what readiness_engine and
disposition_engine already compute per inspection.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.db import models
from app.models.disposition_override import DispositionOverride
from app.models.supervisor_review import SupervisorReview
from app.services.disposition_engine import recommend_disposition
from app.services.instrument_anatomy import resolve_family
from app.services.readiness_engine import (
    PENDING_SUPERVISOR_REVIEW,
    READY,
    READY_WITH_SUPERVISOR_APPROVAL,
    REMOVE_FROM_SERVICE_STATUS,
    REQUIRES_RECLEANING_STATUS,
    REQUIRES_REPAIR_STATUS,
    compute_readiness,
    get_primary_finding_type,
)


def _reviewed_ids(db: Session, tenant_id: str) -> set[int]:
    rows = db.query(SupervisorReview.inspection_id).filter(SupervisorReview.tenant_id == tenant_id).all()
    return {r[0] for r in rows}


def _classify_all(db: Session, tenant_id: str, since_days: int | None = None) -> list[dict]:
    query = db.query(models.Inspection).filter(
        models.Inspection.tenant_id == tenant_id, models.Inspection.has_image.is_(True),
    )
    if since_days is not None:
        since = datetime.now(timezone.utc) - timedelta(days=since_days)
        query = query.filter(models.Inspection.created_at >= since)
    rows = query.all()

    reviewed_ids = _reviewed_ids(db, tenant_id)
    latest_reviews: dict[int, SupervisorReview] = {}
    if rows:
        reviews = (
            db.query(SupervisorReview)
            .filter(SupervisorReview.inspection_id.in_([r.id for r in rows]))
            .order_by(SupervisorReview.id.desc())
            .all()
        )
        for r in reviews:
            latest_reviews.setdefault(r.inspection_id, r)

    results = []
    for insp in rows:
        confirmed = insp.id in reviewed_ids
        review = latest_reviews.get(insp.id)
        primary_finding_type = get_primary_finding_type(db, insp)
        readiness = compute_readiness(
            db, tenant_id, insp, confirmed=confirmed,
            override_action=(review.override_action if review else ""),
        )
        disposition = recommend_disposition(
            readiness, insp, coverage_pct=insp.coverage_pct, primary_finding_type=primary_finding_type,
        )
        results.append({"inspection": insp, "readiness": readiness, "disposition": disposition})
    return results


def readiness_dashboard(db: Session, tenant_id: str) -> dict:
    """Deliverable 7 — /clinical-readiness dashboard."""
    classified = _classify_all(db, tenant_id)

    by_status = defaultdict(int)
    scores = []
    for c in classified:
        by_status[c["readiness"]["status"]] += 1
        if c["readiness"]["readiness_score"] is not None:
            scores.append(c["readiness"]["readiness_score"])

    by_disposition = defaultdict(int)
    for c in classified:
        by_disposition[c["disposition"]["disposition"]] += 1

    return {
        "ready_for_packaging": by_status[READY] + by_status[READY_WITH_SUPERVISOR_APPROVAL],
        "requires_recleaning": by_status[REQUIRES_RECLEANING_STATUS],
        "requires_repair": by_status[REQUIRES_REPAIR_STATUS],
        "remove_from_service": by_status[REMOVE_FROM_SERVICE_STATUS],
        "supervisor_pending": by_status[PENDING_SUPERVISOR_REVIEW],
        "average_readiness_score": round(sum(scores) / len(scores), 1) if scores else None,
        "disposition_trends": dict(by_disposition),
        "total_inspections": len(classified),
        "human_review_required": True,
    }


def enterprise_readiness_analytics(db: Session, tenant_id: str, days: int = 180) -> dict:
    """Deliverable 9 — readiness trends, disposition distribution, supervisor
    overrides, repair referrals, high-risk families, common disposition
    reasons."""
    classified = _classify_all(db, tenant_id, since_days=days)

    by_disposition = defaultdict(int)
    reasons_by_disposition: dict[str, list[str]] = defaultdict(list)
    for c in classified:
        disp = c["disposition"]["disposition"]
        by_disposition[disp] += 1
        reasons_by_disposition[disp].append(c["disposition"]["explanation"])

    overrides = (
        db.query(DispositionOverride)
        .filter(DispositionOverride.tenant_id == tenant_id)
        .all()
    )
    overrides_by_action = defaultdict(int)
    for o in overrides:
        overrides_by_action[o.action] += 1

    repair_referrals = sum(
        1 for c in classified
        if c["disposition"]["disposition"] in ("Repair Evaluation", "Manufacturer Evaluation")
    )

    by_family = defaultdict(lambda: {"total": 0, "high_risk": 0})
    for c in classified:
        family = resolve_family(c["inspection"].instrument_type)
        by_family[family]["total"] += 1
        if c["readiness"]["is_critical_finding"]:
            by_family[family]["high_risk"] += 1

    high_risk_families = sorted(
        (
            {
                "family": f, "total": d["total"], "high_risk_count": d["high_risk"],
                "high_risk_rate_pct": round(100 * d["high_risk"] / d["total"], 1) if d["total"] else None,
            }
            for f, d in by_family.items()
        ),
        key=lambda x: x["high_risk_count"], reverse=True,
    )

    # Most common disposition reason per disposition (the most frequent
    # explanation string, not a fabricated summary).
    common_reasons = {}
    for disp, reasons in reasons_by_disposition.items():
        counts = defaultdict(int)
        for r in reasons:
            counts[r] += 1
        common_reasons[disp] = max(counts.items(), key=lambda kv: kv[1])[0]

    return {
        "period_days": days,
        "readiness_trends": {
            "total_inspections": len(classified),
            "average_readiness_score": (
                round(sum(c["readiness"]["readiness_score"] for c in classified if c["readiness"]["readiness_score"] is not None)
                      / max(1, sum(1 for c in classified if c["readiness"]["readiness_score"] is not None)), 1)
                if any(c["readiness"]["readiness_score"] is not None for c in classified) else None
            ),
        },
        "disposition_distribution": dict(by_disposition),
        "supervisor_overrides": dict(overrides_by_action),
        "repair_referrals": repair_referrals,
        "high_risk_instrument_families": high_risk_families,
        "most_common_disposition_reasons": common_reasons,
        "human_review_required": True,
    }
