"""v5.4 — Project Nova, Section 8: Agent Marketplace.

Zero new tables. Infinity's `MarketplaceListing`/
`infinity_marketplace_service.py` (v5.0) is already a generic,
developer-owned, review-gated listing pipeline (create ->
submit-for-review -> publish (certification-gated) -> install/
uninstall, plus revenue-sharing). Nova extended `LISTING_TYPES` with 6
new agent-category values; this module only adds a marketplace summary
scoped to those types, mirroring `olympus_marketplace_service.py`'s
Innovation Marketplace pattern.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.infinity_platform import (
    LISTING_PUBLISHED,
    LISTING_TYPE_COMPLIANCE_AGENT,
    LISTING_TYPE_EDUCATION_AGENT,
    LISTING_TYPE_INSPECTION_AGENT,
    LISTING_TYPE_MANUFACTURER_AGENT,
    LISTING_TYPE_RESEARCH_AGENT,
    LISTING_TYPE_SIMULATION_AGENT,
    MarketplaceListing,
)

AGENT_MARKETPLACE_LISTING_TYPES = [
    LISTING_TYPE_INSPECTION_AGENT, LISTING_TYPE_RESEARCH_AGENT, LISTING_TYPE_MANUFACTURER_AGENT,
    LISTING_TYPE_EDUCATION_AGENT, LISTING_TYPE_COMPLIANCE_AGENT, LISTING_TYPE_SIMULATION_AGENT,
]


def agent_marketplace_summary(db: Session) -> dict:
    rows = (
        db.query(MarketplaceListing)
        .filter(
            MarketplaceListing.status == LISTING_PUBLISHED,
            MarketplaceListing.listing_type.in_(AGENT_MARKETPLACE_LISTING_TYPES),
        )
        .all()
    )
    by_type: dict[str, int] = {t: 0 for t in AGENT_MARKETPLACE_LISTING_TYPES}
    for r in rows:
        by_type[r.listing_type] = by_type.get(r.listing_type, 0) + 1
    return {
        "listing_types": AGENT_MARKETPLACE_LISTING_TYPES,
        "total_published": len(rows),
        "by_listing_type": by_type,
    }
