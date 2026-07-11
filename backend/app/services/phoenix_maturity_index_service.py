"""v4.9 — Project Phoenix, Section 10: Platform Maturity Index.

Nine named dimensions, each a composition of a real, already-computed
signal from a prior sprint — no dimension re-derives another system's
math. "Quality" reuses Apollo's `apollo_quality_twin_service` (v4.7,
itself an 8-dimension composite) as a single input rather than
re-deriving CAPA/competency/audit-readiness numbers a third time.
Progression over time is tracked via `PlatformMaturitySnapshot` rows,
read back through `maturity_history`.
"""
from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.models.knowledge import KnowledgeQueryLog
from app.models.phoenix_intelligence import DISCLAIMER, PlatformMaturitySnapshot
from app.services import competency_service, phoenix_ai_observatory_service, phoenix_platform_health_service, vanguard_governance_service

# A capped proxy: more logged queries indicates more active analytics
# usage. No "correct" volume exists to compare against, so this is
# reported as a bounded 0-100 usage-activity signal, not a benchmarked
# maturity level.
_ANALYTICS_USAGE_CAP = 200


def _inspection_dimension(db: Session, tenant_id: str) -> float | None:
    coverage = phoenix_ai_observatory_service.coverage_summary(db, tenant_id)
    return coverage["ai_participation_coverage_pct"]


def _analytics_dimension(db: Session, tenant_id: str) -> float | None:
    count = db.query(KnowledgeQueryLog).filter(KnowledgeQueryLog.tenant_id == tenant_id).count()
    if not count:
        return None
    return round(min(100.0, 100 * count / _ANALYTICS_USAGE_CAP), 1)


def _education_dimension(db: Session, tenant_id: str) -> float | None:
    dashboard = competency_service.technician_quality_dashboard(db, tenant_id)
    values = [t["training_progress_pct"] for t in dashboard["technicians"] if t.get("training_progress_pct") is not None]
    return round(sum(values) / len(values), 1) if values else None


def _governance_dimension(db: Session, tenant_id: str) -> float | None:
    dashboard = vanguard_governance_service.governance_dashboard(db, tenant_id)
    compliance = dashboard["policy_compliance"]
    if not compliance["total_policy_count"]:
        return None
    return round(100 * compliance["enabled_policy_count"] / compliance["total_policy_count"], 1)


def _executive_intelligence_dimension(db: Session, tenant_id: str) -> float | None:
    dashboard = vanguard_governance_service.governance_dashboard(db, tenant_id)
    return dashboard["audit_readiness"].get("overall_readiness_score")


def compute_platform_maturity_index(db: Session, tenant_id: str) -> dict:
    factors: dict[str, str] = {}

    inspection = _inspection_dimension(db, tenant_id)
    factors["inspection_score"] = "% of inspections that received a real AI confidence score"

    knowledge = phoenix_platform_health_service.compute_knowledge_health_score(db, tenant_id)["score"]
    factors["knowledge_score"] = "reused from Platform Health's Knowledge Health"

    quality = phoenix_platform_health_service.compute_quality_health_score(db, tenant_id)["score"]
    factors["quality_score"] = "reused from Apollo's Quality Digital Twin overall_score"

    workflow = phoenix_platform_health_service.compute_workflow_health_score(db, tenant_id)["score"]
    factors["workflow_score"] = "reused from Platform Health's Workflow Health"

    analytics = _analytics_dimension(db, tenant_id)
    factors["analytics_score"] = "bounded knowledge-query usage-activity proxy, not a benchmarked level"

    education = _education_dimension(db, tenant_id)
    factors["education_score"] = "org-average technician training_progress_pct"

    digital_twins = phoenix_platform_health_service.compute_digital_twin_health_score(db, tenant_id)["score"]
    factors["digital_twins_score"] = "reused from Platform Health's Digital Twin Health"

    governance = _governance_dimension(db, tenant_id)
    factors["governance_score"] = "enabled-vs-total RetentionPolicy ratio (Vanguard governance dashboard)"

    executive_intelligence = _executive_intelligence_dimension(db, tenant_id)
    factors["executive_intelligence_score"] = "audit-readiness overall_readiness_score (Vanguard governance dashboard)"

    scores = {
        "inspection_score": inspection, "knowledge_score": knowledge, "quality_score": quality,
        "workflow_score": workflow, "analytics_score": analytics, "education_score": education,
        "digital_twins_score": digital_twins, "governance_score": governance,
        "executive_intelligence_score": executive_intelligence,
    }
    present = [v for v in scores.values() if v is not None]
    overall_score = round(sum(present) / len(present), 1) if present else 0.0

    snapshot = PlatformMaturitySnapshot(
        tenant_id=tenant_id, overall_score=overall_score, factors_json=json.dumps(factors),
        **{k: (v or 0.0) for k, v in scores.items()},
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)

    return {
        "id": snapshot.id, "created_at": snapshot.created_at.isoformat(), "scores": scores,
        "overall_score": overall_score, "factors": factors,
        "human_review_required": True, "disclaimer": DISCLAIMER,
    }


def maturity_history(db: Session, tenant_id: str, *, limit: int = 20) -> list[dict]:
    rows = (
        db.query(PlatformMaturitySnapshot)
        .filter(PlatformMaturitySnapshot.tenant_id == tenant_id)
        .order_by(PlatformMaturitySnapshot.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": r.id, "created_at": r.created_at.isoformat(), "overall_score": r.overall_score,
            "scores": {
                "inspection_score": r.inspection_score, "knowledge_score": r.knowledge_score,
                "quality_score": r.quality_score, "workflow_score": r.workflow_score,
                "analytics_score": r.analytics_score, "education_score": r.education_score,
                "digital_twins_score": r.digital_twins_score, "governance_score": r.governance_score,
                "executive_intelligence_score": r.executive_intelligence_score,
            },
        }
        for r in rows
    ]
