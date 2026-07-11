# Project Sage — Learning Effectiveness Engine

LumenAI AI Specialist, Section 9.

## Real before/after metrics, one learner at a time

`sage_effectiveness_service.measure_learning_plan_effectiveness` compares a
completed `SageLearningPlan`'s before-window (ending at plan creation) and
after-window (starting at plan completion), both real, windowed
recomputations over:

| Brief metric | Real source |
|---|---|
| Inspection coverage | `Inspection.coverage_pct` |
| Supervisor correction rate | `SupervisorReview.agreement != "agree"` |
| Image quality | `Inspection.ai_confidence` (this codebase has no separate image-quality score; AI confidence on image-based inspections is the closest real proxy) |
| Finding accuracy | `SupervisorReview.finding_correct` |
| Anatomy accuracy | `SupervisorReview.zone_correct` |
| Workflow compliance | `SupervisorReview.image_view_correct` + `missing_zone_correct` |

## Classification

A metric only counts as "improved" or "declined" if it moves at least 5
percentage points (`_CHANGE_THRESHOLD_PCT`) in the relevant direction
(lower is better for correction rate; higher is better for everything else).

| Result | Rule |
|---|---|
| `insufficient_evidence` | no metric has data in both windows |
| `improved` | every tracked metric improved |
| `declined` | every tracked metric declined, or declines outnumber improvements |
| `partially_improved` | more metrics improved than declined |
| `unchanged` | equal improved/declined counts (including zero) |

## Never claims causation

The narrative always frames the result as "an observed pattern, not a
confirmed causal effect of the education itself."

## API

```
POST /api/sage/learning-plans/{id}/measure-effectiveness
```

Only callable for a `completed` plan (422 otherwise).
