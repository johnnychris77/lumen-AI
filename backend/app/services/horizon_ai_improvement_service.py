"""v3.4 — Project Horizon, Section 10: Global AI Improvement.

Reads only *published, k-anonymity-verified* federated knowledge
(`FederatedLearningSignal`, `GlobalKnowledgeGraphEdge`, `EmergingTrendAlert`)
and produces advisory suggestions for how each of the five named local
systems could be improved — Knowledge Graph, Clinical Reasoning, Zone
Intelligence, Digital Twins, Prediction Models. Every suggestion is
advisory only: this service never mutates any local system's parameters,
baselines, or models — a human reviews and applies (or dismisses) each
suggestion locally.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.federated_horizon import (
    DISCLAIMER,
    IMPROVEMENT_TARGET_CLINICAL_REASONING,
    IMPROVEMENT_TARGET_DIGITAL_TWINS,
    IMPROVEMENT_TARGET_KNOWLEDGE_GRAPH,
    IMPROVEMENT_TARGET_PREDICTION_MODELS,
    IMPROVEMENT_TARGET_ZONE_INTELLIGENCE,
    EmergingTrendAlert,
    FederatedLearningSignal,
    GlobalKnowledgeGraphEdge,
)


def generate_improvement_suggestions(db: Session) -> list[dict]:
    suggestions: list[dict] = []

    for edge in db.query(GlobalKnowledgeGraphEdge).filter(GlobalKnowledgeGraphEdge.published.is_(True)).order_by(GlobalKnowledgeGraphEdge.id.desc()).limit(20).all():
        suggestions.append({
            "target_system": IMPROVEMENT_TARGET_KNOWLEDGE_GRAPH,
            "suggestion": (
                f"Global data shows {edge.target_node_value} recurring on {edge.source_node_value} across "
                f"{edge.tenant_count} organizations — consider adding this relationship to the local Knowledge Graph's "
                "recommended-action mapping for this instrument/zone."
            ),
            "evidence": [{"factor": "tenant_count", "value": edge.tenant_count}, {"factor": "observation_count", "value": edge.observation_count}],
            "confidence": edge.confidence,
            "human_review_required": True,
        })

    for signal in db.query(FederatedLearningSignal).filter(FederatedLearningSignal.published.is_(True)).order_by(FederatedLearningSignal.id.desc()).limit(20).all():
        if signal.signal_category == "instrument_failure_pattern" and (signal.value or 0) > 0.1:
            suggestions.append({
                "target_system": IMPROVEMENT_TARGET_PREDICTION_MODELS,
                "suggestion": f"Elevated failure rate observed globally for {signal.scope_key} — consider reviewing local prediction model risk weighting for this instrument type.",
                "evidence": [{"factor": "tenant_count", "value": signal.tenant_count}, {"factor": "failure_rate", "value": signal.value}],
                "confidence": min(0.9, signal.tenant_count / 20),
                "human_review_required": True,
            })
        if signal.signal_category == "anatomy_trend":
            suggestions.append({
                "target_system": IMPROVEMENT_TARGET_ZONE_INTELLIGENCE,
                "suggestion": f"The {signal.scope_key} zone shows recurring findings across {signal.tenant_count} organizations — consider reviewing local zone risk weighting.",
                "evidence": [{"factor": "tenant_count", "value": signal.tenant_count}],
                "confidence": min(0.9, signal.tenant_count / 20),
                "human_review_required": True,
            })
        if signal.signal_category == "coverage_effectiveness" and signal.value is not None and signal.value < 80:
            suggestions.append({
                "target_system": IMPROVEMENT_TARGET_CLINICAL_REASONING,
                "suggestion": f"Global coverage effectiveness for {signal.scope_key} is below 80% — consider reviewing local clinical reasoning guidance for this instrument type's zone coverage checklist.",
                "evidence": [{"factor": "tenant_count", "value": signal.tenant_count}, {"factor": "coverage_pct", "value": signal.value}],
                "confidence": min(0.9, signal.tenant_count / 20),
                "human_review_required": True,
            })

    for trend in db.query(EmergingTrendAlert).filter(EmergingTrendAlert.status != "resolved").order_by(EmergingTrendAlert.id.desc()).limit(20).all():
        suggestions.append({
            "target_system": IMPROVEMENT_TARGET_DIGITAL_TWINS,
            "suggestion": f"Emerging trend detected: {trend.description} Consider reviewing local Digital Twin lifecycle risk parameters for affected instrument types.",
            "evidence": [{"factor": "tenant_count", "value": trend.tenant_count}, {"factor": "severity", "value": trend.severity}],
            "confidence": min(0.9, trend.tenant_count / 20),
            "human_review_required": True,
        })

    return suggestions


def improvement_summary(db: Session) -> dict:
    suggestions = generate_improvement_suggestions(db)
    by_target: dict[str, int] = {}
    for s in suggestions:
        by_target[s["target_system"]] = by_target.get(s["target_system"], 0) + 1
    return {
        "suggestions": suggestions, "count_by_target_system": by_target,
        "human_review_required": True, "disclaimer": DISCLAIMER,
    }
