"""v3.5 — Project Beacon, Section 5: Clinical Evidence Exchange.

Horizon's `horizon_evidence_service.py` / `ClinicalEvidenceReference` is
already the first general-purpose evidence store in this codebase
(peer-reviewed literature, manufacturer guidance, AAMI/AORN standards,
org SOPs, internal validation studies), extended for Beacon with three
more evidence types (`case_report`, `quality_improvement_initiative`,
`best_practice` — added to `federated_horizon.py::EVIDENCE_TYPES`). This
module adds no new table: it is a presentation/composition layer over
`horizon_evidence_service`, exactly like `horizon_research_portal_service.py`
composed Horizon's own signals over P20's research exchange.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.federated_horizon import DISCLAIMER, EVIDENCE_TYPES
from app.services import horizon_evidence_service

BEACON_EVIDENCE_TYPES = ("case_report", "quality_improvement_initiative", "best_practice")


def submit_case_report(db: Session, *, title: str, citation_text: str, source: str = "", tenant_id: str = "", added_by: str = "") -> dict:
    return horizon_evidence_service.add_evidence(
        db, evidence_type="case_report", title=title, citation_text=citation_text,
        source=source, tenant_id=tenant_id, added_by=added_by,
    )


def submit_quality_improvement_initiative(db: Session, *, title: str, citation_text: str, source: str = "", tenant_id: str = "", added_by: str = "") -> dict:
    return horizon_evidence_service.add_evidence(
        db, evidence_type="quality_improvement_initiative", title=title, citation_text=citation_text,
        source=source, tenant_id=tenant_id, added_by=added_by,
    )


def submit_best_practice(db: Session, *, title: str, citation_text: str, source: str = "", tenant_id: str = "", added_by: str = "") -> dict:
    return horizon_evidence_service.add_evidence(
        db, evidence_type="best_practice", title=title, citation_text=citation_text,
        source=source, tenant_id=tenant_id, added_by=added_by,
    )


def evidence_exchange_summary(db: Session, tenant_id: str = "") -> dict:
    """Section 5: 'every AI recommendation links to available evidence' —
    a composed view of validation studies, case reports, inspection
    science, quality improvement initiatives, peer-reviewed publications,
    and best practices, all reused from `horizon_evidence_service`."""
    by_type = {t: horizon_evidence_service.list_evidence(db, evidence_type=t, tenant_id=tenant_id) for t in EVIDENCE_TYPES}
    return {
        "evidence_by_type": by_type,
        "total_evidence_count": sum(len(v) for v in by_type.values()),
        "human_review_required": True,
        "disclaimer": DISCLAIMER,
    }


def evidence_for_recommendation(db: Session, source_type: str, source_id: str) -> list[dict]:
    return horizon_evidence_service.list_evidence_for_recommendation(db, source_type, source_id)
