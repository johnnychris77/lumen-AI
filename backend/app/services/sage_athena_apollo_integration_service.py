"""Project Sage, Section 15: Integration With Athena and Apollo.

Athena provides institutional knowledge / approved lessons learned /
clinical cases / playbooks -- via `athena_memory_service.list_memory_entries`,
called through rather than re-querying `KnowledgeArticle`/`ClinicalCase`/CAPA/
root-cause tables directly. Apollo provides competency/CAPA/audit/policy
evidence -- via the real `QualityTwinSnapshot` (`competency_score`/
`education_score`), read-only. Sage returns learning recommendations,
education completion, competency evidence, and effectiveness results built
from this input -- it never writes back to either Athena's or Apollo's
tables.
"""
from __future__ import annotations

from app.services.apollo_quality_twin_service import twin_history
from app.services.athena_memory_service import list_memory_entries


def approved_institutional_content(db, tenant_id: str, *, query: str = "") -> list[dict]:
    """Athena's approved lessons-learned/clinical-cases/playbooks content
    Sage may cite as a source for education (never authored by Sage)."""
    entries = list_memory_entries(db, tenant_id)
    if query:
        needle = query.lower()
        entries = [e for e in entries if needle in str(e).lower()]
    return entries


def department_competency_evidence(db, tenant_id: str, department: str = "unspecified") -> dict | None:
    """Apollo's most recent department-level competency/education scores --
    read-only supplementary evidence for Sage's executive workforce view."""
    history = twin_history(db, tenant_id, department, limit=1)
    if not history:
        return None
    latest = history[0]
    scores = latest.get("scores", {})
    return {
        "department": department,
        "competency_score": scores.get("competency_score"),
        "education_score": scores.get("education_score"),
        "snapshot_created_at": latest.get("created_at"),
    }
