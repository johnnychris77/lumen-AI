# LumenAI — Pricing Model

Objective 9 (pricing detail) review. This document reports the actual numbers found in the repository's four disagreeing pricing sources, rather than picking one silently or averaging them — a sales team using this document must know a reconciliation is still required before any figure here is quoted as final to a real prospect.

## The four sources and where they disagree

| Tier | `docs/commercial/pricing-strategy.md` | `docs/global/global-commercialization-plan.md` | `backend/app/routes/commercial.py` (code, tested) | `SubscriptionReadinessPage.tsx` (live UI) |
|---|---|---|---|---|
| Starter | $2,500/mo ($30,000/yr) | $48,000-$72,000/yr | "Up to 10 SPD users / up to 2,000 inspections/month" | *(no matching tier name — see "Hospital Tier" below)* |
| Professional | $6,500/mo ($78,000/yr), +$1,500/mo/facility beyond 3 | $84,000-$144,000/yr | (not directly quoted in recon) | *(no matching tier name)* |
| Enterprise | $15,000/mo ($180,000/yr) up to 10 facilities, +$1,000/mo/facility beyond | $180,000-$360,000+/yr | (not directly quoted in recon) | 10 facilities / 500 users / 100,000 inspections / 2,000 baselines / 200 GB storage |
| Health System | Custom $250,000-$800,000/yr | $250,000-$1,000,000+/yr | (not directly quoted in recon) | *(no matching tier name)* |
| *(UI-only)* Hospital Tier | — | — | — | 1 facility / 50 users / 5,000 inspections / 200 baselines / 20 GB storage |
| *(UI-only)* Vendor Tier | Manufacturer Portal $500/mo (matches) | — | `manufacturer_portal: base_annual = $6,000` ($500/mo, **this one matches**) | 0 facilities / 25 users / 0 inspections / 500 baselines / 10 GB storage |

**The only figure independently confirmed consistent across sources is the $500/month Manufacturer Portal fee** (`pricing-strategy.md`, `commercial.py`, and `docs/sales/sales-playbook.md` all agree). Every other headline tier price disagrees between at least two of the four sources.

## Discounts — consistent, safe to use as-is

- **Multi-year discount**: 10% for 2-year commitment, 15% for 3-year — this figure is consistent across `pricing-strategy.md`, `docs/sales/sales-playbook.md`, `docs/customer/pilot-program-framework.md`, and `commercial.py`'s `_multi_year_discount`. **Safe to quote.**
- **Multi-facility discount**: `pricing-strategy.md` states 10% (3-5 facilities) / 20% (6+); `commercial.py`'s `_multi_facility_discount` implements a matching structure. **Safe to quote.**
- **RWE program discount**: 5% discount in exchange for clinical data-rights participation — consistent across `pricing-strategy.md` and `docs/sales/sales-playbook.md`.

## Pilot pricing — a real conflict requiring resolution before use

`pricing-strategy.md` prices a Professional-tier pilot at $1,500/month for 90 days. `docs/customer/pilot-program-framework.md` separately describes three pilot tiers — Free Discovery Pilot ($0, 30 days, 1 facility, max 500 inspections), Success-Based Pilot ($0 upfront, convert at list price), and Paid Pilot (50% of list price, 90 days) — and maps "Professional features" to the **Success-Based ($0 upfront)** tier, not the $1,500/month figure. **These describe different offers for the same tier.** Recommend adopting the three-tier pilot-program-framework structure as canonical (it's more fully specified and internally consistent) and retiring the single flat $1,500/month figure, pending business-owner sign-off.

## Professional services / implementation fee — a direct contradiction

`pricing-strategy.md` prices Health System implementation as a separate **$15,000-$50,000 fee**. `docs/commercial/product-packaging.md` lists the same tier's professional services as **"Included."** Do not quote either figure until this is resolved by whoever owns commercial pricing.

## What is real and code-enforced (the closest thing to an authoritative source)

`backend/app/routes/commercial.py`'s `PACKAGES`/`HOSPITAL_PRICING`/`VENDOR_PRICING`/`ENTERPRISE_PRICING` constants and discount functions are genuinely implemented and covered by a real test suite (`backend/tests/test_p17_commercial.py`) — this is the only pricing source in the repository backed by executable, tested code rather than prose. **However, the code's own docstring and the pricing API's own response notes state explicitly: "All monetary figures are list estimates for business-case modeling only... not quotes."** Even the most code-grounded source in this repository disclaims itself as non-binding.

## ROI figures — labeled illustrative, not validated

`docs/commercial/roi-model.md` is explicitly labeled "Values are illustrative ranges based on industry benchmarks and pilot data," with 3-year ROI multiples of 0.86x/1.03x/1.42x across three customer segments. `docs/commercial/launch-readiness-checklist.md` itself confirms: "ROI model validated with pilot data | In Progress... pilot data pending first customer." **No real customer ROI data exists yet to validate these multiples.** Cross-reference `docs/demo-program/EXECUTIVE_PRESENTATION.md`'s identical finding about `ROICenterPage.tsx`/`ValueRealizationPage.tsx`'s hardcoded-benchmark methodology — this is the same underlying limitation appearing in both the product UI and the standalone commercial ROI model.

## Recommendation

1. **Before this program can claim "commercial readiness" on pricing**, a single pricing owner must reconcile the four disagreeing tier-taxonomy/dollar-figure sources into one document, and that document — not this one — becomes the approved source of truth. This document's contribution is surfacing every point of disagreement precisely enough that the reconciliation can happen in one pass rather than being discovered piecemeal during a live sales cycle.
2. Migrate `SubscriptionReadinessPage.tsx`'s Hospital/Enterprise/Vendor taxonomy to match whichever edition names are chosen as canonical, or explicitly document that it represents a different (technical-tier) concept than commercial packaging.
3. Do not publish any of the specific dollar figures above in a customer-facing pricing sheet until this reconciliation is complete and formally approved — per `launch-readiness-checklist.md`'s own admission, pricing approval is still in progress.
