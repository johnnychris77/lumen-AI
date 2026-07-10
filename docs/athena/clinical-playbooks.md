# Project Athena — Clinical Playbooks

LumenAI OS v4.8, Section 5.

## No parallel playbook model

Project Forge's `WorkflowDefinition`/`WorkflowRule` (v4.1) already model a
versioned, approved, nested-decision-tree workflow, with `is_template`
and a `TEMPLATE_CATEGORIES` list that already included three of the six
named scenarios (`loaner_instrument`, `vendor_tray`, `robotic_instrument`).
Athena adds the three missing scenario keys —
`blood_detection_investigation`, `corrosion_investigation`,
`joint_commission_preparation` — to that same list, and one additive
column (`linked_standards_json`) to `WorkflowDefinition`, rather than a
second playbook table.

`CustomerSuccessPlaybook` (a different, unrelated SaaS-renewal-risk
domain — checked during research) is not a real collision.

## What a playbook already gets, for free

Because a Clinical Playbook *is* a `WorkflowDefinition`, every playbook
automatically has:

* **Decision trees** — the existing `nodes_json`/`edges_json`.
* **Approval history** — the existing `author`/`reviewer`/`approved_by`/
  `approved_at` + `WorkflowApprovalChain`/`WorkflowApprovalInstance` for
  multi-step (Technician → Supervisor → Manager → Director) approval.
* **Versioning** — the existing `supersedes_id`/`version`/`status` chain
  and `forge_workflow_service.version_history`/`revise_workflow`.

## What Athena adds

* **Standards** — `linked_standards_json` (new column), managed via
  `attach_standard`.
* **Evidence, photos, videos** — attach via `KnowledgeMediaAttachment`
  with `source_type="workflow_definition"` — no new column needed on
  `WorkflowDefinition` itself.

```
POST /api/athena/playbooks
GET  /api/athena/playbooks?category=blood_detection_investigation
GET  /api/athena/playbooks/{id}
POST /api/athena/playbooks/{id}/standards
GET  /api/athena/playbooks/{id}/history
```
