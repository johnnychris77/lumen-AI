# CAPA Integration (v1.5)

## What it does
`app/services/capa_suggestion_service.py` scans the last 90 days of
`InspectionFinding` and `Inspection` rows for three recurring patterns and
suggests a Corrective and Preventive Action for each:

1. **Repeated contamination finding in the same anatomy zone** (≥3
   occurrences) → recommend reviewing manual cleaning competency for that
   zone.
2. **Repeated condition finding (rust/corrosion/pitting/crack/insulation
   damage/missing component) on the same instrument family** (≥3
   occurrences) → recommend evaluating storage and maintenance practices.
3. **Repeated low-confidence or low-coverage inspections by the same
   technician** (≥3 occurrences) → recommend an image-capture refresher.

## Suggestions, never auto-created CAPAs
Consistent with the platform-wide rule that AI output never bypasses human
review, `generate_capa_suggestions()` only returns suggestions — it never
writes to the CAPA store. A supervisor reviews a suggestion and explicitly
creates the CAPA via `POST /api/quality/capa-suggestions/create`, which
calls the existing `app/services/capa_service.create_capa()` (the same CAPA
store already used elsewhere in the platform — no parallel CAPA system).

## API
- `GET /api/quality/capa-suggestions` — current suggestions (leadership only).
- `POST /api/quality/capa-suggestions/create` — materialize a chosen
  suggestion into a real CAPA.
