"""v4.8 — Project Athena, Section 4: Institutional Memory Timeline.

Composes Event -> Investigation -> CAPA -> Education -> Policy Change ->
Outcome -> Verification -> Future Similar Cases from six pre-existing
systems for a given finding type. There is no explicit foreign-key chain
linking a `ClinicalCase` to its eventual `QualityPolicy` change across this
codebase's existing models, so steps are joined by real, matching
`finding_type` values (a keyword-level association, not a fabricated
direct link) — each step is honestly labeled with its real source system.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.athena_knowledge import DISCLAIMER
from app.models.competency_event import CompetencyEvent
from app.models.knowledge import ClinicalCase
from app.models.root_cause import RootCauseAssignment
from app.services import capa_lifecycle_service
from app.services.apollo_policy_service import list_policies
from app.services.similar_case_finder_service import find_similar_cases


def build_memory_timeline(db: Session, tenant_id: str, *, finding_type: str, instrument_type: str = "") -> dict:
    q = finding_type.strip().lower()

    events = (
        db.query(ClinicalCase)
        .filter(ClinicalCase.tenant_id == tenant_id, ClinicalCase.finding_type == finding_type)
        .order_by(ClinicalCase.created_at.asc())
        .all()
    )
    investigations = (
        db.query(RootCauseAssignment)
        .filter(RootCauseAssignment.tenant_id == tenant_id, RootCauseAssignment.finding_type == finding_type)
        .order_by(RootCauseAssignment.created_at.asc())
        .all()
    )
    all_capas = capa_lifecycle_service.list_capas(tenant_id, limit=500)
    capas = [c for c in all_capas if q in (c.get("title") or "").lower() or q in (c.get("description") or "").lower()]

    education_events = (
        db.query(CompetencyEvent)
        .filter(
            CompetencyEvent.tenant_id == tenant_id, CompetencyEvent.finding_type == finding_type,
            CompetencyEvent.event_type == "education_completed",
        )
        .order_by(CompetencyEvent.created_at.asc())
        .all()
    )
    all_policies = list_policies(db, tenant_id)
    policy_changes = [p for p in all_policies if q in p["title"].lower()]

    outcomes = [{"capa_id": c["id"], "lifecycle_status": c.get("lifecycle_status")} for c in capas
                if c.get("lifecycle_status") in ("verified", "closed")]
    verifications = [
        {"capa_id": c["id"], "verified_by": c.get("verified_by"), "verified_at": c.get("verified_at")}
        for c in capas if c.get("verified_at")
    ]

    future_similar_cases = (
        find_similar_cases(db, tenant_id, instrument_type=instrument_type, finding_type=finding_type, limit=5)
        if instrument_type else []
    )

    return {
        "finding_type": finding_type,
        "timeline": {
            "event": [{"id": e.id, "title": e.title, "created_at": e.created_at.isoformat()} for e in events],
            "investigation": [
                {"id": r.id, "root_cause": r.root_cause, "assigned_by": r.assigned_by, "created_at": r.created_at.isoformat()}
                for r in investigations
            ],
            "capa": [{"id": c["id"], "title": c["title"], "lifecycle_status": c.get("lifecycle_status")} for c in capas],
            "education": [
                {"id": r.id, "technician": r.technician, "created_at": r.created_at.isoformat()}
                for r in education_events
            ],
            "policy_change": [{"id": p["id"], "title": p["title"], "version": p["version"], "status": p["status"]} for p in policy_changes],
            "outcome": outcomes,
            "verification": verifications,
            "future_similar_cases": future_similar_cases,
        },
        "human_review_required": True,
        "disclaimer": DISCLAIMER,
    }
