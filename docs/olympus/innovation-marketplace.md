# Project Olympus — Innovation Marketplace

LumenAI OS v5.1, Section 8.

## Reuses Infinity's marketplace directly — no second marketplace model

Infinity's `MarketplaceListing`/`infinity_marketplace_service.py` (v5.0)
is already a generic, developer-owned, review-gated listing pipeline:
create → submit-for-review → publish (certification-gated) → install/
uninstall, plus revenue-sharing. Olympus does not rebuild any of that.

Olympus extends Infinity's `LISTING_TYPES` vocabulary with the six new
types the brief names, alongside the pre-existing `ai_skill`:

| Brief item | `listing_type` |
|---|---|
| Workflow packs | `workflow_pack` |
| Knowledge packs | `knowledge_pack` |
| Training modules | `training_module` |
| Analytics dashboards | `analytics_dashboard` |
| Research datasets | `research_dataset` |
| AI skills | `ai_skill` (pre-existing) |
| Simulation templates | `simulation_template` |

Every one of Infinity's existing marketplace endpoints
(`/api/infinity/marketplace/listings`, `/installations`, and
`/api/infinity/certification/listings/{id}/...`) already works against
these new types with no code change — `listing_type` is validated only
against the `LISTING_TYPES` list, not hardcoded per type.

## What Olympus adds

Only a network-facing summary grouped by the Innovation-Marketplace-
specific listing types, since Infinity's own summaries weren't scoped to
this particular subset:

```
GET /api/olympus/marketplace/summary
```

"Marketplace items undergo review before publication" (Section 8) is
already enforced by Infinity's `publish_listing`, which raises
`ListingNotCertifiedError` unless the listing's certification chain (see
`docs/olympus/model-registry.md`) reports `certified`.
