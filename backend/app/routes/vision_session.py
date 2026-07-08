"""v2.2 — Vision Intelligence & Multi-Image Clinical Reasoning ("Project
Vision 360").

- GET  /api/inspections/{id}/vision-session — the full multi-image session
  view: image timeline, missing-anatomy prompts, duplicate/wrong-anatomy/
  wrong-instrument warnings, cross-image reasoning, and the fused clinical
  recommendation.
- GET  /api/inspections/{id}/gallery — captured images grouped by anatomy
  zone, for the Inspection Gallery.
- POST /api/inspections/{id}/images/{tag_id}/flag — flag/unflag one
  captured image with a reason.
"""
from __future__ import annotations

from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.authz import require_roles
from app.db import models
from app.deps import get_db
from app.models.inspection_finding import InspectionFinding
from app.models.inspection_image_tag import InspectionImageTag
from app.models.supervisor_review import SupervisorReview
from app.services.duplicate_detection_service import detect_all
from app.services.vision_session_engine import (
    cross_image_reasoning, evidence_fusion, image_timeline, missing_anatomy_prompts, tag_to_dict,
)

router = APIRouter(tags=["vision-session"])

_READ_ROLES = ("admin", "spd_manager", "supervisor", "operator", "viewer")
_SEVERITY_STATUS = {0: "clear", 1: "monitor", 2: "review", 3: "escalate"}


def _get_inspection(db: Session, inspection_id: int, tenant_id: str | None, is_admin: bool) -> models.Inspection:
    query = db.query(models.Inspection).filter(models.Inspection.id == inspection_id)
    if tenant_id and not is_admin:
        query = query.filter(models.Inspection.tenant_id == tenant_id)
    row = query.first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inspection not found.")
    return row


def _reconstruct_predicted_findings(db: Session, inspection_id: int) -> list[dict]:
    """Real per-finding rows already persisted at analysis time
    (app/models/inspection_finding.py) — not a re-run of the scoring
    engine. Confidence isn't persisted per-finding, so it's omitted rather
    than fabricated."""
    rows = db.query(InspectionFinding).filter(InspectionFinding.inspection_id == inspection_id).all()
    return [
        {
            "type": r.finding_type,
            "instrument_zone": r.zone,
            "severity_index": r.severity_index,
            "status": _SEVERITY_STATUS.get(r.severity_index, "clear"),
            "confidence": None,
        }
        for r in rows
    ]


@router.get("/inspections/{inspection_id}/vision-session")
def get_vision_session(
    inspection_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_READ_ROLES)),
):
    """Objectives 1-2, 5-7 — the full multi-image session view."""
    from app.services.inspection_coverage import compute_coverage

    tenant_id = getattr(current_user, "tenant_id", None)
    is_admin = getattr(current_user, "role", "") == "admin"
    insp = _get_inspection(db, inspection_id, tenant_id, is_admin)

    tags = (
        db.query(InspectionImageTag)
        .filter(InspectionImageTag.inspection_id == inspection_id)
        .order_by(InspectionImageTag.id.asc())
        .all()
    )
    tag_dicts = [tag_to_dict(t) for t in tags]

    predicted_findings = _reconstruct_predicted_findings(db, inspection_id)
    supervisor_reviews = (
        db.query(SupervisorReview).filter(SupervisorReview.inspection_id == inspection_id).all()
    )
    captured_zones = [t["anatomy_zone"] for t in tag_dicts if t["anatomy_zone"]]
    coverage = compute_coverage(insp.instrument_type, captured_zones or None)

    return {
        "inspection_id": inspection_id,
        "instrument_type": insp.instrument_type,
        "image_count": len(tag_dicts),
        "images": tag_dicts,
        "image_timeline": image_timeline(tag_dicts),
        "missing_anatomy": missing_anatomy_prompts(insp.instrument_type, tag_dicts),
        "duplicate_detection": detect_all(tag_dicts),
        "cross_image_reasoning": cross_image_reasoning(predicted_findings, tag_dicts),
        "evidence_fusion": evidence_fusion(
            predicted_findings=predicted_findings,
            tag_dicts=tag_dicts,
            coverage=coverage,
            baseline_source=insp.baseline_source,
            supervisor_reviews=supervisor_reviews,
        ),
        "human_review_required": True,
    }


@router.get("/inspections/{inspection_id}/gallery")
def get_inspection_gallery(
    inspection_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_READ_ROLES)),
):
    """Objective 9 — Inspection Gallery: captured images grouped by anatomy
    zone, each with its quality band and flag state."""
    tenant_id = getattr(current_user, "tenant_id", None)
    is_admin = getattr(current_user, "role", "") == "admin"
    _get_inspection(db, inspection_id, tenant_id, is_admin)

    tags = (
        db.query(InspectionImageTag)
        .filter(InspectionImageTag.inspection_id == inspection_id)
        .order_by(InspectionImageTag.id.asc())
        .all()
    )

    groups: dict[str, list[dict]] = defaultdict(list)
    for t in tags:
        groups[t.anatomy_zone or "unspecified"].append(tag_to_dict(t))

    return {
        "inspection_id": inspection_id,
        "groups": [
            {"anatomy_zone": zone, "images": images}
            for zone, images in sorted(groups.items())
        ],
        "total_images": len(tags),
    }


class FlagImageIn(BaseModel):
    flagged: bool = Field(True)
    reason: str = Field("", max_length=500)


@router.post("/inspections/{inspection_id}/images/{tag_id}/flag")
def flag_image(
    inspection_id: int,
    tag_id: int,
    body: FlagImageIn,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "spd_manager", "supervisor")),
):
    """Flag (or clear a flag on) one captured image — e.g. duplicate, wrong
    anatomy, needs recapture. Supervisor/admin/spd_manager only."""
    tenant_id = getattr(current_user, "tenant_id", None)
    is_admin = getattr(current_user, "role", "") == "admin"
    _get_inspection(db, inspection_id, tenant_id, is_admin)

    tag = (
        db.query(InspectionImageTag)
        .filter(InspectionImageTag.id == tag_id, InspectionImageTag.inspection_id == inspection_id)
        .first()
    )
    if tag is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found on this inspection.")

    tag.flagged = body.flagged
    tag.flag_reason = body.reason if body.flagged else ""
    db.commit()

    return {"id": tag.id, "flagged": tag.flagged, "flag_reason": tag.flag_reason}
