"""v4.8 — Project Athena, Section 1: Institutional Memory Engine.

Normalizes real records from six pre-existing stores into one searchable
"memory entry" shape — clinical decisions/lessons learned/vendor/repair
observations (`KnowledgeArticle`), CAPA outcomes (`capa_lifecycle_service`),
Root Cause Analyses (`RootCauseAssignment`), workflow improvements
(`ContinuousImprovementInitiative`), policy history (`QualityPolicy`), and
education history (`CompetencyEvent`). No new "memory" table — every
record here is a read of data that already exists elsewhere.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.athena_knowledge import DISCLAIMER
from app.models.competency_event import CompetencyEvent
from app.models.continuous_improvement import ContinuousImprovementInitiative
from app.models.knowledge import KnowledgeArticle
from app.models.root_cause import RootCauseAssignment
from app.services import capa_lifecycle_service
from app.services.apollo_policy_service import list_policies

MEMORY_SOURCE_ARTICLE = "knowledge_article"
MEMORY_SOURCE_CAPA = "capa"
MEMORY_SOURCE_ROOT_CAUSE = "root_cause_analysis"
MEMORY_SOURCE_IMPROVEMENT = "workflow_improvement"
MEMORY_SOURCE_POLICY = "policy_history"
MEMORY_SOURCE_EDUCATION = "education_history"
MEMORY_SOURCE_TYPES = [
    MEMORY_SOURCE_ARTICLE, MEMORY_SOURCE_CAPA, MEMORY_SOURCE_ROOT_CAUSE,
    MEMORY_SOURCE_IMPROVEMENT, MEMORY_SOURCE_POLICY, MEMORY_SOURCE_EDUCATION,
]


def _articles_as_memory(db: Session, tenant_id: str) -> list[dict]:
    rows = db.query(KnowledgeArticle).filter(KnowledgeArticle.tenant_id == tenant_id).all()
    return [
        {
            "source_type": MEMORY_SOURCE_ARTICLE, "source_id": r.id, "title": r.title,
            "summary": r.body[:280], "category": r.category, "created_at": r.created_at.isoformat(),
            "status": r.approval_status,
        }
        for r in rows
    ]


def _capas_as_memory(tenant_id: str) -> list[dict]:
    rows = capa_lifecycle_service.list_capas(tenant_id, limit=500)
    return [
        {
            "source_type": MEMORY_SOURCE_CAPA, "source_id": r["id"], "title": r["title"],
            "summary": r.get("description") or "", "category": r.get("recommendation_type") or "",
            "created_at": r["created_at"], "status": r.get("lifecycle_status"),
        }
        for r in rows
    ]


def _root_causes_as_memory(db: Session, tenant_id: str) -> list[dict]:
    rows = db.query(RootCauseAssignment).filter(RootCauseAssignment.tenant_id == tenant_id).all()
    return [
        {
            "source_type": MEMORY_SOURCE_ROOT_CAUSE, "source_id": r.id,
            "title": f"Root cause: {r.finding_type} -> {r.root_cause}",
            "summary": f"Assigned by {r.assigned_by} for inspection {r.inspection_id}.",
            "category": r.finding_type, "created_at": r.created_at.isoformat(), "status": "assigned",
        }
        for r in rows
    ]


def _improvements_as_memory(db: Session, tenant_id: str) -> list[dict]:
    rows = (
        db.query(ContinuousImprovementInitiative)
        .filter(ContinuousImprovementInitiative.tenant_id == tenant_id)
        .all()
    )
    return [
        {
            "source_type": MEMORY_SOURCE_IMPROVEMENT, "source_id": r.id, "title": r.initiative,
            "summary": r.expected_impact or "", "category": r.methodology or "",
            "created_at": r.created_at.isoformat(), "status": r.status,
        }
        for r in rows
    ]


def _policies_as_memory(db: Session, tenant_id: str) -> list[dict]:
    rows = list_policies(db, tenant_id)
    return [
        {
            "source_type": MEMORY_SOURCE_POLICY, "source_id": r["id"], "title": r["title"],
            "summary": f"Version {r['version']} — {r['status']}", "category": "policy",
            "created_at": r["created_at"], "status": r["status"],
        }
        for r in rows
    ]


def _education_as_memory(db: Session, tenant_id: str) -> list[dict]:
    rows = (
        db.query(CompetencyEvent)
        .filter(
            CompetencyEvent.tenant_id == tenant_id,
            CompetencyEvent.event_type.in_(("education_completed", "annual_competency", "procedure_validation")),
        )
        .all()
    )
    return [
        {
            "source_type": MEMORY_SOURCE_EDUCATION, "source_id": r.id,
            "title": f"{r.event_type.replace('_', ' ').title()}: {r.finding_type or 'general'}",
            "summary": f"Technician: {r.technician}", "category": r.event_type,
            "created_at": r.created_at.isoformat(), "status": "recorded",
        }
        for r in rows
    ]


def list_memory_entries(db: Session, tenant_id: str, *, source_types: list[str] | None = None) -> list[dict]:
    """Every knowledge object, normalized and searchable (Section 1)."""
    builders = {
        MEMORY_SOURCE_ARTICLE: lambda: _articles_as_memory(db, tenant_id),
        MEMORY_SOURCE_CAPA: lambda: _capas_as_memory(tenant_id),
        MEMORY_SOURCE_ROOT_CAUSE: lambda: _root_causes_as_memory(db, tenant_id),
        MEMORY_SOURCE_IMPROVEMENT: lambda: _improvements_as_memory(db, tenant_id),
        MEMORY_SOURCE_POLICY: lambda: _policies_as_memory(db, tenant_id),
        MEMORY_SOURCE_EDUCATION: lambda: _education_as_memory(db, tenant_id),
    }
    wanted = source_types or MEMORY_SOURCE_TYPES
    entries: list[dict] = []
    for source_type in wanted:
        if source_type in builders:
            entries.extend(builders[source_type]())
    entries.sort(key=lambda e: e["created_at"], reverse=True)
    return entries


def search_memory(db: Session, tenant_id: str, query: str) -> dict:
    """Keyword match across every normalized memory entry (Section 1's
    "every knowledge object is searchable")."""
    q = (query or "").strip().lower()
    entries = list_memory_entries(db, tenant_id)
    if q:
        entries = [e for e in entries if q in e["title"].lower() or q in e["summary"].lower()]
    return {
        "query": query, "results": entries, "result_count": len(entries),
        "human_review_required": True, "disclaimer": DISCLAIMER,
    }


def memory_summary(db: Session, tenant_id: str) -> dict:
    entries = list_memory_entries(db, tenant_id)
    by_source: dict[str, int] = {}
    for e in entries:
        by_source[e["source_type"]] = by_source.get(e["source_type"], 0) + 1
    return {
        "total_entries": len(entries), "by_source_type": by_source,
        "recent_entries": entries[:10], "human_review_required": True,
    }
