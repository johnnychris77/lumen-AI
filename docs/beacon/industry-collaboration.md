# Project Beacon — Industry Collaboration Hub

LumenAI v3.5 — Section 1

## This is the 9th cross-tenant/collaboration sprint — reuse first

Before writing any new table, this sprint's research pass confirmed what
already exists across the eight prior collaboration sprints in this
codebase (P15, P20, P23 "GSIN", P24, OR Connect, Atlas, Nexus, Horizon).
The Industry Collaboration Hub adds **no new participant/membership
model**. It reuses P24's `AdvisoryConsortiumMember`
(`app/models/p24_standards.py`) directly as the roster for all seven
participant types the sprint names:

| Sprint's participant type | `organization_type` value |
|---|---|
| Hospitals | `hospital` |
| Manufacturers | `manufacturer` |
| Repair Vendors | `repair_vendor` *(added this sprint)* |
| Academic Institutions | `academic` |
| Standards Organizations | `standards_body` |
| Regulatory Teams | `regulator` |
| Research Partners | `research_partner` *(added this sprint)* |

Enrollment already existed at `POST /api/standards/consortium/enroll`
(`app/routes/p24_standards.py::enroll_consortium`); this sprint only
extended its hardcoded `VALID_TYPES` set with the two participant types
P24's original five didn't cover.

## Governance-ruled by construction

`beacon_collaboration_hub_service.collaboration_hub_summary` only ever
lists members with `membership_status == "active"` — a `pending`,
`suspended`, or `resigned` organization is never shown as an active
collaborator, matching every other governance gate in this codebase.

## Endpoints

```
GET  /api/beacon/collaboration/hub                       — full participant directory, grouped by type
GET  /api/beacon/collaboration/participants/{organization_type}
GET  /api/beacon/collaboration/my-status                 — the calling tenant's own membership record
```

## Frontend

`/collaboration` (`CollaborationHubPage.tsx` →
`CollaborationHubDashboard.tsx`) composes this section alongside
Sections 4–8 and 10 in one tabbed dashboard, exactly as
`docs/horizon/research-platform.md`'s Research Portal composed several
of Horizon's own sections into one page.
