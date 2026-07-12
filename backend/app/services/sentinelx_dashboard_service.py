"""Project Sentinel-X, Section 9: Risk Dashboard (`/risk`).

Aggregates every dimension the brief names from already-persisted
Sentinel-X assessments plus the real Knowledge Graph confidence signal --
no new tables, no fabricated distributions.
"""
from __future__ import annotations

from collections import Counter

from sqlalchemy.orm import Session

from app.models.sentinelx_risk import RISK_LEVEL_CRITICAL, RISK_LEVEL_HIGH, SentinelXRiskAssessment
from app.services.knowledge_graph_service import learning_confidence
from app.services.sage_knowledge_gap_service import list_gaps
from app.services.sentinelx_heatmap_service import all_heatmaps


def risk_dashboard_summary(db: Session, tenant_id: str) -> dict:
    assessments = db.query(SentinelXRiskAssessment).filter(SentinelXRiskAssessment.tenant_id == tenant_id).all()
    total = len(assessments)

    level_counts = Counter(a.risk_level for a in assessments)
    enterprise_risk = {
        "total_assessments": total,
        "average_risk_score": round(sum(a.risk_score for a in assessments) / total, 1) if total else None,
        "risk_level_distribution": dict(level_counts),
        "high_or_critical_pct": round(100 * sum(1 for a in assessments if a.risk_level in (RISK_LEVEL_HIGH, RISK_LEVEL_CRITICAL)) / total, 1) if total else None,
    }

    heatmaps = all_heatmaps(db, tenant_id)

    workflow_risk = {
        "process_variation_flagged_count": sum(1 for a in assessments if "process_variation" in a.evidence_json),
    }

    declining_count = sum(1 for a in assessments if a.digital_twin_condition_trend == "declining")
    digital_twin_risk = {
        "declining_assessment_count": declining_count,
        "declining_pct": round(100 * declining_count / total, 1) if total else None,
    }

    knowledge = learning_confidence(db, tenant_id)
    knowledge_risk = {
        "knowledge_confidence": knowledge.get("knowledge_confidence"),
        "clinical_recommendation_confidence": knowledge.get("clinical_recommendation_confidence"),
        "sample_sizes": knowledge.get("sample_sizes"),
    }

    open_gaps = list_gaps(db, tenant_id, status="open")
    education_risk = {"open_knowledge_gap_count": len(open_gaps)}

    return {
        "enterprise_risk": enterprise_risk,
        "facility_risk": heatmaps["facility"],
        "instrument_risk": heatmaps["instrument_family"],
        "anatomy_risk": heatmaps["anatomy"],
        "workflow_risk": workflow_risk,
        "education_risk": education_risk,
        "knowledge_risk": knowledge_risk,
        "digital_twin_risk": digital_twin_risk,
        "human_review_required": True,
    }
