# Project Genesis AI — Global Standards Observatory

LumenAI Network v5.3, Section 9.

## Zero new tables — composes four real change feeds

| Brief item | Source |
|---|---|
| Manufacturer guidance | `ManufacturerKnowledgeUpdate` (this sprint, Section 4), filtered to `published` |
| Internal policies | Apollo's `QualityPolicy` version chain (`apollo_policy_service.py`, v4.7) |
| Industry standards | P24's `StandardsPublication`, filtered to `published` |
| Scientific publications | Horizon's `ClinicalEvidenceReference` with `evidence_type == "peer_reviewed"` |

## Internal policies never leak across organizations

Unlike the other three feeds (which are legitimately cross-organization
by design), "internal policies" are returned **only for the requesting
organization's own `tenant_id`** — an org's internal policy changes are
never surfaced to any other organization, regardless of observatory
opt-in status. This is the one place in this module where the mission's
"organizations retain ownership of their data" principle overrides the
otherwise-global observatory scope.

## "Notify participating organizations" — an honest implementation

There is no email/push notification system anywhere in this codebase.
Rather than fabricate one, this is implemented as a queryable
recent-changes feed scoped to `AdvisoryConsortiumMember.observatory_opt_in`
participants (Olympus's existing flag, reused rather than a second
opt-in column) — callers poll it; nothing is pushed.

```
GET /api/genesis-ai/standards-observatory/summary
```
