# Benefits Realization Engine

`steward_benefits_realization_service.record_outcome_review` compares one
expected metric against its actual measured value and classifies the result.

## Classification logic

Given `baseline`, `expected`, `actual`, and a `higher_is_better` flag:

1. If `actual` or `expected` is missing, the classification is always
   `inconclusive` -- **Steward never claims success without a real measured
   value.** This is deliberate: inconclusive evidence must never be reported
   as achieved.
2. If the actual value meets or exceeds expected: `exceeded_expectations` (if
   strictly better) or `achieved` (if exactly met).
3. If it falls short of expected but still improved on baseline:
   `partially_achieved`.
4. If it falls short of expected and did not improve on baseline:
   `not_achieved`, or `worsened` if it is strictly worse than baseline.

## Classifications

`exceeded_expectations`, `achieved`, `partially_achieved`, `not_achieved`,
`worsened`, `inconclusive`.

## Rollup

The most recent classification is rolled up onto the Governed Action's own
`benefits_realization` field so workspace and board views never need to
re-derive it from the full `GovernedActionOutcomeReview` history -- but the
full history remains queryable via `list_outcome_reviews` for the Benefits
Realization Report.

## Avoiding unsupported causal claims

Steward never asserts that an action *caused* a measured change -- it only
reports the comparison between expected and actual values. Aegis's own
process-variation finding and Vulcan's own reliability-outcome finding
(Sections 16-17) are surfaced separately and are never merged into a single
attributed "Steward caused this" statement.
