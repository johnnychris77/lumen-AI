"""v4.8 — Project Athena, Section 7: Organizational Search.

Federates keyword search across every real source the brief names.
Confirmed via grep: no embeddings/vector search/TF-IDF exists anywhere in
this codebase — consistent with the platform-wide "deterministic,
source-grounded, zero real LLM integration" convention, so this stays
keyword/facet-based rather than introducing a fabricated semantic layer.
`knowledge_search_service.smart_search` already covers Articles+Cases;
this widens coverage to Policies/CAPAs/Digital Twins/Inspections/
Playbooks/Research/Competencies, each result tagged with its real source
system. "Meeting Notes" has no backing store anywhere in this codebase —
rather than fabricate one, that source always returns an empty result set
with an honest reason string.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.db import models
from app.models.apollo_quality import QualityTwinSnapshot
from app.models.competency_event import CompetencyEvent
from app.services import capa_lifecycle_service
from app.services.apollo_policy_service import list_policies
from app.services.athena_playbook_service import list_playbooks
from app.services.knowledge_search_service import smart_search
from app.services.p24_standards_service import get_publications

SOURCE_KNOWLEDGE_ARTICLES = "knowledge_articles"
SOURCE_POLICIES = "policies"
SOURCE_CAPAS = "capas"
SOURCE_DIGITAL_TWINS = "digital_twins"
SOURCE_INSPECTIONS = "inspections"
SOURCE_PLAYBOOKS = "playbooks"
SOURCE_RESEARCH = "research"
SOURCE_COMPETENCIES = "competencies"
SOURCE_MEETING_NOTES = "meeting_notes"
SOURCE_TYPES = [
    SOURCE_KNOWLEDGE_ARTICLES, SOURCE_POLICIES, SOURCE_CAPAS, SOURCE_DIGITAL_TWINS, SOURCE_INSPECTIONS,
    SOURCE_PLAYBOOKS, SOURCE_RESEARCH, SOURCE_COMPETENCIES, SOURCE_MEETING_NOTES,
]


def _search_policies(db: Session, tenant_id: str, q: str) -> list[dict]:
    return [p for p in list_policies(db, tenant_id) if q in p["title"].lower() or q in (p["content"] or "").lower()]


def _search_capas(tenant_id: str, q: str) -> list[dict]:
    rows = capa_lifecycle_service.list_capas(tenant_id, limit=500)
    return [c for c in rows if q in (c.get("title") or "").lower() or q in (c.get("description") or "").lower()]


def _search_digital_twins(db: Session, tenant_id: str, q: str) -> list[dict]:
    rows = db.query(QualityTwinSnapshot).filter(QualityTwinSnapshot.tenant_id == tenant_id).all()
    return [
        {"id": r.id, "department": r.department, "overall_score": r.overall_score, "created_at": r.created_at.isoformat()}
        for r in rows if q in r.department.lower()
    ]


def _search_inspections(db: Session, tenant_id: str, q: str) -> list[dict]:
    rows = (
        db.query(models.Inspection)
        .filter(models.Inspection.tenant_id == tenant_id)
        .order_by(models.Inspection.id.desc())
        .limit(200)
        .all()
    )
    return [
        {"id": r.id, "instrument_type": r.instrument_type, "detected_issue": r.detected_issue, "created_at": r.created_at.isoformat()}
        for r in rows if q in (r.instrument_type or "").lower() or q in (r.detected_issue or "").lower()
    ]


def _search_playbooks(db: Session, tenant_id: str, q: str) -> list[dict]:
    return [p for p in list_playbooks(db, tenant_id) if q in p["name"].lower() or q in (p.get("description") or "").lower()]


def _search_research(db: Session, q: str) -> list[dict]:
    publications = get_publications(db)
    return [p for p in publications if q in p["title"].lower() or q in (p.get("abstract") or "").lower()]


def _search_competencies(db: Session, tenant_id: str, q: str) -> list[dict]:
    rows = db.query(CompetencyEvent).filter(CompetencyEvent.tenant_id == tenant_id).all()
    return [
        {"id": r.id, "technician": r.technician, "event_type": r.event_type, "finding_type": r.finding_type}
        for r in rows if q in (r.finding_type or "").lower() or q in r.technician.lower()
    ]


def organizational_search(db: Session, tenant_id: str, query: str, *, actor: str = "") -> dict:
    q = (query or "").strip().lower()
    core = smart_search(db, tenant_id, query, actor=actor)

    return {
        "query": query,
        SOURCE_KNOWLEDGE_ARTICLES: core["articles"] + core["cases"],
        SOURCE_POLICIES: _search_policies(db, tenant_id, q) if q else [],
        SOURCE_CAPAS: _search_capas(tenant_id, q) if q else [],
        SOURCE_DIGITAL_TWINS: _search_digital_twins(db, tenant_id, q) if q else [],
        SOURCE_INSPECTIONS: _search_inspections(db, tenant_id, q) if q else [],
        SOURCE_PLAYBOOKS: _search_playbooks(db, tenant_id, q) if q else [],
        SOURCE_RESEARCH: _search_research(db, q) if q else [],
        SOURCE_COMPETENCIES: _search_competencies(db, tenant_id, q) if q else [],
        SOURCE_MEETING_NOTES: {
            "results": [], "reason": "No meeting-notes store exists in this codebase yet — not fabricated.",
        },
        "human_review_required": True,
    }
