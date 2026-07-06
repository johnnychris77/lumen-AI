"""v1.9 — Pilot Data Collection Dashboard (Deliverable 6).

A rollup for the pilot lead to answer "is our dataset actually usable
yet?" — built entirely from real, already-persisted rows (Inspection,
BaselineLibraryEntry, SupervisorReview, PilotErrorLog) plus the data
quality guardrails' own evaluation. Nothing here is a separate analysis.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.db import models
from app.models.baseline_library import BaselineLibraryEntry
from app.models.pilot_error_log import AI_ANALYSIS_FAILURE, UPLOAD_FAILURE
from app.models.supervisor_review import SupervisorReview
from app.services.data_quality_guardrails_service import evaluate_data_quality
from app.services.pilot_error_log_service import count_by_type
from app.services.pilot_site_config_service import get_or_create_config


def pilot_data_collection_summary(db: Session, tenant_id: str) -> dict:
    config = get_or_create_config(db, tenant_id)

    inspections = db.query(models.Inspection).filter(models.Inspection.tenant_id == tenant_id).all()
    baseline_images_collected = (
        db.query(BaselineLibraryEntry)
        .filter(BaselineLibraryEntry.approval_status == "approved")
        .count()
    )
    inspection_images_collected = sum(1 for i in inspections if i.has_image)
    supervisor_reviews_completed = (
        db.query(SupervisorReview).filter(SupervisorReview.tenant_id == tenant_id).count()
    )

    evaluations = [evaluate_data_quality(i, pilot_config=config) for i in inspections]
    incomplete_inspections = [e for e in evaluations if not e["is_dataset_ready"]]
    missing_anatomy_zones = sum(
        1 for e in evaluations if any(issue["code"] == "missing_anatomy_zone" for issue in e["issues"])
    )
    dataset_ready_images = sum(1 for e in evaluations if e["is_dataset_ready"])

    failed_uploads = count_by_type(db, tenant_id, UPLOAD_FAILURE) + count_by_type(db, tenant_id, AI_ANALYSIS_FAILURE)

    return {
        "facility_name": config.facility_name,
        "department": config.department,
        "inspections_collected": len(inspections),
        "baseline_images_collected": baseline_images_collected,
        "inspection_images_collected": inspection_images_collected,
        "supervisor_reviews_completed": supervisor_reviews_completed,
        "incomplete_inspections": len(incomplete_inspections),
        "incomplete_inspection_details": incomplete_inspections[:20],
        "failed_uploads": failed_uploads,
        "missing_anatomy_zones": missing_anatomy_zones,
        "dataset_ready_images": dataset_ready_images,
        "human_review_required": True,
    }
