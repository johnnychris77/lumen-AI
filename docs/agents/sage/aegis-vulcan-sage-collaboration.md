# Project Sage — Integration With Aegis and Vulcan

LumenAI AI Specialist, Sections 13 & 14.

## Separation of responsibility

Aegis remains responsible for process analysis. Vulcan remains responsible
for instrument reliability. Sage remains responsible only for education and
competency support. `sage_aegis_vulcan_integration_service.py` reads each
agent's real conclusion and returns a Sage-specific recommendation — it
never mutates or overwrites the source.

## Aegis -> Sage (Section 13)

`sage_recommendation_from_aegis` calls
`vulcan_aegis_integration_service.compute_process_variation_signal` directly
(Sage has no separate Aegis client — there is one real, minimal Aegis
signal in this codebase, built for Vulcan, and Sage reads the same
function). If a process-concentration pattern is detected, Sage recommends
focused brushing/inspection education for the affected workflow. The
underlying Aegis signal is returned verbatim as `source_aegis_signal` --
never edited.

## Vulcan -> Sage (Section 14)

`sage_recommendation_from_vulcan` takes a real, already-persisted
`VulcanReliabilityAssessment` row and recommends differentiation education
when the failure category is one this codebase's own severity scale
recognizes as visually confusable with a benign cosmetic finding (e.g.
corrosion/rust vs. cosmetic discoloration, pitting vs. cosmetic wear -- see
`_AMBIGUOUS_CONDITION_PAIRS`). The Vulcan assessment's ID and category are
referenced (`source_vulcan_assessment_id`), never copied into or blended
with Sage's own recommendation text.

## Separately traceable, by construction

Every returned dict keeps the source agent's evidence under its own key
(`source_aegis_signal` / `source_vulcan_assessment_id`) alongside Sage's own
`recommendation` string — there is no shared/blended conclusion field, so
Aegis, Vulcan, and Sage evidence can always be inspected independently.

## API

```
GET /api/sage/aegis-recommendation?instrument_identity=...&zone=...
GET /api/sage/vulcan-recommendation/{assessment_id}
```
