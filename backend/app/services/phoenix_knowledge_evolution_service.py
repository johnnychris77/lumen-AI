"""v4.9 — Project Phoenix, Section 5: Knowledge Evolution Center.

`athena_curator_service.py` (v4.8) already detects duplicate documents,
outdated guidance, retirement candidates, emerging best practices, and
knowledge gaps — composed here directly, never re-derived. The one
genuinely new check is **contradictory guidance**: no such detection
exists anywhere in this codebase (confirmed by grep). It uses a real,
deterministic keyword-conflict check — never a semantic/LLM judgment —
so it only ever flags an *explicit* lexical conflict for human review.
"""
from __future__ import annotations

import json
from collections import defaultdict

from sqlalchemy.orm import Session

from app.models.knowledge import APPROVED, KnowledgeArticle
from app.models.phoenix_intelligence import DISCLAIMER
from app.services import athena_curator_service

# Deliberately non-overlapping keyword sets — an article containing only
# strict-disposition language and another containing only lenient-
# disposition language, for the same finding+zone, is a real, checkable
# lexical conflict.
_STRICT_KEYWORDS = ("remove from service", "reprocess", "quarantine", "do not use")
_LENIENT_KEYWORDS = ("monitor", "acceptable", "no action needed", "continue use")


def _disposition_signal(text: str) -> str:
    lowered = text.lower()
    has_strict = any(k in lowered for k in _STRICT_KEYWORDS)
    has_lenient = any(k in lowered for k in _LENIENT_KEYWORDS)
    if has_strict and not has_lenient:
        return "strict"
    if has_lenient and not has_strict:
        return "lenient"
    return "unclear"


def contradictory_guidance(db: Session, tenant_id: str) -> list[dict]:
    """Approved articles sharing a finding+zone but with opposite,
    unambiguous disposition language."""
    rows = db.query(KnowledgeArticle).filter(
        KnowledgeArticle.tenant_id == tenant_id, KnowledgeArticle.approval_status == APPROVED,
    ).all()

    groups: dict[tuple[str, str], list[KnowledgeArticle]] = defaultdict(list)
    for r in rows:
        try:
            findings = json.loads(r.applicable_findings or "[]")
        except (TypeError, ValueError):
            findings = []
        for finding in findings or [""]:
            if finding and r.anatomy_zone:
                groups[(finding, r.anatomy_zone)].append(r)

    conflicts = []
    for (finding, zone), articles in groups.items():
        if len(articles) < 2:
            continue
        signals = {a.id: _disposition_signal(a.body) for a in articles}
        strict_ids = [aid for aid, s in signals.items() if s == "strict"]
        lenient_ids = [aid for aid, s in signals.items() if s == "lenient"]
        if strict_ids and lenient_ids:
            conflicts.append({
                "finding_type": finding, "anatomy_zone": zone,
                "strict_article_ids": strict_ids, "lenient_article_ids": lenient_ids,
            })
    return conflicts


def knowledge_evolution_summary(db: Session, tenant_id: str) -> dict:
    curator = athena_curator_service.curator_summary(db, tenant_id)
    return {
        **curator,
        "contradictory_guidance": contradictory_guidance(db, tenant_id),
        "human_review_required": True,
        "disclaimer": DISCLAIMER,
    }
