"""v1.8 — Smart Knowledge Search (Deliverable 4).

A deterministic, keyword-matched search over institutional knowledge
articles and clinical cases — mirroring the same "explainable, not a black
box" approach already used by the disposition/priority/risk engines rather
than calling out to an external LLM. The query is matched against real,
already-known vocabulary (finding types, anatomy zones, instrument
families) so "show all blood findings in Kerrisons" resolves to a real
`finding=blood` + `instrument family=kerrison_rongeur` filter, not a guess.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.knowledge import KnowledgeQueryLog
from app.services.clinical_mentor import FINDING_EDUCATION
from app.services.clinical_case_library_service import list_cases
from app.services.instrument_anatomy import INSTRUMENT_ANATOMY
from app.services.instrument_zones import ZONE_INFO
from app.services.knowledge_repository_service import list_articles


def _matched_findings(q: str) -> list[str]:
    return [f for f in FINDING_EDUCATION if f in q or f.replace("_", " ") in q]


def _matched_zones(q: str) -> list[str]:
    return [z for z in ZONE_INFO if z.lower() in q]


def _matched_families(q: str) -> list[str]:
    families = []
    for family, defn in INSTRUMENT_ANATOMY.items():
        if family == "default":
            continue
        if family.replace("_", " ") in q or any(k in q for k in defn.get("match", [])):
            families.append(family)
    return families


def smart_search(db: Session, tenant_id: str, query: str, *, actor: str = "") -> dict:
    """Deliverable 4 — natural-language-style search resolved to real facet
    matches over KnowledgeArticle + ClinicalCase."""
    q = (query or "").strip().lower()
    matched_findings = _matched_findings(q)
    matched_zones = _matched_zones(q)
    matched_families = _matched_families(q)

    articles: list[dict] = []
    cases: list[dict] = []
    seen_article_ids: set[int] = set()
    seen_case_ids: set[int] = set()

    if matched_findings:
        for finding in matched_findings:
            for a in list_articles(db, tenant_id, finding=finding, approval_status="approved"):
                if a["id"] not in seen_article_ids:
                    seen_article_ids.add(a["id"])
                    articles.append(a)
            for c in list_cases(db, tenant_id, finding=finding):
                if c["id"] not in seen_case_ids:
                    seen_case_ids.add(c["id"])
                    cases.append(c)
    else:
        # No recognized finding keyword — fall back to a free-text match
        # over approved article title/body.
        for a in list_articles(db, tenant_id, approval_status="approved"):
            if q and (q in a["title"].lower() or q in a["body"].lower()):
                articles.append(a)

    if matched_families:
        for family in matched_families:
            for c in list_cases(db, tenant_id):
                if c["id"] in seen_case_ids:
                    continue
                from app.services.instrument_anatomy import resolve_family
                if resolve_family(c["instrument_type"]) == family:
                    seen_case_ids.add(c["id"])
                    cases.append(c)

    matched_category = (
        "finding" if matched_findings else "instrument_family" if matched_families
        else "zone" if matched_zones else "free_text"
    )
    db.add(KnowledgeQueryLog(tenant_id=tenant_id, actor=actor, query_text=query, matched_category=matched_category))

    return {
        "query": query,
        "matched_findings": matched_findings,
        "matched_zones": matched_zones,
        "matched_instrument_families": matched_families,
        "articles": articles,
        "cases": cases,
        "human_review_required": True,
    }
