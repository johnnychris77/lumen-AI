# Enterprise Alert Center & Recommendation Engine

LumenAI v3.0 · Project Sentinel

## No unified alert feed existed before this

`SPDAlert` (digital-twin workflow alerts), `AlertEvent` (external Slack/
Teams/email dispatch), `WorkflowNotification` (in-app SPD queue), and
`CaseRiskAlert` (OR Connect) are each siloed to their own subsystem.
`SentinelAlert` aggregates Sentinel's own findings — risk signals,
watchlist entries, and critical/escalation Digital Twin flags — into one
explainable feed, following the same severity/acknowledge/resolve idiom
those four tables already use, so it's additive and consistent rather than
a fifth incompatible shape.

## Explainable by construction

Every alert has a `title`, a plain-language `narrative` (the underlying
signal's own detail text — e.g. *"3 blood findings in Kerrison jaw
serrations over the past 90 days."*), and a concrete `recommendation`
(e.g. *"Review manual cleaning competency for this anatomy zone."*) —
never a bare severity number. Generation is idempotent per (source,
related signal/watchlist/flag id): re-running `generate_enterprise_alerts`
never creates a duplicate for an already-alerted, still-unresolved finding.

## Recommendation Engine

`sentinel_recommendation_service.generate_recommendations` derives one of
eight typed recommendations, each grounded in a specific already-detected
signal — never a bare model suggestion:

| Recommendation | Trigger |
|---|---|
| `create_baseline` | A high-risk instrument/family watchlist entry with no approved `BaselineLibraryEntry` |
| `update_anatomy_profile` | An active anatomy watchlist entry |
| `review_competency` | A `repeated_low_confidence`/`repeated_missing_coverage` risk signal |
| `update_sop` | A `repeated_blood`/`repeated_bone`/`repeated_damage` signal at high/critical severity |
| `review_ifu` | A recurring finding in a high-retention zone (`instrument_zones.is_high_retention`) |
| `expand_knowledge_graph` | Knowledge Graph confidence backed by fewer than 30 supervisor reviews |
| `schedule_education` | An open Quality Guardian `CompetencyOpportunity` |
| `review_digital_twin` | A `critical`/`escalation` Digital Twin flag |

`reasoning` always names the specific trigger data — never a generic
"this looks risky." A supervisor can `action` (mark handled) or `dismiss`
each recommendation; nothing is auto-executed.

## Endpoints

- `POST /api/sentinel/alerts/generate`, `GET /api/sentinel/alerts`,
  `POST /api/sentinel/alerts/{id}/acknowledge|resolve`
- `POST /api/sentinel/recommendations/generate`, `GET /api/sentinel/recommendations`,
  `POST /api/sentinel/recommendations/{id}/action|dismiss`

## Supervisor Intelligence

`GET /api/sentinel/supervisor-intelligence` is a curated view over the
above — not a new detection engine — filtered to what a supervisor
specifically needs: high-risk instruments awaiting review, recurring
technician education needs (Quality Guardian competency opportunities),
coverage gaps (`anatomy_risk_dashboard`), unusual contamination trends and
repeated repair referrals (risk signals), and potential IFU conflicts
(`review_ifu` recommendations).
