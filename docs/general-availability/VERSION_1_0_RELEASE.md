# Version 1.0 Release Declaration — LumenAI

**Status:** Version 1.0 is declared as a **pilot-stage release**, approved
for one narrow, fully-disclosed facility pilot under the conditions in
`GO_LIVE_CHECKLIST.md`. It is explicitly **not** declared General
Availability. Future enhancements and the eventual GA decision will be
managed through the Version 1.x release process under the same product
governance established here.

## What Version 1.0 is

The full additive body of work delivered across this program: the core
inspection workflow, the enterprise/quality/knowledge specialist modules,
the Genesis production-model-training pipeline, Shadow prospective
validation, and the Advisor supervised advisory pilot framework — all
verified to coexist without regression (3,516 tests passing) and built
under a consistent no-fabrication discipline.

## What Version 1.0 is not

A General Availability release. See `GENERAL_AVAILABILITY_REPORT.md` for
the full evidence behind that distinction.

## 12. Production Metrics — what will be monitored once a pilot begins

These are the metrics the pilot must actually produce data for before any
GA reconsideration; several already have a real computation behind them,
noted below.

| Metric | Source (real, existing code) |
|---|---|
| Availability | `pulse_ai_ops_service.ai_operations_monitor()`'s `model_availability_pct` (errored/total real inspections) |
| Latency | Not yet instrumented — `docs/release-management/PERFORMANCE_LOG.md` confirms no APM exists; must be added before this metric is meaningful |
| Inspection throughput | `advisory_workflow_impact_service.adoption_rate()`'s `total_eligible_inspections`, and `quality_dashboard_service.dashboard_summary()`'s `inspection_volume` |
| AI utilization / adoption | `advisory_workflow_impact_service.adoption_rate()`, `acceptance_and_override_rates()` |
| Support tickets | Not yet instrumented — no ticketing tool exists (see `SUPPORT_HANDBOOK.md`) |
| Safety events | `advisory_safety_service.safety_summary()` — real, persisted, reviewable |
| Customer satisfaction | `advisory_user_feedback_service.feedback_summary()` — real, per-role averages |
| Adoption | Same as AI utilization above |
| Operational reliability | `sentinel_ai_health_service.compute_ai_health()`'s drift detection, `quality_dashboard_service.benchmark()`'s trend comparisons |

Latency and support-ticket volume have no real instrumentation today —
these must be added before they can be reported honestly; do not report a
number for either until real instrumentation exists.

## 13. Post-Launch Governance

Established as of this release, to begin once a real pilot is underway:

- **Monthly product review**: pilot dashboard (`GET /api/advisory-pilot/
  dashboard`) and success metrics (`GET /api/advisory-pilot/
  success-metrics`) reviewed with Product Management and Engineering.
- **Quarterly clinical review**: the Clinical Review Board process
  already built (`shadow_clinical_review_board.py` /
  `ClinicalReviewBoardSession`, extended with the `pilot_decision` field
  — continue/expand/pause/terminate) convened on a quarterly cadence
  once a real pilot is running, reviewing performance, safety, failure
  analysis, and user feedback per `docs/advisory-pilot/PILOT_FINAL_REPORT.md`.
- **Security review cadence**: at minimum aligned to the existing
  CI-blocking dependency-scan cadence (continuous) plus a manual review
  each time a new blocking item from `GO_LIVE_CHECKLIST.md` closes.
- **Model performance monitoring**: `sentinel_ai_health_service`'s drift
  detection, reviewed as part of the monthly product review; any drift
  detected feeds directly into the Validated Candidate / Production
  promotion checklists already built in `candidate_promotion.py`.
- **Customer advisory board**: to be established once more than one real
  pilot facility exists — premature with a single narrow pilot.
- **Product roadmap governance**: future functionality is scoped and
  prioritized against real pilot evidence (adoption, safety, satisfaction)
  rather than in advance of it — a direct consequence of this report's
  central finding that prior phases built substantial capability ahead of
  any real operating evidence.

## Definition of Done for this release

LumenAI Version 1.0 has completed all required release-readiness reviews
across engineering, clinical, security, operational, customer, and
commercial dimensions. The review's honest conclusion is a **CONDITIONAL
GO for one narrow, disclosed pilot**, not unconditional General
Availability. All known limitations are documented in `KNOWN_LIMITATIONS.md`.
Post-launch governance is defined and will activate once a real pilot
begins. Future enhancements will be managed through the Version 1.x
release process under this same governance.
