# LumenAI — Commercial Strategy

Objective 9 review (editions, licensing model, subscription plans, support packages, professional services, implementation packages, training packages). Numeric pricing detail lives in the companion `docs/commercial-readiness/PRICING_MODEL.md` — this document covers the structural/packaging strategy, and its most important contribution is disclosing that **the underlying pricing is not yet approved or internally consistent**, which any commercial-strategy document must state rather than paper over.

## Product editions — three or four competing taxonomies currently coexist

This is the central finding of this review and must be resolved before this strategy can be operationalized:

1. **`docs/commercial/product-packaging.md`** defines Starter / Professional / Enterprise / Health System, with detailed feature/limit tables (facilities, users, inspection volume, baseline storage, SLA, support).
2. **`docs/global/global-commercialization-plan.md`** uses the same four tier names but with **different dollar ranges** for each (see `PRICING_MODEL.md`).
3. **`frontend/src/pages/SubscriptionReadinessPage.tsx`** — the live, running product UI — uses an entirely different taxonomy: **Hospital / Enterprise / Vendor**, with numeric limits (facilities/users/inspections/baselines/storage) that match none of the above tier definitions.
4. **`backend/app/routes/commercial.py`**'s `PACKAGES` dict (the actual, tested, code-backed pricing API) uses Starter/Professional/Enterprise/Health System names again, but with its own numeric limits that don't fully match `product-packaging.md` either.

**This must be resolved before the strategy is externally usable**: pick one edition taxonomy, migrate `SubscriptionReadinessPage.tsx` to match it (or deliberately keep Hospital/Enterprise/Vendor as an internal technical-tier concept distinct from commercial packaging, and say so explicitly), and reconcile `product-packaging.md`/`global-commercialization-plan.md`/`commercial.py` to agree on numeric limits.

## Licensing model

No formal licensing-model document (per-seat vs. per-facility vs. usage-based) was found as a standalone artifact — the tier structures above implicitly mix per-facility caps with per-user caps with inspection-volume caps. This should be made an explicit, named licensing model (e.g., "per-facility base fee with included user/inspection allowances, metered overage above cap") rather than left implicit across four disagreeing documents.

## Subscription plans and support packages

`docs/customer/customer-success-playbook.md`'s CSM tier/cadence model (support responsiveness scaling with subscription tier) is real and directly usable as the support-package structure, cross-referenced with the severity/SLA framework in `docs/commercial-readiness/SUPPORT_OPERATIONS_MANUAL.md`.

## Professional services, implementation packages, training packages

A direct internal contradiction exists here too: `docs/commercial/pricing-strategy.md` prices Health System implementation as a **separate $15,000-$50,000 fee**, while `docs/commercial/product-packaging.md` lists professional services (implementation, training, custom integrations) for the same tier as **"Included."** Resolve this before quoting either figure to a real prospect. No standalone "Training Package" SKU or price exists anywhere — training is currently always bundled into tier support levels, never itemized; per `docs/commercial-readiness/TRAINING_GUIDE.md`'s reuse of Project Sage's real competency infrastructure, this bundling is defensible, but if training packages are meant to be sold as separate line items, that pricing needs new authorship, not reconciliation of existing conflicting figures (there are none to reconcile).

## Pilot pricing and enterprise pricing

A third conflict: `docs/commercial/pricing-strategy.md` prices a Professional-tier pilot at **$1,500/month for 90 days**, while `docs/customer/pilot-program-framework.md` describes the same tier's pilot as a **"Success-Based Pilot... $0 upfront."** These are materially different offers for the same audience and must be reconciled before either is used in a real sales conversation. See `docs/commercial-readiness/PRICING_MODEL.md` for the full numeric detail and the recommended resolution path.

## Status — explicitly not yet approved

`docs/commercial/launch-readiness-checklist.md` itself states: **"Pricing approved by leadership | In Progress; pricing strategy documented; final approval pending."** This commercial strategy document does not change that status — it should not be read as evidence that pricing is finalized, only that the strategic structure (editions, tiers, packaging logic) is well-developed and ready for a final reconciliation-and-approval pass.
