# Project Council — Leadership Team Registry

Sections 2 & 15 of the sprint brief.

## The six default teams (`DEFAULT_TEAM_DEFINITIONS`)

| Team | Required specialists | Purpose |
|---|---|---|
| Clinical Quality Council | Sentinel-X, Veritas, Apollo, Athena, Vulcan | High-risk findings, evidence quality, clinical significance, quality implications, institutional guidance. |
| Operations Council | Maestro, Aegis, Pulse, Vulcan, Sentinel-X | Workload prioritization, workflow risk, repair impact, staffing pressure, immediate operational response. |
| Education Council | Sage, Aegis, Athena, Apollo, Veritas | Knowledge gaps, competency needs, approved educational content, effectiveness measurement. |
| Reliability Council | Vulcan, Veritas, Sentinel-X, Aegis, Maestro | Recurring instrument failure, repair recurrence, process exposure, clinical risk, disposition options. |
| Executive Council | Maestro, Sentinel-X, Pulse, Phoenix, Apollo, Aegis | Enterprise priorities, executive risks, resource options, quality priorities, strategic recommendations. |
| Research and Innovation Council | Phoenix, Athena, Veritas, Sentinel-X, Research Agent | New hypotheses, model improvements, evidence needs, pilots, research proposals, innovation opportunities. |

`council_team_registry_service.ensure_default_teams(db, tenant_id)`
provisions these six teams for a tenant the first time Council is used
there -- idempotent, so it's safe to call on every request.

## Case-type routing (`CASE_TYPE_DEFAULT_TEAM`)

Each of the 12 Council Case types (Section 3) has a default team it
routes to out of the box (e.g. `recurring_instrument_failure` ->
Reliability Council, `education_need` -> Education Council,
`enterprise_trend` -> Executive Council). Organizations may reconfigure
which specialists sit on a team, but the case-type routing itself is a
platform default, not per-tenant configurable in this release.

## Versioned, audited configuration

`update_team_config` never mutates a team's current configuration row --
it marks the current row `is_current=False` and inserts a new row with
`version` incremented by one and `approval_status="pending_review"`. The
full configuration history is always queryable via
`team_config_history`, mirroring Veritas's append-only baseline
governance action pattern.

## Mandatory safety review can't be configured away

`SAFETY_VETO_SPECIALISTS` (Sentinel-X, Veritas) can never be removed from
a team's required specialist list if they were already required --
`update_team_config` raises `ValueError` if an organization's proposed
change would drop one of them. Optional specialists and everything else
(decision scope, escalation rules, quorum requirement, evidence
requirements, review frequency) are freely configurable.
