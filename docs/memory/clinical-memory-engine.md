# Clinical Memory Engine (Project Insight, v2.4)

`app/services/clinical_memory_service.py`, `app/routes/clinical_memory.py`.

## Mission

Every inspection should be able to answer: have I inspected this instrument
before? Has this anatomy failed previously? Is this finding recurring? The
Clinical Memory Engine is the composition layer that assembles a single
instrument's complete recorded history into one context object — it does not
re-run AI scoring or invent a new re-identification scheme.

## `GET /api/clinical-memory?instrument_identity=<barcode:...|udi:...>`

Roles: admin, spd_manager, supervisor, operator, viewer. 404 when there's no
recorded history for that identity (untracked instruments — no barcode/UDI —
never have one; see below).

Composes, without duplicating any of their logic:

| Field | Source |
|---|---|
| `condition_history` | `instrument_condition_service.instrument_condition_history` (v1.6) — inspection/finding/repair/supervisor-comment history + condition trend |
| `recurring_issues` | `recurrence_detection_service.detect_recurring_issues` (Section 3) |
| `predictive_risk` | `predictive_risk_engine.estimate_predictive_risk` (Section 4) |
| `health_forecast` | `instrument_health_forecast_service.forecast_instrument_health` (Section 5) |
| `similar_instruments` | `similar_instrument_search_service.find_similar_instruments` (Section 2) |
| `knowledge_articles` | `knowledge_repository_service.list_articles(instrument=...)` (v1.8), top 5 |
| `timeline` | `build_memory_timeline` (Section 7) |
| `memory_recommendation` | `build_memory_recommendation` (Section 9) |

Every field carries `human_review_required: true` (also set at the top
level) — Clinical Memory never issues a self-executing recommendation.

## Instrument identity

Reuses the exact `barcode:<value>` / `udi:<value>` key already established by
`app/services/pre_sterilization_command_center_service._instrument_identity`
and consumed by `instrument_condition_service`/`prioritization_engine`. An
instrument with neither a barcode nor a UDI captured gets an
`untracked:<type>:<inspection_id>` key — a per-inspection singleton, not a
re-identified physical instrument — and is correctly excluded from Clinical
Memory (there's no real history to recall) rather than faked.

## AI Context Expansion (Section 6)

`app/routes/inspections.py`'s `create_inspection()` computes
`get_clinical_memory(db, tenant_id, memory_identity)` from the submitted
`instrument_barcode`/`instrument_udi` **before** the new inspection is
persisted, and attaches it to the analysis response as
`analysis["clinical_memory"]` when history exists. Because it's computed
before the current row is inserted, it always reflects prior history only —
purely additive context for the technician/reviewer, never a second scoring
pass and never altering the risk score, findings, or recommendation the
scoring engine already produced.

## What this deliberately does not do

No new instrument-identity scheme, no re-derivation of condition trend or
inspection history (both already exist and are already tested), and no
fabricated confidence — see `docs/memory/predictive-intelligence.md` and
`docs/memory/instrument-health-forecast.md` for how those specifically avoid
overclaiming precision.
