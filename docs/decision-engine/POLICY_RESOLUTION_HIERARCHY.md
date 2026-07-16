# Policy Resolution Hierarchy

Implemented in `app/services/policy_resolution_service.py::resolve_active_policy()`.

## Resolution order (most specific first)

1. `model` (instrument-model-specific)
2. `instrument_family`
3. `anatomy_zone`
4. `department`
5. `facility`
6. `health_system`
7. LumenAI recommended default (`lumenai_default`)

Only `status == "active"` policies are ever read — draft and
pending_approval policies never influence a live recommendation (Section
9). The final applicable policy (`policy_id`, `version`, `scope`) is
documented on every recommendation returned by the Lumen Decision Engine
and persisted on the `LumenDecisionRecord` row, never left implicit.

## Cross-tenant isolation

Every resolution query filters `organization_id == tenant_id`. A policy
authored under one organization can never influence another tenant's
recommendation — see
`test_lumen_decision_engine.py::TestCrossTenantIsolation`.

## Mandatory rules cannot be weakened

Manufacturer instructions, validated safety requirements, and mandatory
organizational controls are never weakened by a less-restrictive local
threshold:

- The Section 4 contamination-safety override and the structural-damage
  escalation rule are enforced unconditionally in
  `app/services/lumen_decision_engine.py` — they do not read from, and
  cannot be disabled by, `BaselineDecisionPolicy` threshold fields. See
  `test_lumen_decision_engine.py::TestContaminationSafetyRule::test_less_restrictive_policy_cannot_cancel_contamination`.
- Where a genuine scope conflict exists (e.g. a facility policy vs. a
  mandatory health-system policy), the more specific scope always wins per
  the resolution order above — organizations wanting a mandatory floor
  should publish it at the least-specific scope they control and rely on
  more-specific overrides only tightening, never loosening, it as a matter
  of governance process (Section 8's approval role is the control point,
  not the resolution algorithm itself).
