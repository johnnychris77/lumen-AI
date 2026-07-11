# Project Infinity — AI Skills Marketplace & Application Marketplace

LumenAI OS v5.0, Sections 4 & 5.

## One generic listing model, not two

Forge's `WorkflowDefinition.marketplace_status` (v4.1,
`forge_marketplace_service.py`) is a real, narrow marketplace for
workflow templates only — no author identity, no pricing, no generic
listing abstraction. Infinity's `MarketplaceListing` is genuinely new and
covers both marketplaces the brief names via a `listing_type`
discriminator (`ai_skill` | `application`), reusing Forge's exact
`private`/`pending_review`/`published` state names for consistency but
not its table.

| AI Skill categories (Section 4) | Application categories (Section 5) |
|---|---|
| Inspection, Knowledge, Forecast, Reporting, Research, Education | Hospital, Manufacturer, Repair Vendor, Academic, Research, Enterprise, Consulting |

## Publication is gated by certification

A listing can only move from `pending_review` to `published` once its
linked Certification Program chain (`docs/infinity/certification.md`)
reports `certified` — enforced in code (`publish_listing` raises
`ListingNotCertifiedError` otherwise), not left to convention.

```
POST /api/infinity/marketplace/listings
GET  /api/infinity/marketplace/listings?listing_type=ai_skill
GET  /api/infinity/marketplace/listings/{id}
POST /api/infinity/marketplace/listings/{id}/submit-for-review
POST /api/infinity/marketplace/listings/{id}/publish
POST /api/infinity/marketplace/listings/{id}/unpublish
```

## Organizations choose what to install

`MarketplaceInstallation` tracks which tenant installed which listing, at
which version — installing an unpublished listing is rejected.

```
POST /api/infinity/marketplace/installations
GET  /api/infinity/marketplace/installations
POST /api/infinity/marketplace/installations/{id}/uninstall
```
