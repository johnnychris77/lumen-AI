"""v4.9 — Project Phoenix, Section 2: Improvement Recommendation Engine.

Scans the real outputs of the other Phoenix engines and Sentinel's AI
health monitor, drafting an `ImprovementRecommendation` for each genuine
signal found — never fabricated. Every recommendation starts as `draft`
and enters Continuous Validation (Section 9) only via an explicit,
separate human action (`phoenix_validation_pipeline_service.
start_validation`) — generating a recommendation never auto-starts its
approval chain.
"""
from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.models.phoenix_intelligence import (
    DISCLAIMER,
    REC_COLLECT_BASELINE_IMAGES,
    REC_CREATE_COMPETENCY,
    REC_IMPROVE_ANATOMY_MODEL,
    REC_IMPROVE_KNOWLEDGE_GRAPH,
    REC_REVIEW_AI_CONFIDENCE,
    REC_REVISE_INSPECTION_GUIDANCE,
    REC_UPDATE_SOP,
    REC_UPDATE_WORKFLOW,
    SOURCE_AI_OBSERVATORY,
    SOURCE_COMPETENCY_INTELLIGENCE,
    SOURCE_KNOWLEDGE_EVOLUTION,
    SOURCE_WORKFLOW_OPTIMIZER,
    ImprovementRecommendation,
)
from app.models.supervisor_review import SupervisorReview
from app.services import competency_intelligence_service, phoenix_ai_observatory_service, phoenix_knowledge_evolution_service, phoenix_workflow_optimization_service
from app.services.ml.pilot_validation import zone_performance

_LOW_CONFIDENCE_THRESHOLD = 0.7
_HIGH_MISS_RATE_THRESHOLD = 0.2


def _to_dict(row: ImprovementRecommendation) -> dict:
    return {
        "id": row.id, "created_at": row.created_at.isoformat(), "recommendation_type": row.recommendation_type,
        "source": row.source, "title": row.title, "evidence": json.loads(row.evidence_json or "[]"),
        "expected_benefit": row.expected_benefit, "confidence": row.confidence,
        "impact_assessment": row.impact_assessment,
        "required_approvals": json.loads(row.required_approvals_json or "[]"),
        "status": row.status, "related_object_type": row.related_object_type, "related_object_id": row.related_object_id,
        "human_review_required": True, "disclaimer": DISCLAIMER,
    }


def _create(
    db: Session, tenant_id: str, *, recommendation_type: str, source: str, title: str, evidence: list[str],
    expected_benefit: str, confidence: float, impact_assessment: str, required_approvals: list[str],
    related_object_type: str = "", related_object_id: int | None = None,
) -> ImprovementRecommendation:
    row = ImprovementRecommendation(
        tenant_id=tenant_id, recommendation_type=recommendation_type, source=source, title=title,
        evidence_json=json.dumps(evidence), expected_benefit=expected_benefit, confidence=confidence,
        impact_assessment=impact_assessment, required_approvals_json=json.dumps(required_approvals),
        related_object_type=related_object_type, related_object_id=related_object_id,
    )
    db.add(row)
    return row


