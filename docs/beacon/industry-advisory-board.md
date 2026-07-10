# Project Beacon — Industry Advisory Board Module

LumenAI v3.5 — Section 10

## Board membership is reused; meeting tracking is genuinely new

P24's `AdvisoryConsortiumMember` is a membership roster (organization
type, tier, voting rights) — it has never tracked a meeting, an action
item, or a roadmap recommendation. `beacon_advisory_board_service.py`
reuses the roster directly (`board_members` calls
`beacon_collaboration_hub_service.collaboration_hub_summary`) and adds
three genuinely new additive tables in
`app/models/industry_collaboration.py`:

  * `AdvisoryBoardMeeting` — title, scheduled time, status
    (scheduled/completed/cancelled), attendee organizations, notes,
    roadmap feedback.
  * `AdvisoryBoardActionItem` — tied to a meeting, owner, due date,
    status (open/in_progress/done).
  * `AdvisoryBoardRecommendation` — title, rationale, target area,
    status (proposed/under_review/adopted/declined), optionally tied to
    a meeting.

## Advisory only — never auto-applied

Every recommendation carries `human_review_required: true` without
exception. `decide_recommendation` only ever changes a recommendation's
own status field (adopted/declined/under_review) — no function in this
module writes to any other system's baselines, weights, or parameters.
A human decides whether and how to act on an adopted recommendation.

## Endpoints

```
GET  /api/beacon/advisory-board                                   — members, meetings, open action items, recommendations
POST /api/beacon/advisory-board/meetings
GET  /api/beacon/advisory-board/meetings
POST /api/beacon/advisory-board/meetings/{meeting_id}/notes
POST /api/beacon/advisory-board/action-items
GET  /api/beacon/advisory-board/action-items
POST /api/beacon/advisory-board/action-items/{item_id}/resolve
POST /api/beacon/advisory-board/recommendations
GET  /api/beacon/advisory-board/recommendations
POST /api/beacon/advisory-board/recommendations/{recommendation_id}/decide
```
