# Project Olympus — Network Architecture

LumenAI OS v5.1, Section 1: Network Identity.

## No new participant table

P24's `AdvisoryConsortiumMember` (`app/models/p24_standards.py`) is already
a real, tenant-scoped participant roster: `organization_type`,
`membership_tier` (Participation Level), `membership_status`,
`governance_roles`/`voting_rights` (Governance Profile). Olympus extends
its `organization_type` vocabulary with `partner`, `consultant`, `educator`
(in `p24_standards.py`'s `VALID_TYPES` and
`beacon_collaboration_hub_service.py`'s `PARTICIPANT_TYPES`) to cover the
brief's full participant list:

| Brief category | `organization_type` value |
|---|---|
| Organizations | `hospital` |
| Partners | `partner` |
| Research Institutions | `academic` / `research_partner` |
| Manufacturers | `manufacturer` |
| Repair Providers | `repair_vendor` |
| Consultants | `consultant` |
| Educators | `educator` |
| Regulators | `regulator` |

`standards_body` remains available as a ninth type from P24's original set.

## Contribution History is composed, never duplicated

`olympus_network_identity_service.contribution_history` counts real rows
from Horizon's `KnowledgeContribution` and Beacon's
`AdvisoryBoardActionItem` — there is no second contribution log.

## Observatory opt-in

`AdvisoryConsortiumMember` gained one nullable-turned-required boolean,
`observatory_opt_in`, the single flag `docs/olympus/` Section 5 queries
filter on.

```
GET /api/olympus/participants?organization_type=hospital&active_only=true
GET /api/olympus/participants/{tenant_id}
GET /api/olympus/directory-summary
```

Every participant response composes the latest `NetworkTrustSnapshot`
(`docs/olympus/trust-framework.md`) and the contribution-history rollup —
never a stale cached number.

## Global Research Observatory (Section 5)

Entirely a read-only composition, no new table: emerging contamination
trends and instrument performance trends reuse Horizon's
`EmergingTrendAlert`/`InstrumentRiskRegistryEntry`; quality improvement
initiatives reuse Apollo's `ContinuousImprovementInitiative`, scoped to
`observatory_opt_in` tenants only; inspection science updates and
published research reuse P24's `StandardsPublication`.

```
GET /api/olympus/observatory/contamination-trends
GET /api/olympus/observatory/instrument-trends
GET /api/olympus/observatory/quality-initiatives
GET /api/olympus/observatory/research
GET /api/olympus/observatory/summary
```
