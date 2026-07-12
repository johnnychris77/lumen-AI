# Project Vulcan — Instrument Reliability Score

LumenAI AI Specialist, Section 7.

## 0–100 composite, with a transparent breakdown

`vulcan_reliability_score_service.compute_reliability_score` starts at 100
and applies itemized penalties, returned verbatim in
`VulcanReliabilityAssessment.score_breakdown_json` so every point deducted
is traceable to a real factor:

| Factor | Penalty |
|---|---|
| Progression (`rapidly_worsening`/`slowly_worsening`/`unresolved`/`intermittent`) | up to -25 |
| Repeated findings (recurrence count) | up to -20 |
| Structural condition (latest severity index) | up to -15 |
| Repair recurrence (repair outcome) | up to -15 |
| Anatomy-zone risk (high-risk zone per `instrument_anatomy.py`) | -5 |
| Supervisor concerns flagged | -10 |
| Baseline deviation | -8 |
| Evidence quality (low-confidence progression) | -5 |

Score is clamped to [0, 100].

## Explicit exclusion

**Sterilization-cycle counts are never read by this service** — the brief's
explicit instruction. No factor above touches cycle-count data.

## Categories

| Range | Category |
|---|---|
| 90-100 | Reliable |
| 75-89 | Monitor |
| 50-74 | Elevated Concern |
| 25-49 | Repair / Manufacturer Review |
| 0-24 | Remove From Service Candidate |

`reliability_category(score)` (in `app/models/vulcan_reliability.py`) is the
single source of truth for this banding, reused by both the score service
and the orchestrator's disposition logic.
