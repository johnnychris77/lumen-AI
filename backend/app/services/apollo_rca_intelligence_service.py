"""v4.7 — Project Apollo, Section 3: Root Cause Intelligence.

A pure *structuring/presentation* layer over data that already exists —
`RCADraft`/`rca_engine_service` (evidence, contributing factors, historical
recurrence, similar events — supervisor-approved) and `root_cause_service.
root_cause_trends` (confirmed `RootCauseAssignment` rows). This module never
writes a new root-cause data model and never finalizes a root cause itself;
`approve_draft`'s supervisor gate remains the only path that ever creates a
real `RootCauseAssignment`.

Four methodology views, all derived from real evidence already on the draft
or from real assignment counts — never a fabricated score:
  * Five Whys — the draft's own evidence/contributing-factors chain,
    presented as a "why" ladder for the supervisor to keep extending.
  * Fishbone — contributing factors bucketed into the six standard
    ishikawa categories by keyword match against real factor text.
  * Pareto — real root-cause assignment counts (`root_cause_trends`)
    ranked with cumulative percentage.
  * Trend Analysis — the same trends, split by finding type over time.
"""
from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.models.apollo_quality import DISCLAIMER, FISHBONE_CATEGORIES
from app.services import rca_engine_service, root_cause_service

_FISHBONE_KEYWORDS: dict[str, list[str]] = {
    "man": ["technician", "training", "competency", "staff", "supervisor"],
    "machine": ["instrument", "washer", "sterilizer", "equipment", "device"],
    "method": ["procedure", "sop", "process", "protocol", "workflow", "step"],
    "material": ["chemistry", "detergent", "solution", "material", "supply"],
    "measurement": ["coverage", "confidence", "indicator", "test", "inspection"],
    "environment": ["storage", "temperature", "humidity", "facility", "environment"],
}


def five_whys_view(db: Session, tenant_id: str, draft_id: int) -> dict:
    """Presents the RCA draft's real evidence and contributing factors as a
    "why" ladder — the supervisor still has to answer each "why", this only
    structures what's already on the draft."""
    draft = rca_engine_service.get_draft(db, tenant_id, draft_id)
    evidence = json.loads(draft.get("evidence_json") or "[]")
    contributing_factors = json.loads(draft.get("contributing_factors_json") or "[]")

    whys = []
    if evidence:
        whys.append({"level": 1, "question": "What happened?", "answer": evidence[0]})
    for i, factor in enumerate(contributing_factors, start=2):
        whys.append({"level": i, "question": "Why did that happen?", "answer": factor})
    whys.append({
        "level": len(whys) + 1,
        "question": "What is the root cause?",
        "answer": draft.get("approved_root_cause") or "Not yet determined — supervisor review required.",
    })

    return {
        "draft_id": draft_id,
        "methodology": "five_whys",
        "whys": whys,
        "status": draft.get("status"),
        "human_review_required": True,
        "disclaimer": DISCLAIMER,
    }


def fishbone_view(db: Session, tenant_id: str, draft_id: int) -> dict:
    """Buckets the draft's real contributing factors into the six standard
    Ishikawa categories by keyword match. Factors that don't match any
    category are listed under "uncategorized" rather than forced into a
    bucket that doesn't fit."""
    draft = rca_engine_service.get_draft(db, tenant_id, draft_id)
    contributing_factors = json.loads(draft.get("contributing_factors_json") or "[]")

    buckets: dict[str, list[str]] = {cat: [] for cat in FISHBONE_CATEGORIES}
    uncategorized: list[str] = []
    for factor in contributing_factors:
        lowered = factor.lower()
        matched = False
        for category, keywords in _FISHBONE_KEYWORDS.items():
            if any(kw in lowered for kw in keywords):
                buckets[category].append(factor)
                matched = True
                break
        if not matched:
            uncategorized.append(factor)

    return {
        "draft_id": draft_id,
        "methodology": "fishbone",
        "categories": buckets,
        "uncategorized": uncategorized,
        "human_review_required": True,
        "disclaimer": DISCLAIMER,
    }


def pareto_view(db: Session, tenant_id: str) -> dict:
    """Real root-cause assignment counts (never drafts) ranked with
    cumulative percentage — the classic 80/20 Pareto chart."""
    trends = root_cause_service.root_cause_trends(db, tenant_id)
    overall = trends["overall"]
    total = trends["total_assignments"]

    ranked = sorted(overall.items(), key=lambda kv: kv[1], reverse=True)
    rows = []
    cumulative = 0
    for root_cause, count in ranked:
        cumulative += count
        rows.append({
            "root_cause": root_cause,
            "count": count,
            "pct_of_total": round(100 * count / total, 1) if total else None,
            "cumulative_pct": round(100 * cumulative / total, 1) if total else None,
        })

    return {
        "methodology": "pareto",
        "total_assignments": total,
        "rows": rows,
        "human_review_required": True,
        "disclaimer": DISCLAIMER,
    }


def trend_view(db: Session, tenant_id: str) -> dict:
    """Real root-cause counts split by finding type — recurring-pattern
    detection across finding categories, not a time-series forecast (no
    per-assignment timestamp bucketing exists to support one honestly)."""
    trends = root_cause_service.root_cause_trends(db, tenant_id)
    return {
        "methodology": "trend_analysis",
        "total_assignments": trends["total_assignments"],
        "by_finding_type": trends["by_finding_type"],
        "human_review_required": True,
        "disclaimer": DISCLAIMER,
    }


def rca_intelligence_summary(db: Session, tenant_id: str) -> dict:
    """Composes the Pareto and Trend views (tenant-wide, no draft required)
    plus a count of drafts still awaiting supervisor review."""
    from app.models.quality_guardian import RCADraft

    pending_drafts = (
        db.query(RCADraft)
        .filter(RCADraft.tenant_id == tenant_id, RCADraft.status == "draft")
        .count()
    )
    return {
        "pareto": pareto_view(db, tenant_id),
        "trend_analysis": trend_view(db, tenant_id),
        "pending_draft_count": pending_drafts,
        "human_review_required": True,
        "disclaimer": DISCLAIMER,
    }
