"""v5.1 — Project Olympus, Section 8: Innovation Marketplace.

Infinity's `infinity_marketplace_service.py` (v5.0) is already a
generic, developer-owned, review-gated listing pipeline
(create/submit-for-review/publish/install/uninstall). Olympus's
Innovation Marketplace does not duplicate any of that -- it reuses
`infinity_marketplace_service.py` directly against the 6 new
`LISTING_TYPES` this sprint added (`workflow_pack`, `knowledge_pack`,
`training_module`, `analytics_dashboard`, `research_dataset`,
`simulation_template`) plus the pre-existing `ai_skill` type. This module
only adds the one genuinely new thing the brief names that Infinity's
marketplace didn't need: a network-facing summary grouped by the
Innovation-Marketplace-specific listing types.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.infinity_platform import (
    LISTING_PUBLISHED,
    LISTING_TYPE_AI_SKILL,
    LISTING_TYPE_ANALYTICS_DASHBOARD,
    LISTING_TYPE_KNOWLEDGE_PACK,
    LISTING_TYPE_RESEARCH_DATASET,
    LISTING_TYPE_SIMULATION_TEMPLATE,
    LISTING_TYPE_TRAINING_MODULE,
    LISTING_TYPE_WORKFLOW_PACK,
    MarketplaceListing,
)

INNOVATION_MARKETPLACE_LISTING_TYPES = [
    LISTING_TYPE_WORKFLOW_PACK, LISTING_TYPE_KNOWLEDGE_PACK, LISTING_TYPE_TRAINING_MODULE,
    LISTING_TYPE_ANALYTICS_DASHBOARD, LISTING_TYPE_RESEARCH_DATASET, LISTING_TYPE_SIMULATION_TEMPLATE,
    LISTING_TYPE_AI_SKILL,
]


def innovation_marketplace_summary(db: Session) -> dict:
    rows = (
        db.query(MarketplaceListing)
        .filter(
            MarketplaceListing.status == LISTING_PUBLISHED,
            MarketplaceListing.listing_type.in_(INNOVATION_MARKETPLACE_LISTING_TYPES),
        )
        .all()
    )
    by_type: dict[str, int] = {t: 0 for t in INNOVATION_MARKETPLACE_LISTING_TYPES}
    for r in rows:
        by_type[r.listing_type] = by_type.get(r.listing_type, 0) + 1
    return {
        "listing_types": INNOVATION_MARKETPLACE_LISTING_TYPES,
        "total_published": len(rows),
        "by_listing_type": by_type,
    }
