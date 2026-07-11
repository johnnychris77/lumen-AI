# Project Infinity — Billing & Licensing

LumenAI OS v5.0, Section 8.

## Module Licensing — reused, not rebuilt

Genesis's `platform_licensing_service.py` (`PlatformModuleLicense`, v4.0)
already tracks per-tenant module entitlement (`enabled`/`disabled`/
`trial`). Infinity composes it directly for "Module Licensing" — no
second per-module license table.

```
GET /api/infinity/billing/module-licenses
```

## Enterprise & Partner Licensing — genuinely new

P14's billing infrastructure (`TenantPlan`/`PaymentEvent`/
`TenantUsageCounter`) is entirely inspection-volume subscription billing
— there was no home anywhere for commercial licensing *terms* (as
opposed to a simple enabled/disabled flag). `PartnerLicense` is a new,
additive table distinct from `PlatformModuleLicense`, covering
`module` | `enterprise` | `partner` license types with real terms,
effective/expiration dates, and an optional revenue-share percentage.

```
POST /api/infinity/billing/partner-licenses
GET  /api/infinity/billing/partner-licenses
POST /api/infinity/billing/partner-licenses/{id}/revoke
```

## Marketplace Revenue Sharing — genuinely new

No revenue-sharing ledger concept existed anywhere in this codebase
before Infinity. `MarketplaceRevenueEvent` records the real gross amount
of a subscription charge, one-time purchase, or usage fee for a listing,
and splits it into `developer_share_cents`/`platform_share_cents` using
either the listing's `PartnerLicense.revenue_share_pct` override or a
documented default split (70% developer / 30% platform) — the split
percentage is always visible in the response, never a hidden
computation.

```
POST /api/infinity/billing/revenue-events
GET  /api/infinity/billing/revenue-events/listings/{id}/summary
```

Every total in `revenue_summary_for_listing` is summed only from real
recorded `MarketplaceRevenueEvent` rows — nothing is projected or
estimated.
