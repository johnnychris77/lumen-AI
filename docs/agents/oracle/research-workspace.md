# Research Workspace, Registry & Executive Innovation Dashboard

## Research Workspace

`oracle_workspace_service.workspace_summary` is a pure read composition over
every Oracle table for one tenant: hypothesis counts by stage, trend
observations by direction, digital twin insights by source service,
knowledge suggestions by status, and a combined recent-activity feed (stage
transitions, trend observations, digital twin insights, model observations)
sorted newest-first. Nothing here is separately persisted -- the frontend
`/oracle` "Workspace" tab is a direct view of `GET /api/oracle/workspace`.

## Research Registry

`oracle_registry_service.search_registry` filters
`oracle_hypothesis_service.list_hypotheses` (category / stage / confidence /
outcome) and, if a `query` string is supplied, substring-matches it against
`title`, `observation_summary`, and `hypothesis_statement`.
`registry_summary` rolls every hypothesis up by category, stage, confidence,
and outcome -- the same funnel shape the Executive Innovation Dashboard
uses, at hypothesis granularity rather than portfolio granularity.

## Executive Innovation Dashboard

`oracle_innovation_dashboard_service.innovation_dashboard` (route: `GET
/api/oracle/dashboard`, leadership-role-gated) reports:

- `pipeline_funnel` -- hypothesis count per validation stage (+ `REJECTED`).
- `promoted_to_production_count` -- hypotheses with
  `outcome == "promoted_to_knowledge"`.
- `avg_time_to_validation_days` -- for promoted hypotheses only, the days
  between their first stage transition and their `PRODUCTION_KNOWLEDGE`
  transition (`None` if no hypothesis has been promoted yet -- never
  fabricated from an empty set).
- `category_distribution` -- hypothesis count per discovery category.
- `top_research_owners` -- the ten owners with the most hypotheses.

Every field here is a live rollup; `human_review_required: true` is always
included in the response.
