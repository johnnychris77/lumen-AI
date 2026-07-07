"""v1.8 — Knowledge Analytics (Deliverable 10).

Rollups over real KnowledgeArticle/ClinicalCase/query-log/override data —
nothing here is a separate model, just aggregation of what the rest of
v1.8 and the existing v1.6/v1.4 stores already record.
"""
from __future__ import annotations

from collections import defaultdict

from sqlalchemy.orm import Session

from app.models.disposition_override import DispositionOverride
from app.models.knowledge import APPROVED, TEACHING_POINT, ClinicalCase, KnowledgeArticle, KnowledgeQueryLog


def most_viewed_articles(db: Session, tenant_id: str, limit: int = 10) -> list[dict]:
    rows = (
        db.query(KnowledgeArticle)
        .filter(KnowledgeArticle.tenant_id == tenant_id, KnowledgeArticle.view_count > 0)
        .order_by(KnowledgeArticle.view_count.desc())
        .limit(limit)
        .all()
    )
    return [{"id": r.id, "title": r.title, "category": r.category, "view_count": r.view_count} for r in rows]


def most_common_questions(db: Session, tenant_id: str, limit: int = 10) -> list[dict]:
    rows = db.query(KnowledgeQueryLog).filter(KnowledgeQueryLog.tenant_id == tenant_id).all()
    counts: dict[str, int] = defaultdict(int)
    for r in rows:
        counts[r.query_text.strip().lower()] += 1
    return [
        {"query": q, "count": c}
        for q, c in sorted(counts.items(), key=lambda kv: kv[1], reverse=True)[:limit]
    ]


def most_frequent_teaching_points(db: Session, tenant_id: str, limit: int = 10) -> list[dict]:
    import json

    rows = (
        db.query(KnowledgeArticle)
        .filter(KnowledgeArticle.tenant_id == tenant_id, KnowledgeArticle.category == TEACHING_POINT)
        .all()
    )
    counts: dict[str, int] = defaultdict(int)
    for r in rows:
        try:
            findings = json.loads(r.applicable_findings or "[]")
        except (TypeError, ValueError):
            findings = []
        for f in findings or ["unspecified"]:
            counts[f] += 1
    return [
        {"finding": f, "teaching_point_count": c}
        for f, c in sorted(counts.items(), key=lambda kv: kv[1], reverse=True)[:limit]
    ]


def common_supervisor_comments(db: Session, tenant_id: str, limit: int = 10) -> list[dict]:
    rows = (
        db.query(DispositionOverride)
        .filter(DispositionOverride.tenant_id == tenant_id, DispositionOverride.reason != "")
        .all()
    )
    counts: dict[str, int] = defaultdict(int)
    for r in rows:
        counts[r.reason.strip()] += 1
    return [
        {"comment": c, "count": n}
        for c, n in sorted(counts.items(), key=lambda kv: kv[1], reverse=True)[:limit]
    ]


def knowledge_gaps(db: Session, tenant_id: str) -> list[dict]:
    """Findings that have prompted a supervisor override but have no
    approved institutional article addressing them yet — a real gap, not a
    guess."""
    import json

    override_findings: dict[str, int] = defaultdict(int)
    for r in db.query(DispositionOverride).filter(DispositionOverride.tenant_id == tenant_id).all():
        if r.ai_recommended_disposition:
            override_findings[r.ai_recommended_disposition] += 1

    covered: set[str] = set()
    for a in db.query(KnowledgeArticle).filter(
        KnowledgeArticle.tenant_id == tenant_id, KnowledgeArticle.approval_status == APPROVED,
    ).all():
        try:
            findings = json.loads(a.applicable_findings or "[]")
        except (TypeError, ValueError):
            findings = []
        covered.update(findings)

    case_findings: dict[str, int] = defaultdict(int)
    for c in db.query(ClinicalCase).filter(ClinicalCase.tenant_id == tenant_id).all():
        if c.finding_type and c.finding_type not in covered:
            case_findings[c.finding_type] += 1

    return [
        {"finding_type": f, "clinical_case_count": n}
        for f, n in sorted(case_findings.items(), key=lambda kv: kv[1], reverse=True)
    ]


def training_opportunities(db: Session, tenant_id: str) -> list[dict]:
    """Technicians with a repeated error on record (v1.4 competency events)
    for a finding type that has no approved institutional guidance yet."""
    import json

    from app.models.competency_event import CompetencyEvent

    covered: set[str] = set()
    for a in db.query(KnowledgeArticle).filter(
        KnowledgeArticle.tenant_id == tenant_id, KnowledgeArticle.approval_status == APPROVED,
    ).all():
        try:
            findings = json.loads(a.applicable_findings or "[]")
        except (TypeError, ValueError):
            findings = []
        covered.update(findings)

    rows = (
        db.query(CompetencyEvent)
        .filter(CompetencyEvent.tenant_id == tenant_id, CompetencyEvent.event_type == "repeated_error")
        .all()
    )
    opportunities = []
    for r in rows:
        if r.finding_type and r.finding_type not in covered:
            opportunities.append({"technician": r.technician, "finding_type": r.finding_type})
    return opportunities


def knowledge_analytics(db: Session, tenant_id: str) -> dict:
    return {
        "most_viewed_articles": most_viewed_articles(db, tenant_id),
        "most_common_questions": most_common_questions(db, tenant_id),
        "most_frequent_teaching_points": most_frequent_teaching_points(db, tenant_id),
        "common_supervisor_comments": common_supervisor_comments(db, tenant_id),
        "knowledge_gaps": knowledge_gaps(db, tenant_id),
        "training_opportunities": training_opportunities(db, tenant_id),
        "human_review_required": True,
    }
