# Project Beacon — Collaboration Governance

LumenAI v3.5 — Section 9

## Composes what already exists, mirroring Horizon's governance center

`beacon_governance_service.py` follows the exact composition pattern
`horizon_governance_service.py` established one sprint earlier:

| Requirement | Source |
|---|---|
| Participation agreements | `beacon_collaboration_hub_service.participant_status` (P24's `AdvisoryConsortiumMember`) |
| Knowledge approval | `horizon_contribution_service`'s pending queue (manufacturer feedback contributions) |
| Evidence review | `horizon_evidence_service.list_evidence` |
| Contribution history | `horizon_contribution_service.list_contributions`, scoped to the requesting tenant's own submissions |
| Access control | Governance gates already enforced at the point of use (e.g. `beacon_standards_service._is_approved_publisher` requires an active `standards_body`/`regulator`/`academic` consortium member before `publish_guidance` succeeds) |
| Version management | `beacon_standards_service.version_history` (walks `StandardsPublication.supersedes_id`) |
| Audit trails | This platform's existing `AuditLog` table (`app/audit.py::log_audit_event`), filtered to `beacon.*` action types |

No second audit store, no second participation table, no second
contribution-approval queue. `governance_overview` is a per-tenant view
(participation status, own contribution history, own pending approvals,
own audit trail); `pending_knowledge_approvals` is the governance-board-
wide view (every organization's pending contributions, de-identified per
`horizon_contribution_service.list_contributions`'s own guarantee).

## Endpoints

```
GET /api/beacon/governance/overview
GET /api/beacon/governance/pending-approvals
```

## Frontend

`/collaboration-governance`
(`CollaborationGovernancePage.tsx` → `CollaborationGovernanceDashboard.tsx`)
mirrors `docs/horizon/knowledge-governance.md`'s Governance Center layout
(Participation / Pending Approvals / Audit Trail tabs).
