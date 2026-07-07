# Case Studies

## Status: none published yet

No customer case study exists yet. This document defines the template a
real case study will follow once a customer reaches Day 90 value
realization (`docs/customer/90-day-value-realization-plan.md`) and
consents to being featured.

## Case study template

```markdown
# [Facility Name / Anonymized Identifier] Case Study

## Facility profile
- Facility type (community hospital / regional medical center / academic
  medical center — see docs/commercial/roi-model.md segment definitions)
- SPD team size
- Instrument volume/month

## Challenge
What specific pre-sterilization quality problem prompted evaluation?

## Implementation
- Go-live date, timeline vs. the standard 30-day plan
- Instrument families onboarded
- Any notable customization or integration

## Results (Day 90+, using real site data only)
- Readiness rate, coverage rate, supervisor agreement rate
  (from /api/cios/dashboard)
- ROI figures (from /api/pilot-analytics/roi, this site's real inputs)
- Notable findings caught that would otherwise have proceeded to
  packaging (described as quality indicators, never as prevented harm
  claims — see docs/architecture/pre-sterilization-boundary.md)

## Quote
A named or anonymized quote from the Executive Sponsor or SPD Champion,
with their consent.

## Lessons for future implementations
What would this site do differently, or what should LumenAI improve?
Feed into docs/evidence/lessons-learned.md.
```

## Consent and review requirements before publishing

- Written consent from the customer (Executive Sponsor sign-off) is
  required before any case study naming the facility is published
  externally.
- All figures must be pulled from the customer's real, live dashboard
  data at the time of writing — never backfilled or estimated after the
  fact.
- No causal claims — findings are described as quality indicators and
  potential associations, consistent with platform-wide language
  requirements (`docs/architecture/pre-sterilization-boundary.md`).
- No FDA clearance or regulatory approval claims in any case study
  (CLAUDE.md constraint).

## Related

See `docs/customer-success/reference-customer-program.md` for how a
customer becomes eligible and opts in to being referenced publicly.
