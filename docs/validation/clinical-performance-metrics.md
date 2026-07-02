# Clinical Performance Metrics (Phase 18)

Computed from real supervisor-review ground truth. Source:
`app.services.ml.pilot_validation`. API: `/api/pilot-validation/dashboard`.

## Overall (§4)

From the ground-truth counts (TP/TN/FP/FN):
- **accuracy** = (TP+TN)/(TP+TN+FP+FN)
- **precision** = TP/(TP+FP)
- **recall** = TP/(TP+FN)
- **F1** = harmonic mean of precision & recall
- **false-positive rate** = FP/(FP+TN)
- **false-negative rate** = FN/(FN+TP)
- **supervisor agreement rate** = agree / total reviews
- **override rate** = reviews with an override / total
- **confidence calibration** — realized accuracy per predicted-confidence band
  (0–0.5, 0.5–0.7, 0.7–0.9, 0.9–1.0), so over/under-confidence is visible.

Metrics are `null` when the denominator is zero — never defaulted to a flattering
number.

## Critical safety metrics (§4)

False-negative rate per safety-critical finding — a missed hazard is the primary
risk:
- blood, tissue, organic residue, crack, missing component.
- `worst_safety_false_negative_rate` = the max across these.

FNR here = (reviews of that finding where it was truly present but the AI missed
it) / (reviews where it was truly present).

## Zone performance (§5)

Per high-retention zone (serrations, grooves, drill-bit flutes, threaded regions,
o-ring areas, scope ports, lumens, box locks, hinges, ratchets, insulation
edges): count, missed (FN), overrides, disagreements, average confidence, miss
rate. Ranked views: most-commonly-missed, highest-risk (miss rate),
lowest-confidence, highest-override.

## Instrument-family performance

Per family: review count, agreement rate, accuracy.

## The question this answers

> How well does LumenAI agree with trained SPD supervisors, especially for
> high-risk findings and high-retention instrument zones?

The dashboard's agreement rate, safety FNRs, and zone/family breakdowns are the
evidence.
