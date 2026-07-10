# Project Catalyst — Supervisor Copilot

LumenAI OS v4.4 — Section 5

## Persona mapping

Roles `supervisor`, `spd_manager`, and `admin` map to the Supervisor
persona (`catalyst_persona_service.persona_for_role`).

## Coaching

`GET /api/catalyst/persona/supervisor-coaching?technician=<name>` calls
`competency_service.competency_summary(db, technician)` directly — the
same real event-counted competency data (`record_finding_reviewed`,
`record_supervisor_correction`, `record_education_completed`) already
used by the Coaching Dashboard elsewhere in this codebase. Catalyst adds
no second competency-tracking mechanism.

## Finding explanations & rule interpretation

`POST /api/catalyst/persona/supervisor-finding-explanation`
`{instrument_type, finding_type, manufacturer?}` calls
`knowledge_graph_service.reasoning_chain` — the traceable
Instrument → Anatomy Zone → Cleaning Knowledge → Recommendation chain
the Knowledge Graph Explorer already exposes. This is the same
mechanism `catalyst_skills_service.research_skill` wraps for the
general-purpose Research Skill; the persona endpoint is a thin,
role-scoped front door onto it.

## Workflow guidance

Workflow interpretation reuses `catalyst_skills_service.workflow_skill`,
which itself wraps `forge_workflow_service.get_workflow`/`list_workflows`/
`version_history` — Forge's own rule engine remains the single source of
truth for what a workflow does; Catalyst never re-derives rule logic.

## Case comparison & knowledge search

Both reuse `catalyst_skills_service.inspection_skill` and
`knowledge_search_skill` respectively — the same functions the NL Query
Engine dispatches to for a technician or executive question. A
supervisor asking "compare this to last month's Kerrison findings" and
an executive asking "show me recurring corrosion" run through the same
underlying skill, scoped differently only by the parameters passed in.
