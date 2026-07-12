"""Project Maestro: materializing a "Generate CAPA draft" recommendation.

Thin wrapper over the pre-existing `capa_suggestion_service` -- Maestro
never invents its own CAPA-detection logic. This is the explicit,
human-triggered action a leader takes after approving a
`generate_capa_draft` recommendation in the Decision Journal; nothing here
runs automatically.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.maestro_orchestration import RECOMMENDATION_GENERATE_CAPA_DRAFT, MaestroRecommendation
from app.services.capa_suggestion_service import create_capa_from_suggestion, generate_capa_suggestions


def create_capa_from_recommendation(
    db: Session, tenant_id: str, recommendation_id: int, *, owner: str = "Quality / Operations",
) -> dict | None:
    """Re-derives the live CAPA suggestion matching the recommendation's
    recorded subject and materializes it. Returns `None` if the
    recommendation is not a CAPA-draft recommendation, or if the
    triggering pattern is no longer present (e.g. already remediated)."""
    recommendation = (
        db.query(MaestroRecommendation)
        .filter(MaestroRecommendation.tenant_id == tenant_id, MaestroRecommendation.id == recommendation_id)
        .first()
    )
    if recommendation is None or recommendation.recommendation_type != RECOMMENDATION_GENERATE_CAPA_DRAFT:
        return None

    import json

    evidence = json.loads(recommendation.evidence_json or "{}")
    suggested_title = evidence.get("suggested_title")

    suggestions = generate_capa_suggestions(db, tenant_id)
    match = next((s for s in suggestions if s["suggested_title"] == suggested_title), None)
    if match is None and suggestions:
        match = suggestions[0]
    if match is None:
        return None

    return create_capa_from_suggestion(match, owner=owner)
