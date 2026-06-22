# LumenAI Pricing Strategy
Version 1.0 | Commercial — CONFIDENTIAL
**Internal use only. Subject to revision based on market feedback.**

## Pricing Philosophy
- Value-based pricing anchored to labor savings and risk reduction
- Annual contracts standard; monthly available at 20% premium
- Per-facility model scales naturally with hospital system growth
- Pilot pricing removes budget risk for initial champions

## Subscription Pricing (Annual Contract, Billed Annually)

### Starter
- **List price**: $2,500/month ($30,000/year)
- **Pilot price**: $0 for 90 days (success-based conversion)
- **Target budget owner**: SPD Director, Materials Management

### Professional
- **List price**: $6,500/month ($78,000/year)
- **Per additional facility** (beyond 3): $1,500/month
- **Pilot price**: $1,500/month for 90 days
- **Target budget owner**: VP of Surgical Services, CNO office

### Enterprise
- **List price**: $15,000/month ($180,000/year) for up to 10 facilities
- **Per additional facility** (beyond 10): $1,000/month
- **Multi-year discount**: 10% (2-year), 15% (3-year)
- **Pilot price**: Negotiated; typically $3,000–5,000/month
- **Target budget owner**: COO, CFO, VP Supply Chain

### Health System
- **List price**: Custom (typically $250,000–$800,000/year depending on network size)
- **Basis**: Per-facility × network size × included modules
- **Professional services**: $15,000–$50,000 implementation fee
- **Target budget owner**: C-suite (COO, CFO, CIO, CMO)

## Vendor/Manufacturer Subscription
- **Manufacturer Portal access**: $500/month per manufacturer
- **Vendor Intelligence Premium**: $1,000/month (included in Professional+)
- **FDA Recall Integration (Vendor)**: Included in Manufacturer Portal

## Pricing Levers
| Lever | Description | Impact |
|-------|-------------|--------|
| Multi-facility discount | 10% off per facility tier 3–5, 20% off 6+ | Drives health system deals |
| Multi-year commitment | 10–15% discount for 2–3 year terms | Reduces churn risk |
| EHR integration bundle | +$500/month, removes friction | Increases stickiness |
| Clinical validation opt-in | 5% discount for RWE participants | Grows evidence base |
| GPO pricing | Negotiated via Premier/Vizient/HPG | Reduces sales cycle |

## Competitive Positioning
| Competitor Category | Price Range | LumenAI Advantage |
|--------------------|-------------|------------------|
| Manual audit tools (spreadsheet) | $0 | AI detection, audit trail, benchmarking |
| Legacy tracking software | $5K–$20K/year | CV detection, predictive analytics, copilot |
| General clinical AI platforms | $50K–$500K/year | SPD-specific, faster ROI, lower complexity |
| Full CMMS suites | $100K–$1M/year | Focused scope, faster deployment, SPD-first |

## Discounting Policy
- AE authority: up to 15% discount without approval
- VP Sales: up to 25%
- CEO/CPO approval: >25%
- Strategic discounts (reference customer, case study rights): up to 40%

## Revenue Model Assumptions (Year 1)
| Segment | Target Customers | ACV | ARR |
|---------|-----------------|-----|-----|
| Starter pilots → conversion | 20 pilots, 60% convert | $30K | $360K |
| Professional hospitals | 10 customers | $78K | $780K |
| Enterprise systems | 3 customers | $180K | $540K |
| Health System | 1 customer | $350K | $350K |
| Manufacturer subscriptions | 10 manufacturers | $6K | $60K |
| **Total Year 1 ARR target** | | | **~$2.1M** |

## Pricing API (P17)
The commercial pricing model is exposed via authenticated endpoints for sales tooling:

| Endpoint | Purpose |
|----------|---------|
| `GET /api/commercial/packages` | List all four package tiers and features |
| `GET /api/commercial/packages/{tier}` | Single tier detail (starter/professional/enterprise/health_system) |
| `GET /api/commercial/pricing/hospital` | Hospital per-facility pricing model |
| `GET /api/commercial/pricing/vendor` | Manufacturer/vendor subscription pricing |
| `GET /api/commercial/pricing/enterprise` | Enterprise/Health System pricing model |
| `POST /api/commercial/pricing/estimate` | Non-binding list estimate (tier, facilities, term) |

Estimate logic mirrors this document:
- **Multi-facility discount:** 10% (3–5 facilities), 20% (6+)
- **Multi-year discount:** 10% (2-year), 15% (3-year)
- **Discount cap:** 40% (matches strategic-discount ceiling)
- Health System figures returned are the midpoint of the published $250K–$800K range.

> All API estimates are non-binding list prices for modeling only; not quotes.
