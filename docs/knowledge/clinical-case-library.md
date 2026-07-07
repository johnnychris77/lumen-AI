# Clinical Case Library & Supervisor Knowledge Capture

## Clinical Case Library (Deliverable 2)

`GET /api/knowledge/cases`, `GET /api/knowledge/cases/{id}`

Significant inspections are saved automatically as a `ClinicalCase` —
never fabricated after the fact, always tied to a real inspection:

- At inspection creation, if the inspection has any real actionable
  finding (matching the spec's own examples — blood, bone, corrosion,
  missing insulation, a crack are all ordinary findings, not just
  remove-from-service-tier ones), or the risk stratification tier is
  `Critical`, or the readiness engine's own `is_critical_finding`
  classification is true.
- At every supervisor disposition action (v1.6), which both is itself a
  significance trigger and updates the case with the real
  `supervisor_corrections`, `final_disposition`, and `outcome`.

One case per inspection — later events update the same row rather than
creating a duplicate, so a case's history stays a single coherent record
of what happened.

Each case contains: `ai_findings` (a JSON snapshot of the real
`InspectionFinding` rows at save time), `supervisor_corrections`,
`final_disposition`, `clinical_reasoning`, `educational_notes`, and
`outcome`. Images are referenced via `inspection_id`, not duplicated.

## Supervisor Knowledge Capture (Deliverable 3)

`POST /api/inspections/{id}/teaching-point` (admin/spd_manager only)

After a disposition override, a supervisor can capture what future
technicians should know: `explanation`, `teaching_point` (headline),
`common_mistake`, `prevention_tip`, `references`. This creates a
`KnowledgeArticle` with `category=teaching_point`, tagged to the
inspection's real instrument type and primary finding, and updates that
inspection's `ClinicalCase.educational_notes`.

Teaching points are **auto-approved** rather than routed through the
general `pending_review` queue — a supervisor is already exercising real
clinical authority at the point of a disposition decision (the same
authority already granted to disposition overrides in v1.6), so requiring
a second reviewer would be redundant. They still carry a `reviewer` (the
authoring supervisor) and remain fully subject to later archival via
Knowledge Governance if the guidance becomes outdated.

## Similar Case Finder (Deliverable 5)

`GET /api/inspections/{id}/similar-cases`

When the AI detects a finding on a new inspection, surfaces prior real
cases with the same finding type on the same **instrument family**
(`instrument_anatomy.resolve_family()` — not exact instrument type, since a
Kerrison from one manufacturer and another share the anatomy that drives
the finding, not the brand). Each result includes the previous
recommendation, supervisor outcome, and educational notes — nothing here
is a fabricated "similar" case, only ones that are real matches.
