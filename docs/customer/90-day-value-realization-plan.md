# 90-Day Value Realization Plan

Picks up from `docs/customer/60-day-optimization-plan.md`. Days 61–90
shift the conversation from "is it working operationally" to "what value
has it delivered," using the site's own real data rather than industry
benchmarks.

## Weeks 9–10 — Value Data Collection

- Pull the site's real `/api/pilot-analytics/roi` output — labor savings,
  reprocessing avoidance, and cancellation avoidance estimates computed
  from this site's actual inspection volume and contamination-detection
  rate, not generic assumptions
- Pull `/api/cios/dashboard`'s `enterprise_risk_index`,
  `readiness_rate`, and `average_inspection_time_minutes` as the
  quantitative operational baseline
- Compare against the site's own pre-LumenAI baseline where available
  (`baseline_period_days` parameter on the ROI endpoint) rather than only
  industry benchmarks — a customer-specific comparison is more credible
  than an industry-average one

## Weeks 11–12 — Executive Value Review

- Prepare the value realization package using
  `docs/enterprise/roi-framework.md`'s nine value categories, populated
  with this site's real Day 90 figures
- Executive Sponsor review meeting: present measured value, remaining
  gaps, and the expansion recommendation
  (`/api/pilot-analytics/quarterly-review`'s `expansion_recommendations`)
- Identify next-phase opportunities: additional facilities, additional
  instrument families, or upgrading to a higher edition
  (`docs/enterprise/commercial-packaging.md`) if usage has outgrown the
  current one

## Day 90 exit criteria

- [ ] Quantified ROI figures presented to the Executive Sponsor, sourced
  from real site data (not solely industry benchmarks)
- [ ] Go/no-go decision recorded (`/api/pilot-validation/go-no-go`) if
  this site is also part of the formal Phase 18 pilot validation cohort
- [ ] Customer Success Checklist fully complete
  (`docs/customer/customer-success-checklist.md`)
- [ ] Customer Health Score established as an ongoing tracked metric
  (`docs/customer-success/customer-health-framework.md`,
  `docs/enterprise/enterprise-metrics.md`)
- [ ] Renewal-readiness baseline established
  (`docs/customer-success/renewal-readiness-guide.md`)

## Beyond Day 90

Ongoing success is tracked through the ongoing Enterprise Metrics
framework (`docs/enterprise/enterprise-metrics.md`), not a one-time
90-day report — value realization is a continuous measurement, and the
same dashboards used during onboarding remain the source of truth for
every subsequent quarterly business review.
