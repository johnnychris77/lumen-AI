# Baseline Decision Policy

A governed, org-configurable policy replacing the hardcoded universal
thresholds that previously lived alongside scoring logic (e.g.
`baseline_comparison_scoring_service._CRITICAL_THRESHOLDS`, the
`baseline_match_score < 0.70` checks in `recommended_action()`). Those
scoring-engine thresholds are unchanged and continue to drive the existing
KPI/severity/disposition pipeline; the Baseline Decision Policy is a
separate, additive layer the Lumen Decision Engine consults for its own
observation-vs-policy recommendation.

## Model

`app/models/lumen_decision_engine.py::BaselineDecisionPolicy`. Configurable
scopes (`POLICY_SCOPES`): `health_system`, `market`, `facility`,
`department`, `instrument_family`, `manufacturer`, `model`, `anatomy_zone`,
`finding_category`, `lumenai_default`.

Fields: `policy_id`, `organization_id`, `scope`/`scope_value`,
`policy_name`, `version`, `baseline_source_requirement`, `pass_threshold`,
`technician_review_threshold`, `supervisor_attention_threshold`,
`supervisor_approval_threshold`, `contamination_override_rule`,
`structural_damage_rule`, `unknown_finding_rule`, `author`,
`approving_role`, `approved_by`, `rationale`, `supporting_reference`,
`effective_date`, `review_date`, `status`, `previous_version_id`.

## LumenAI's recommended starting policy

Not a universal clinical standard — a default used only when no
organization-specific policy resolves at any scope
(`baseline_decision_policy_service.LUMENAI_DEFAULT_POLICY`):

- 90–100% baseline similarity → eligible to continue (no probable
  contamination/damage/other actionable finding).
- 70–89% → focused technician reinspect or additional image capture.
- Below 70% → supervisor attention or approved corrective action.
- Probable contamination at any similarity → reclean and reinspect
  (Section 4 — unconditional, not policy-configurable).
- Probable structural damage / progressive corrosion / unknown foreign
  material / repeated condition decline → supervisor or repair evaluation.

## Governance lifecycle (Section 8)

Status vocabulary: `draft` → `pending_approval` → `approved` → `active`
(supersedes the prior active policy in the same scope) → `superseded` /
`archived` / `rejected`. Only `active` (which required passing through
`approved`) policies influence a live recommendation
(`policy_resolution_service.resolve_active_policy` filters on
`status == "active"` only).

Technicians (`operator`) and viewers may never create, submit, approve,
activate, archive, or reject a policy —
`baseline_decision_policy_service.ROLES_MAY_PUBLISH_POLICY = {"admin",
"spd_manager"}`, enforced both in the service (defense in depth) and at
the route layer (`app/routes/lumen_decision_engine.py`, `require_roles`).

## Routes

`POST/GET /api/decision-policies`, `POST /api/decision-policies/{id}/submit`
`/approve` `/activate` `/archive` `/reject`.
