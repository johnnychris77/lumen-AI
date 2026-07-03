# ROI Framework

Expands `docs/commercial/roi-model.md` (illustrative, benchmark-based
model) and `/api/pilot-analytics/roi` (real, live-data computation from
`app/routes/pilot_analytics.py`) into the nine value categories an
enterprise buyer expects a mature ROI framework to cover.

## The nine value categories

| Category | Source today | Status |
|---|---|---|
| **Inspection Time Saved** | `MINUTES_SAVED_PER_INSPECTION` × real inspection volume (`/api/pilot-analytics/inspection-efficiency`) | Real, computed live |
| **Supervisor Time Saved** | Not yet separately tracked — inspection time savings currently bundle technician and supervisor time together | Gap — see below |
| **Reduction in Reprocessing Events** | `reprocessing_avoidance_usd` in `/api/pilot-analytics/roi`, from real contamination-detection counts | Real, computed live |
| **Reduction in Missing Contamination** | Phase 18's critical finding false-negative rate (`/api/pilot-validation/metrics`) — a lower FN rate is the direct measure of fewer missed contamination events | Real, computed live from ground truth |
| **Reduction in Instrument Damage** | Phase 20's repair/remove-from-service queue trend over time (`/api/pre-sterilization-command-center/repair-remove-queue`) | Real, computed live |
| **Improved Compliance** | Audit log completeness, coverage rate (`/api/cios/dashboard`'s `coverage_rate`), and the Clinical Decision Ledger's completeness for every reviewed inspection | Real, computed live |
| **Training Efficiency** | Not yet quantified — the Training Matrix (`docs/customer/training-matrix.md`) defines *what* training is required; time-to-competency is not yet measured | Gap — see below |
| **Operational Visibility** | The existence and adoption of `/pre-sterilization-command-center`, `/cios-dashboard`, `/knowledge-graph`, `/pilot-validation` themselves — visibility that did not exist pre-LumenAI | Real (qualitative); adoption/usage frequency trackable via `docs/enterprise/enterprise-metrics.md` |
| **Executive Reporting** | The Executive Command Center, CIOS Dashboard, and quarterly review package (`/api/pilot-analytics/quarterly-review`) | Real, computed live |

## Honest gaps

Two categories are not yet independently quantified, stated plainly
rather than papered over with an estimate presented as real:

1. **Supervisor Time Saved** — currently folded into the general
   inspection-efficiency estimate rather than isolated. Isolating it
   would require timing the supervisor-review step specifically (the
   Clinical Decision Ledger's timestamps, Phase 23, make this
   computable in a future release — see
   `docs/cios/clinical-decision-ledger.md`).
2. **Training Efficiency** — the Training Matrix defines training
   requirements but the platform does not yet measure time-to-competency
   against them. A future enhancement could track "days from go-live to
   a technician's first unsupervised, zero-correction week" as a direct
   proxy.

## How to present ROI to a customer

1. Always lead with the customer's own real data
   (`/api/pilot-analytics/roi?baseline_period_days=N` for a
   before/after comparison against their own pre-LumenAI period) —
   this is more credible than an industry benchmark.
2. Use `docs/commercial/roi-model.md`'s segment benchmarks only when
   real customer data isn't yet available (e.g. during a sales
   conversation before implementation).
3. Never present an estimate as if it were measured — every ROI
   endpoint response includes `human_review_required: true` and
   explicit disclaimers that figures require site financial validation.

## Where this feeds

`docs/customer/90-day-value-realization-plan.md` is where this framework
is first applied to a real customer; `docs/enterprise/enterprise-metrics.md`
tracks ROI achievement as an ongoing metric thereafter.
