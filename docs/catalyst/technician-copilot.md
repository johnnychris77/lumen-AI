# Project Catalyst — Technician Copilot

LumenAI OS v4.4 — Section 6

## Persona mapping

Roles `technician` and `operator` map to the Technician persona
(`catalyst_persona_service.persona_for_role`'s default fallback — any
role not explicitly listed as Executive or Supervisor lands here,
matching the principle of least privilege for an unrecognized role).

## Contextual assistance, never disposition authority

`GET /api/catalyst/persona/technician-help?instrument_type=<name>`
(`catalyst_persona_service.technician_contextual_help`) returns:

* recent inspection context for that instrument type
  (`catalyst_skills_service.inspection_skill`), and
* related knowledge articles/graph entries
  (`catalyst_skills_service.knowledge_search_skill`).

This is deliberately read-only and advisory. The Technician Copilot:

* never sets `qa_review_status`, never overrides `qa_reviewer` fields,
  and never calls anything that writes to `Inspection`'s supervisor
  review columns;
* every response carries the note
  `"Informational only — supervisor review authority is unchanged."`

Supervisor review authority remains exactly where it already lived
before this sprint (`SupervisorReview`, `Inspection.qa_review_status`) —
Catalyst adds a technician-facing lens onto real data, not a new
approval path that could be used to bypass supervisor sign-off.

## Shared engine, role-scoped view

Like the Supervisor Copilot, the Technician Copilot is not a separate
implementation — `/api/catalyst/chat` answers a technician's plain
question ("what did we find on the last three Kerrisons?") through the
exact same `catalyst_query_engine.answer_query` every persona uses.
`persona` on the conversation is metadata for the frontend's framing and
future role-scoped filtering, not a second query engine.
