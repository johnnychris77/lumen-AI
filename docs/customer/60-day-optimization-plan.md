# 60-Day Optimization Plan

Picks up from `docs/customer/30-day-go-live-plan.md` once the site is
live. Days 31–60 focus on adoption depth and data-quality optimization
rather than initial rollout.

## Weeks 5–6 — Adoption Depth

- Expand instrument-family coverage — review
  `/api/pre-sterilization-command-center/baseline-coverage` for instrument
  types still missing an approved baseline and prioritize closing gaps
- Review zone-coverage quality
  (`/api/pre-sterilization-command-center/missing-zone-coverage`) and
  retrain technicians on capture technique for instrument families with
  frequent `not_assessed`/`incomplete` coverage
- Confirm every active SPD shift has at least one trained supervisor
  available to clear the Supervisor Review Queue promptly

## Weeks 7–8 — Data Quality & Feedback Loop

- Review the Knowledge Graph's `learning_confidence` output
  (`/api/knowledge-graph/learning-confidence`) — this is the first point
  where enough real supervisor reviews exist to say something meaningful
  about zone/finding confidence for this site's instrument mix
- Review the Enterprise Knowledge Analytics
  (`/api/knowledge-graph/analytics`) for this site's most common findings,
  highest-risk zones, and most common supervisor overrides — feed
  findings back into technician training
- Address any recurring override patterns: if supervisors consistently
  correct the same zone or finding type, that's a signal for the
  `docs/customer/training-matrix.md` refresh, not just a one-off note

## Day 60 checkpoint

- [ ] Supervisor agreement rate stable or improving vs. Day 30
- [ ] Coverage rate (Phase 23 `/api/cios/dashboard`) trending toward the
  target in `docs/validation/pilot-go-no-go-criteria.md`
- [ ] Zero unresolved critical missed findings older than 48 hours
- [ ] Customer Success Checklist Week 5–8 items complete
  (`docs/customer/customer-success-checklist.md`)
- [ ] Executive Sponsor mid-point business review — early ROI signal
  using `docs/commercial/roi-model.md` inputs specific to this site

## Transition to Day 90

Proceed to `docs/customer/90-day-value-realization-plan.md` once adoption
depth and data quality checkpoints are met. If they are not met, extend
the optimization phase rather than moving to value realization on a
site that hasn't yet stabilized — a premature ROI conversation on
unstable data undermines the customer relationship more than a short
delay does.
