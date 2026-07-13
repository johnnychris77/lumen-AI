# Steward Action Orchestration Agent

Steward converts approved decisions -- from Council, CAPA, Sentinel-X, Maestro,
Aegis, Vulcan, Sage, Veritas, Phoenix, audit findings, policy changes, and
leadership directives -- into governed implementation plans, and tracks their
execution, verification, measured outcomes, and closure.

**Steward does not approve clinical or operational decisions.** It executes
and monitors only actions authorized by the appropriate human role, and no
action may begin without an approved source decision.

## Architecture position

```
Specialist Evidence -> Council Review -> Human Decision -> Steward Implementation Plan
  -> Owner Assignment -> Controlled Execution -> Verification -> Outcome Measurement
  -> Benefits Realization -> Institutional Learning
```

## Responsibilities

- Receive approved decisions and create implementation plans (`steward_plan_generator_service`).
- Identify owners, stakeholders, milestones, and dependencies (`steward_action_service`, `steward_change_management_service`).
- Schedule reviews, track execution, and identify blocked work (`steward_action_service.transition_status`).
- Verify completion evidence (`steward_verification_service`).
- Measure outcomes and recommend sustain/revise/escalate/close (`steward_benefits_realization_service`, `steward_closure_service`).
- Preserve complete audit history (`GovernedActionAuditEvent`, append-only).

## Module map

| Concern | Service |
|---|---|
| Core CRUD, lifecycle, RBAC gating | `steward_action_service.py` |
| Implementation Plan Generator | `steward_plan_generator_service.py` |
| Dependency analysis + change management | `steward_change_management_service.py` |
| Phased rollout tracking | `steward_rollout_service.py` |
| Completion evidence + Veritas gate | `steward_verification_service.py` |
| Benefits realization | `steward_benefits_realization_service.py` |
| Unintended consequence monitoring | `steward_unintended_consequence_service.py` |
| Sentinel-X residual risk | `steward_residual_risk_service.py` |
| Aegis/Vulcan/Sage integration | `steward_specialist_integration_service.py` |
| Escalation rules | `steward_escalation_service.py` |
| Notifications | `steward_notification_service.py` |
| Workspace summary | `steward_workspace_service.py` |
| Leadership action boards | `steward_action_board_service.py` |
| Decision-to-outcome timeline | `steward_timeline_service.py` |
| Closure governance | `steward_closure_service.py` |
| Reports | `steward_reports_service.py` |
| Council integration | `steward_council_integration_service.py` |

Frontend: `/steward`. API prefix: `/api/steward`.
