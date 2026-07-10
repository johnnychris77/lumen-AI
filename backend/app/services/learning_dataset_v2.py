"""v2.0 — Learning Dataset v2.

Assembles the anatomy-aware training/label dataset the v2.0 sprint asks for
(instrument family, manufacturer, anatomy zone, zone risk, inspection view,
finding, supervisor correction, final outcome) by joining rows that already
exist — Inspection, InspectionImageTag, SupervisorReview — never a separate,
duplicated table. Every row traces back to a real supervisor-reviewed
inspection; nothing here is synthesized.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.db import models
from app.models.inspection_image_tag import InspectionImageTag
from app.models.supervisor_review import SupervisorReview
from app.services.instrument_anatomy import resolve_family
from app.services.zone_intelligence import zone_risk_for_family


def learning_dataset_v2(db: Session, tenant_id: str, limit: int = 500) -> dict:
    """Real, joined learning-dataset rows for one tenant, most recent first."""
    reviews = (
        db.query(SupervisorReview)
        .filter(SupervisorReview.tenant_id == tenant_id)
        .order_by(SupervisorReview.id.desc())
        .limit(limit)
        .all()
    )

    insp_ids = [r.inspection_id for r in reviews]
    inspections: dict[int, models.Inspection] = {}
    tags_by_inspection: dict[int, list[InspectionImageTag]] = {}
    if insp_ids:
        # Scoped by tenant_id too — a SupervisorReview row's inspection_id
        # should already belong to the same tenant, but the export must
        # never trust that without checking: an inspection/tag row from a
        # different tenant must not leak into this tenant's dataset.
        inspections = {
            i.id: i
            for i in db.query(models.Inspection)
            .filter(models.Inspection.id.in_(insp_ids), models.Inspection.tenant_id == tenant_id)
            .all()
        }
        for t in (
            db.query(InspectionImageTag)
            .filter(InspectionImageTag.inspection_id.in_(insp_ids), InspectionImageTag.tenant_id == tenant_id)
            .order_by(InspectionImageTag.id.asc())
            .all()
        ):
            tags_by_inspection.setdefault(t.inspection_id, []).append(t)

    rows = []
    for r in reviews:
        insp = inspections.get(r.inspection_id)
        tags = tags_by_inspection.get(r.inspection_id, [])
        anatomy_zone = r.corrected_zone or r.ai_zone or None
        family = r.instrument_family or (resolve_family(insp.instrument_type) if insp else "")
        zone_risk = zone_risk_for_family(family, anatomy_zone) if anatomy_zone and family else None
        # Prefer the tag whose own anatomy_zone matches the zone under
        # review — several zone names are ambiguous across image tags
        # (e.g. an overview shot vs. the reviewed zone's own close-up), so
        # falling back to "the first tag" can label the wrong view.
        matching_tag = next((t for t in tags if anatomy_zone and t.anatomy_zone == anatomy_zone), None)
        inspection_view = (matching_tag or (tags[0] if tags else None))
        inspection_view = inspection_view.image_view if inspection_view else None
        rows.append({
            "inspection_id": r.inspection_id,
            "instrument_family": family,
            "manufacturer": insp.vendor_name if insp else "",
            "anatomy_zone": anatomy_zone,
            "zone_risk": zone_risk,
            "inspection_view": inspection_view,
            "finding": r.finding_type or None,
            "supervisor_correction": {
                "agreement": r.agreement,
                "instrument_family_correct": r.instrument_family_correct,
                "zone_correct": r.zone_correct,
                "corrected_instrument_family": r.corrected_instrument_family or None,
                "corrected_zone": r.corrected_zone or None,
                "corrected_recommendation": r.corrected_recommendation or None,
            },
            "final_outcome": r.final_disposition or r.ground_truth or None,
            "reviewed_at": r.created_at.isoformat() if r.created_at else None,
        })

    return {
        "tenant_id": tenant_id,
        "count": len(rows),
        "rows": rows,
        "human_review_required": True,
        "note": "Every row is derived from a real supervisor-reviewed inspection — nothing synthesized.",
    }
