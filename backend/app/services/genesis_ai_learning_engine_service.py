"""v5.3 — Project Genesis AI, Section 5: Global Learning Engine.

Zero new tables. Horizon's `horizon_federated_signal_service.py`/
`horizon_ai_improvement_service.py` (v3.4, Section 10) already aggregate
de-identified signals (inspection findings, anatomy trends, instrument
failure patterns, coverage effectiveness) and already generate advisory
hypotheses for human review -- reused directly, never re-derived.
"Model performance" and "Workflow effectiveness" reuse Phoenix's
`compute_ai_health_score`/`compute_workflow_health_score`
(`phoenix_platform_health_service.py`, v4.9) directly. "Knowledge
adoption" is the one genuinely new lightweight metric here -- how much
of the knowledge base is actually being used, not how healthy it is
(Phoenix's `compute_knowledge_health_score` already answers the latter).
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.knowledge import KnowledgeArticle
from app.services import horizon_ai_improvement_service, horizon_federated_signal_service, phoenix_platform_health_service


def compute_knowledge_adoption(db: Session, tenant_id: str) -> dict:
    articles = db.query(KnowledgeArticle).filter(KnowledgeArticle.tenant_id == tenant_id).all()
    if not articles:
        return {"score": None, "note": "insufficient data — no knowledge articles recorded yet for this tenant"}
    viewed = sum(1 for a in articles if a.view_count > 0)
    return {
        "score": round(100.0 * viewed / len(articles), 1),
        "total_articles": len(articles),
        "articles_ever_viewed": viewed,
    }


def global_learning_summary(db: Session, tenant_id: str) -> dict:
    return {
        "federated_signals": horizon_federated_signal_service.list_federated_signals(db),
        "improvement_hypotheses": horizon_ai_improvement_service.generate_improvement_suggestions(db),
        "model_performance": phoenix_platform_health_service.compute_ai_health_score(db, tenant_id),
        "workflow_effectiveness": phoenix_platform_health_service.compute_workflow_health_score(db, tenant_id),
        "knowledge_adoption": compute_knowledge_adoption(db, tenant_id),
        "human_review_required": True,
    }