def generate_recommendations(db: Session, tenant_id: str) -> list[dict]:
    created: list[ImprovementRecommendation] = []

    # 1. AI confidence decline -> review_ai_confidence.
    obs = phoenix_ai_observatory_service.observatory_summary(db, tenant_id)
    if obs["model_drift_detected"]:
        created.append(_create(
            db, tenant_id, recommendation_type=REC_REVIEW_AI_CONFIDENCE, source=SOURCE_AI_OBSERVATORY,
            title="Review AI confidence — drift detected",
            evidence=[obs["model_drift_detail"] or "AI health drift signal is active."],
            expected_benefit="Restores AI confidence calibration and reduces the risk of undetected accuracy regression.",
            confidence=0.7, impact_assessment="Affects every future inspection until addressed.",
            required_approvals=["spd_manager", "admin"],
        ))

    # 2. Low-confidence / high-miss-rate zones -> improve_anatomy_model / collect_baseline_images.
    reviews = db.query(SupervisorReview).filter(SupervisorReview.tenant_id == tenant_id).all()
    if reviews:
        zones = zone_performance(reviews)
        for z in zones["lowest_confidence_zones"][:3]:
            if z["avg_confidence"] is not None and z["avg_confidence"] < _LOW_CONFIDENCE_THRESHOLD:
                created.append(_create(
                    db, tenant_id, recommendation_type=REC_COLLECT_BASELINE_IMAGES, source=SOURCE_AI_OBSERVATORY,
                    title=f"Collect more baseline images — {z['zone']}",
                    evidence=[f"Average AI confidence in {z['zone']} is {z['avg_confidence']} across {z['n']} reviews."],
                    expected_benefit="More labeled baseline examples typically improve confidence calibration in a low-confidence zone.",
                    confidence=0.6, impact_assessment=f"Affects inspections touching the {z['zone']} zone.",
                    required_approvals=["spd_manager"],
                ))
        for z in zones["highest_risk_zones"][:3]:
            if z["miss_rate"] and z["miss_rate"] >= _HIGH_MISS_RATE_THRESHOLD:
                created.append(_create(
                    db, tenant_id, recommendation_type=REC_IMPROVE_ANATOMY_MODEL, source=SOURCE_AI_OBSERVATORY,
                    title=f"Improve anatomy model — {z['zone']}",
                    evidence=[f"Miss rate in {z['zone']} is {z['miss_rate']} across {z['n']} reviews."],
                    expected_benefit="Reduces false negatives in a zone with an elevated real miss rate.",
                    confidence=0.65, impact_assessment=f"Safety-relevant: missed findings in {z['zone']}.",
                    required_approvals=["spd_manager", "admin"],
                ))

    # 3. Knowledge evolution -> revise_inspection_guidance / improve_knowledge_graph.
    evolution = phoenix_knowledge_evolution_service.knowledge_evolution_summary(db, tenant_id)
    for gap in evolution["knowledge_gaps"][:5]:
        created.append(_create(
            db, tenant_id, recommendation_type=REC_REVISE_INSPECTION_GUIDANCE, source=SOURCE_KNOWLEDGE_EVOLUTION,
            title=f"Revise inspection guidance — {gap['finding_type']}",
            evidence=[f"{gap['clinical_case_count']} clinical case(s) with no approved institutional article covering '{gap['finding_type']}'."],
            expected_benefit="Closes a real documented knowledge gap for technicians handling this finding.",
            confidence=0.6, impact_assessment="Affects future inspections of this finding type.",
            required_approvals=["spd_manager"],
        ))
    for conflict in evolution["contradictory_guidance"][:5]:
        created.append(_create(
            db, tenant_id, recommendation_type=REC_UPDATE_SOP, source=SOURCE_KNOWLEDGE_EVOLUTION,
            title=f"Resolve contradictory guidance — {conflict['finding_type']} / {conflict['anatomy_zone']}",
            evidence=[f"Articles {conflict['strict_article_ids']} recommend strict disposition; articles {conflict['lenient_article_ids']} recommend lenient disposition for the same finding+zone."],
            expected_benefit="Removes conflicting guidance that could lead to inconsistent technician decisions.",
            confidence=0.7, impact_assessment="Safety-relevant: conflicting disposition guidance.",
            required_approvals=["spd_manager", "admin"],
        ))
    if evolution["duplicate_candidates"] or evolution["retirement_candidates"]:
        created.append(_create(
            db, tenant_id, recommendation_type=REC_IMPROVE_KNOWLEDGE_GRAPH, source=SOURCE_KNOWLEDGE_EVOLUTION,
            title="Consolidate duplicate and retire outdated knowledge articles",
            evidence=[
                f"{len(evolution['duplicate_candidates'])} duplicate candidate pair(s).",
                f"{len(evolution['retirement_candidates'])} retirement candidate(s).",
            ],
            expected_benefit="A cleaner, less redundant Knowledge Graph improves search relevance and trust.",
            confidence=0.55, impact_assessment="Improves knowledge discoverability platform-wide.",
            required_approvals=["spd_manager"],
        ))

    # 4. Competency opportunities -> create_competency.
    open_opportunities = competency_intelligence_service.list_opportunities(db, tenant_id, status="open")
    if open_opportunities:
        created.append(_create(
            db, tenant_id, recommendation_type=REC_CREATE_COMPETENCY, source=SOURCE_COMPETENCY_INTELLIGENCE,
            title="Create competency plan for open coaching/education opportunities",
            evidence=[o["rationale"] for o in open_opportunities[:5]],
            expected_benefit="Addresses recorded repeated-error patterns before they recur further.",
            confidence=0.65, impact_assessment=f"Affects {len({o['scope_value'] for o in open_opportunities})} technician(s)/team(s).",
            required_approvals=["spd_manager"],
        ))

    # 5. Workflow bottlenecks -> update_workflow.
    workflow_opt = phoenix_workflow_optimization_service.workflow_optimization_summary(db, tenant_id)
    for failure in workflow_opt["repeated_exceptions"][:3]:
        created.append(_create(
            db, tenant_id, recommendation_type=REC_UPDATE_WORKFLOW, source=SOURCE_WORKFLOW_OPTIMIZER,
            title=f"Update workflow {failure['workflow_id']} — repeated failures",
            evidence=[f"{failure['failure_count']} repeated failed executions recorded for workflow {failure['workflow_id']}."],
            expected_benefit="Reduces recurring execution failures and manual rework.",
            confidence=0.6, impact_assessment=f"Affects every future execution of workflow {failure['workflow_id']}.",
            required_approvals=["spd_manager", "admin"], related_object_type="workflow_definition",
            related_object_id=failure["workflow_id"],
        ))

    db.commit()
    for row in created:
        db.refresh(row)
    return [_to_dict(r) for r in created]


def list_recommendations(db: Session, tenant_id: str, *, status: str = "") -> list[dict]:
    q = db.query(ImprovementRecommendation).filter(ImprovementRecommendation.tenant_id == tenant_id)
    if status:
        q = q.filter(ImprovementRecommendation.status == status)
    return [_to_dict(r) for r in q.order_by(ImprovementRecommendation.created_at.desc()).all()]


def get_recommendation(db: Session, tenant_id: str, recommendation_id: int) -> dict:
    row = (
        db.query(ImprovementRecommendation)
        .filter(ImprovementRecommendation.id == recommendation_id, ImprovementRecommendation.tenant_id == tenant_id)
        .first()
    )
    if row is None:
        raise ValueError(f"Recommendation {recommendation_id} not found for tenant {tenant_id}.")
    return _to_dict(row)
