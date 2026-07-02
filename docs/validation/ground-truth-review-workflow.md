# Ground-Truth Review Workflow (Phase 18)

How a supervisor review becomes a ground-truth label for clinical performance.
Source: `app.services.ml.ground_truth`, captured on `SupervisorReview`.

## Captured per inspection

- **AI prediction** — recommendation + whether the AI flagged a finding
  (`ai_finding_present`), zone (`ai_zone`), confidence (`ai_confidence`).
- **Supervisor finding** — whether a finding is truly present
  (`supervisor_finding_present`), the finding type.
- **Supervisor zone correction** — `zone_correct` + `corrected_zone`.
- **Final disposition** — `final_disposition` / `corrected_recommendation`.
- **Reviewer rationale** — required for partial-agreement, disagreement, override.

## Ground-truth labels

| AI flagged | Supervisor confirms | Label |
|---|---|---|
| yes | yes | **true_positive** |
| no | no | **true_negative** |
| yes | no | **false_positive** |
| no | yes | **false_negative** |
| unknown | — | **inconclusive** |

The label is computed at submit time by `classify_ground_truth(...)` and stored on
the review (`ground_truth`), so performance can be queried directly.

## Derivation fallback

When the two flags are not sent explicitly, `derive_flags_from_review(...)`
recovers them: the AI flag from its recommendation (a non-pass/monitor
recommendation means it flagged something), and the supervisor flag from
`finding_correct` (correct → supervisor agrees with the AI's flag; incorrect →
the opposite) or the corrected disposition. If either remains unknown, the label
is `inconclusive` — never guessed.

## Honesty

One supervisor per review unless adjudicated; single-rater ground truth is a
documented limitation. No label is inferred beyond the rules above.
