# User Feedback Plan

**Status:** New this pass (Advisor). **Code:**
`backend/app/models/advisory_pilot.py` (`AdvisoryUserFeedback`),
`backend/app/services/advisory_user_feedback_service.py`.

## Why a new feedback model

No existing model in this codebase collects structured technician/
supervisor trust-in-AI feedback. `SageFeedback` (Project Sage) is about
learning-plan/coaching recommendations; `VulcanFeedback` (Project Vulcan)
is about instrument-reliability predictions — different domains.
`AdvisoryUserFeedback` is the first feedback mechanism scoped to trust in
an AI clinical recommendation itself.

## Respondent roles (§7)

Structured feedback is collected from: technicians, supervisors,
managers, quality, and biomedical engineering — `submitted_role` is a
free-text-but-conventioned field (`technician | supervisor | manager |
quality | biomedical_engineering`).

## Dimensions measured

Each 1-5, nullable — a respondent may skip a dimension, and an unrated
dimension is never assumed to be neutral or averaged in as a default:

| Dimension | Field |
|---|---|
| Ease of use | `ease_of_use` |
| Trust | `trust` |
| Clarity | `clarity` |
| Explainability | `explainability_rating` |
| Confidence | `confidence` |
| Perceived value | `perceived_value` |

Plus free-text `suggestions`.

## Aggregation

`feedback_summary()` reports an overall average per dimension (over
respondents who actually rated it) and a per-role breakdown, plus the
full list of free-text suggestions — nothing is fabricated when a
dimension or role has zero responses (`None`, not `0`).

## API

- `POST /api/advisory-pilot/feedback` — submit feedback.
- `GET /api/advisory-pilot/feedback/summary` — the aggregated view.

## Use

Feedback summaries feed the Pilot Dashboard (`PILOT_DASHBOARD_GUIDE.md`),
`SUCCESS_METRICS.md`'s user-satisfaction metric, and the Clinical Review
Board's periodic review (`PILOT_PROTOCOL.md` §11).
