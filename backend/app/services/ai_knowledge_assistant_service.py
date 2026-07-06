"""v1.8 — AI Knowledge Assistant (Deliverable 8).

Answers contextual technician questions using existing structured
knowledge — finding education (the Knowledge Graph's own source), approved
institutional knowledge (KnowledgeArticle), and instrument anatomy
profiles — the same deterministic, source-grounded pattern already used by
`knowledge_graph_service.reasoning_chain()`, never a call to an external
LLM. Every answer lists exactly which sources it drew from, so nothing is
presented as authoritative without a traceable origin.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.knowledge import KnowledgeQueryLog
from app.services.clinical_mentor import FINDING_EDUCATION
from app.services.instrument_anatomy import get_anatomy, resolve_family
from app.services.knowledge_repository_service import list_articles
from app.services.knowledge_search_service import _matched_families, _matched_findings, _matched_zones


def answer_question(db: Session, tenant_id: str, question: str, *, instrument_type: str = "", actor: str = "") -> dict:
    """Deliverable 8 — a grounded answer plus the sources it came from."""
    q = (question or "").strip().lower()
    findings = _matched_findings(q)
    zones = _matched_zones(q)
    families = _matched_families(q) or ([resolve_family(instrument_type)] if instrument_type else [])
    families = [f for f in families if f != "default"]

    sources: list[str] = []
    answer_parts: list[str] = []

    for finding in findings:
        edu = FINDING_EDUCATION.get(finding, {})
        if edu:
            answer_parts.append(
                f"{finding.replace('_', ' ').capitalize()}: {edu.get('clinical_significance') or edu.get('why_it_matters', '')}"
            )
            sources.append("Knowledge Graph / finding education")
        for a in list_articles(db, tenant_id, finding=finding, approval_status="approved")[:3]:
            answer_parts.append(f"Institutional guidance ({a['title']}): {a['body']}")
            sources.append(f"Approved institutional article #{a['id']}")

    for family in families:
        anatomy = get_anatomy(family)
        high_risk_zones = [z["zone_name"] for z in anatomy.get("zones", []) if z.get("zone_risk_level") in ("high", "critical")]
        if high_risk_zones:
            answer_parts.append(
                f"For the {family.replace('_', ' ')} family, the high-risk anatomy zones are: {', '.join(high_risk_zones)}."
            )
            sources.append("Instrument anatomy profile")

    if not answer_parts:
        answer_parts.append(
            "No matching institutional knowledge, finding education, or anatomy profile was found for this "
            "question — consider adding it to the Knowledge Repository once answered."
        )

    db.add(KnowledgeQueryLog(tenant_id=tenant_id, actor=actor, query_text=question, matched_category="assistant"))

    return {
        "question": question,
        "answer": " ".join(answer_parts),
        "matched_findings": findings,
        "matched_zones": zones,
        "matched_instrument_families": families,
        "sources": sources,
        "human_review_required": True,
    }
