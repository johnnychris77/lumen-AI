# Project Council — Human Decision Authority

Section 8 of the sprint brief.

## Mapping the brief's five-tier scale onto LumenAI's actual RBAC

LumenAI's real tenant RBAC has four roles: `admin`, `spd_manager`,
`operator`, `viewer`. The brief calls for five authority tiers
(technician, supervisor, SPD manager, director, clinical/quality
governance). `council_leadership.py` layers the five-tier scale on top of
the real four roles via `ROLE_AUTHORITY_TIER`:

| Tenant role | Authority tier | Brief's equivalent |
|---|---|---|
| `viewer` / `operator` | 0 | Technician -- may view recommendations, cannot finalize. |
| `spd_manager` | 2 | Supervisor + SPD Manager scope. |
| `admin` | 4 | Director + Clinical/Quality Governance scope (ceiling). |

`APPROVAL_TIER_BY_ROLE_NAME` maps the five conceptual roles to tiers
0-4. A `CouncilCase`'s `required_approval_tier` is set at `convene()`
time to the highest tier any assessing specialist flagged as necessary
(`human_role_required` on each `CouncilSpecialistAssessment`).

## Enforcement

`council_human_decision_service.finalize_decision` calls `can_approve
(approver_role, case.required_approval_tier)` and raises
`PermissionError` (surfaced as HTTP 403) if the deciding user's role tier
is insufficient. A technician-equivalent role (`viewer`/`operator`) can
always read a case's recommendation but can never finalize its decision.
Every finalized decision records `approver`, `approver_role`, `decision`,
`rationale`, `conditions`, and `decided_at` -- a complete, auditable
record.
