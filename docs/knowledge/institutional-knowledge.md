# Institutional Knowledge Repository

`GET/POST /api/knowledge/articles` · frontend route `/knowledge-center`

## What it is

A user-authored repository of institutional SPD knowledge — supervisor
best practices, local inspection standards, organization-approved
workflows, clinical pearls, lessons learned, FAQs, competency guidance, and
manufacturer clarifications. Deliberately distinct from two existing
stores it might be confused with:

- `education_library.py` (v1.4) — a fixed, code-generated reference for
  the 12 finding categories. Static, not authored or governed.
- `InstrumentKnowledge` (Phase 15) — manufacturer/model technical data
  (failure modes, maintenance intervals). Not staff-authored guidance.

`KnowledgeArticle` is what SPD staff actually write themselves, with real
governance (see `knowledge-governance.md`).

## Search facets

Every article stores the facets it's searchable by — populated only when
actually supplied at authoring time, never inferred:

| Facet | Field |
|---|---|
| Instrument | `applicable_instruments` (list) |
| Manufacturer | `applicable_manufacturers` (list) |
| Instrument family | derived by resolving each `applicable_instruments` entry via `instrument_anatomy.resolve_family()` at search time |
| Anatomy zone | `anatomy_zone` |
| Finding | `applicable_findings` (list) |
| Procedure | `procedure` (free text, substring match) |
| Specialty | `specialty` |

`GET /api/knowledge/articles?instrument=&manufacturer=&anatomy_zone=&finding=&procedure=&specialty=&category=&approval_status=`
combines any of these filters.

## Categories

`best_practice`, `local_standard`, `approved_workflow`, `clinical_pearl`,
`lesson_learned`, `faq`, `competency_guidance`, `manufacturer_clarification`,
`teaching_point` (the last one is written via the Supervisor Knowledge
Capture flow — see `clinical-case-library.md`).

## Honesty notes

- New articles start `pending_review` — nothing self-publishes as
  authoritative institutional knowledge without a reviewer, except
  supervisor teaching points captured at the point of a real disposition
  decision (see `knowledge-governance.md` for why that's different).
- Editing an approved article's title/body bumps its version and reopens
  review — staff relying on "approved" guidance never see it silently
  change underneath them.
