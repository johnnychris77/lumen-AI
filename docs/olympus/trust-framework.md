# Project Olympus — Trust Framework

LumenAI OS v5.1, Section 2.

## Genuinely new — nothing scores an organization today

Athena's Knowledge Trust Score (`athena_trust_service.py`, v4.8) scores a
single `KnowledgeArticle`, never an organization. `NetworkTrustSnapshot`
is the first construct anywhere in this codebase that scores a network
*participant*.

## Six components, all computed from real, pre-existing signals

| Component | Source |
|---|---|
| Participation Status | `AdvisoryConsortiumMember.membership_status` |
| Knowledge Quality | Average of Athena's per-article trust scores for the tenant's `KnowledgeArticle` rows |
| Validation History | This organization's own HIX exchange package governance outcomes (approved/published vs. rejected) |
| Evidence Contributions | Count of Horizon's `ClinicalEvidenceReference` rows attributed to the tenant |
| Peer Recognition | Approved cross-organization `KnowledgeContribution` count — genuinely new, no endorsement/rating construct existed before this table |
| Governance Compliance | `AdvisoryConsortiumMember.voting_rights` + `governance_roles` count |

**Trust is earned, not assigned**: a participant with no data yet in a
component scores 0 on it, never a default/optimistic score.

## Snapshot pattern, not a live-only score

Every computation is persisted as a `NetworkTrustSnapshot` — the same
historical-snapshot pattern already used by `PlatformMaturitySnapshot`
(Phoenix) and `QualityTwinSnapshot` (Apollo) — so trust progression over
time is a real queryable history, not a single mutable number.

```
POST /api/olympus/trust/{tenant_id}/compute
GET  /api/olympus/trust/{tenant_id}/history
GET  /api/olympus/trust/leaderboard
```
