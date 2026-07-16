# LumenAI — Human Oversight Model

Objective 10 review. This document maps the brief's clinical approval hierarchy (Technician/Supervisor/Manager/Director/Quality/Manufacturer) onto what is actually implemented, and confirms no irreversible recommendation can bypass human authority.

## The real RBAC vs. the clinical hierarchy — stated plainly

The real, enforced role set is exactly `admin`, `spd_manager`, `operator`, `viewer` (plus `vendor_user` for vendor-facing workflows elsewhere) — confirmed in `app/tenant_authz.py`, which has zero technician/supervisor/manager/director/quality/manufacturer role-name logic of its own.

Council's model file (`app/models/council_leadership.py`) layers a **documented conceptual 5-tier scale** on top of this real RBAC — quoted exactly:

```python
APPROVER_TECHNICIAN = "technician"
APPROVER_SUPERVISOR = "supervisor"
APPROVER_SPD_MANAGER = "spd_manager"
APPROVER_DIRECTOR = "director"
APPROVER_CLINICAL_QUALITY_GOVERNANCE = "clinical_quality_governance"
APPROVAL_TIER_BY_ROLE_NAME = {
    APPROVER_TECHNICIAN: 0, APPROVER_SUPERVISOR: 1, APPROVER_SPD_MANAGER: 2,
    APPROVER_DIRECTOR: 3, APPROVER_CLINICAL_QUALITY_GOVERNANCE: 4,
}
ROLE_AUTHORITY_TIER = {"viewer": 0, "operator": 0, "spd_manager": 2, "admin": 4}
```

| Clinical title (brief) | Conceptual tier | Real enforced RBAC role |
|---|---|---|
| Technician | 0 | `viewer` / `operator` |
| Supervisor | 1 | **No distinct enforced role** — tier 1 exists only as a numeric threshold constant (e.g. `TIER_APPROVE_STANDARD=1`); nothing in `ROLE_AUTHORITY_TIER` resolves to exactly 1 |
| Manager | 2 | `spd_manager` |
| Director | 3 | **No distinct enforced role** — `admin` jumps straight to tier 4, covering tier 3 as part of its ceiling |
| Quality / Governance | 4 | `admin` |
| Manufacturer | — | **Not an approval role at all** |

**This should be disclosed plainly to clinical/leadership audiences reading this document**, since they will reasonably expect the named titles to be literal, independently-enforced roles: only two of the five conceptual tiers (Technician, Manager) map to a genuinely distinct RBAC role. Supervisor and Director are real *authority thresholds* in the code (used to gate specific actions) but are satisfied by `spd_manager` and `admin` respectively rather than by their own role — `spd_manager` covers "supervisor-and-manager" scope, `admin` covers "director-and-quality-governance" scope as the authority ceiling. This is a deliberate, documented architectural choice (quoted directly in `governed_action.py`: *"the underlying RBAC is still only four real roles"*), not an oversight — but it is a real gap between the clinical narrative and the enforced role model that this document exists to surface, not obscure.

**"Manufacturer" is never an approval role.** It appears only as a disposition/action-type label: `"manufacturer_review"` (a `DISPOSITION_ACTIONS` value a supervisor can select) and `Manufacturer Evaluation` (a disposition-engine recommendation). No manufacturer identity ever logs in and approves anything in this system.

## Workflow stage coverage — receiving → cleaning → inspection → assembly → packaging → pre-sterilization review → supervisor review → release

**This 8-stage sequence does not exist as one unified, tracked state machine anywhere in the codebase.** Three separate, narrower models cover parts of it:

1. **`app/models/workflow.py`'s `WORKFLOW_STATES`** (the real inspection-task state machine): `Waiting → Assigned → Image Capture → AI Analysis → Supervisor Review → {Reclean | Repair} → Completed / Cancelled`. Only **"Supervisor Review"** is a literal 1:1 match to the brief; "AI Analysis" roughly corresponds to "inspection."
2. **The OR case timeline** (`or_connect_service.py::build_case_timeline`, extended by `orbit_timeline_service.py`): `Case Scheduled → Vendor Confirmed → Tray Received → Inspection Complete → Supervisor Approved → Packaging → Ready for OR`. "Tray Received" ≈ receiving, "Inspection Complete" ≈ inspection, "Packaging" is explicit, "Supervisor Approved" ≈ supervisor review. Notably, this service's own docstring refuses to fabricate a per-case sterilization-cycle timestamp it doesn't actually observe, surfacing the facility-level figure as read-only context instead — an example of the same overclaim-avoidance discipline found throughout this codebase.
3. **Pre-sterilization review exists as a computed readiness report, not a tracked stage** — `pre_sterilization_command_center_service.py` computes a `READY_FOR_PACKAGING` classification but never stores a "pre-sterilization review" state transition on any record; its own docstring: *"reports pre-sterilization/packaging readiness, never manages the actual process."*

**"Cleaning" and "assembly" are not modeled as distinct, timestamped stages anywhere** — they exist only as RCA root-cause classification labels (`rca_engine_service.py`'s `_PROCESS_STAGE_BY_CATEGORY`: `"Manual Cleaning"`, `"Assembly / Tray Packing"`) used to categorize *findings after the fact*, never as a state a record transitions through in real time. **"Release" has no dedicated stage either** — the closest equivalents are `Completed` (inspection workflow) and `Ready for OR` (case timeline).

**Honest summary**: 4 of the 8 named stages (receiving, inspection, packaging, supervisor review) have real, code-tracked equivalents, split across two different models that are not unified into one sequence. Cleaning, assembly, and pre-sterilization review are descriptive labels or computed reports, not tracked stages. Release has no dedicated named stage in either model. **LumenAI supports, rather than replaces, the workflow at the four stages where it has real tracking — it should not be described as covering the full 8-stage cycle as a single unified pipeline today.**

## No irreversible recommendation may bypass human authority — verified

`app/services/steward_action_service.py::transition_status` (governing `GovernedAction`, the platform's execution-tracking layer for any approved decision) hard-blocks every gated transition:

```python
_GATED_TRANSITIONS = {STATUS_APPROVED, STATUS_CLOSED, STATUS_CANCELLED}
if new_status in _GATED_TRANSITIONS:
    actor_tier = ROLE_AUTHORITY_TIER.get(changed_by_role, 0)
    required_tier = _required_tier(action, new_status)
    if actor_tier < required_tier:
        raise ValueError(f"Role '{changed_by_role}' (tier {actor_tier}) is not authorized...")
    if actor_tier < TIER_CROSS_FACILITY_AUTHORITY and action.facility_id and actor_facility_id != action.facility_id:
        raise ValueError("This approver's configured scope does not include this action's facility...")
```

This is a hard `raise ValueError` (HTTP 422 at the route layer), not a soft warning, and `ROLE_AUTHORITY_TIER` contains only human tenant roles — there is no code path for a system or agent identity to satisfy this check. `TERMINAL_STATUSES = {CLOSED, CANCELLED}` additionally prevents any further mutation once an action is closed; reopening requires creating a new, separately-authorized action, never reversing the closed record in place. `disposition_override.py` independently requires a non-empty reason for every action except plain approval, enforced in the service layer (a real `ReasonRequiredError`, not just documentation). No automated or agent-triggered path to an irreversible state was found anywhere in this review.
