# LumenAI — Customer Success Playbook (Commercial Readiness Edition)

Objective 3 review. **This is a different document from `docs/demo-program/CUSTOMER_SUCCESS_PLAYBOOK.md`** (Phase 5's version, which covers the Administrator Guide/FAQ/Troubleshooting content) — this Phase 6 edition covers the success-milestone/QBR/health-score/renewal process itself, per this program's Objective 3 scope. Cross-reference, don't duplicate, both documents when assembling a full customer-facing package.

## A now-larger reconciliation problem, updated from Phase 5's finding

Phase 5's `docs/demo-program/CUSTOMER_SUCCESS_PLAYBOOK.md` already flagged three disagreeing Customer Health Score formulas (`docs/customer/customer-success-playbook.md`'s 30/25/20/15/10% weights, `docs/customer-success/customer-health-framework.md`'s 5-factor 20%-each formula, and `CustomerSuccessDashboard.tsx`'s own independent `computeHealth()`). This Phase 6 recon surfaces a **fourth candidate document**, `docs/commercial/customer-success-playbook.md`, in a directory not examined during Phase 5. **This document does not attempt to adjudicate a fourth formula on top of the three already flagged** — it reaffirms Phase 5's decision to treat `docs/customer/customer-success-playbook.md`'s formula as canonical, and flags `docs/commercial/customer-success-playbook.md` as a fourth item requiring reconciliation in the same cleanup pass, rather than expanding scope by picking a new canonical source unilaterally.

## Success milestones and implementation timeline

Reference `docs/customer/implementation-timeline.md`'s Day 0→90 lifecycle diagram and `docs/customer/customer-success-playbook.md`'s 30/60/90/180-day milestone definitions directly — these are real and specific.

## Weekly check-ins and quarterly business reviews

`docs/customer/customer-success-playbook.md`'s CSM tier/cadence model already ties QBR frequency to subscription tier (Starter=Annual, Professional=Semi-annual, Enterprise=Quarterly, Health System=Monthly, per `docs/customer/pilot-program-framework.md`'s corroborating cadence table) — use this tier-linked cadence directly rather than a flat weekly/quarterly schedule for every customer.

## Health score and adoption metrics

Use the canonical formula designated in `docs/demo-program/CUSTOMER_SUCCESS_PLAYBOOK.md` (30/25/20/15/10% weights across adoption/inspections/baseline/engagement/completeness). Adoption-metric backing is real: `docs/pilot/pilot-success-metrics.md`'s Adoption/Data Quality/Operational Value/User Satisfaction tables with numeric targets (e.g. WAU ≥80%, field completeness ≥95%) are already computed from real, persisted data via `backend/app/routes/pilot_analytics.py`.

## Escalation paths

Reference `docs/customer/customer-success-playbook.md`'s Trend Monitoring / SEV1-SEV2 support-tier escalation language directly (CS Lead call within 24-48h). For the underlying governed-tracking mechanism behind any escalation, cite Steward's real action-lifecycle state machine (`docs/agents/steward/action-lifecycle.md`) as the platform infrastructure, per `docs/demo-program/PILOT_IMPLEMENTATION_GUIDE.md`'s existing framing — do not re-describe Steward here, only reference it.

## Renewal planning

`docs/customer/customer-success-playbook.md`'s Renewal Playbook (multi-year discount terms) and `docs/customer-success/renewal-readiness-guide.md`'s objection-handling table are both real and directly usable. Cross-reference `docs/commercial-readiness/PRICING_MODEL.md` for the underlying discount figures (10%/15% for 2-/3-year terms) — that document is the canonical source for the numbers; this playbook only describes the renewal *process*.

## What this document adds

The genuinely new contribution here, beyond indexing existing content, is the explicit reconciliation instruction above: **before any of this content ships to a real customer, someone must pick one Customer Health Score formula from the (now four) candidates and update the other three documents/dashboard to match it.** This is a concrete, scoped cleanup task this review surfaces rather than obscures.
