# LumenAI Workflow Orchestration Framework

> **Audience:** SPD operations leaders, quality managers, and IT teams. Defines the workflow definition, execution, and step-completion model powering LumenAI's autonomous operations platform.

---

## 1. Workflow Lifecycle

```
Definition → Steps → Execution triggered
                           ↓
                    approval_required?
                    Yes → awaiting_approval → human approves → in_progress
                    No  → in_progress (immediately)
                           ↓
                    Steps assigned to role queues
                           ↓
                    Assignees complete steps → audit logged
                           ↓
                    All steps done → completed
                    Overdue / SLA breach → escalated
```

---

## 2. Workflow Definition

A workflow definition is a reusable template parameterized per execution:

| Field | Description |
|-------|-------------|
| `workflow_type` | `capa` / `inspection` / `escalation` / `notification` |
| `priority` | `low` / `normal` / `high` / `critical` |
| `sla_hours` | Target completion window; used to compute `sla_due_at` at execution time |
| `auto_assign` | Whether system may suggest an assignee from the role queue |
| `approval_required` | If `true`, execution pauses at `awaiting_approval` until a human acts |

---

## 3. Workflow Steps

Steps define the ordered set of actions within a workflow:

| Field | Description |
|-------|-------------|
| `step_order` | Integer ordering (1, 2, 3…) |
| `step_type` | `action` / `approval` / `notification` / `gate` |
| `assignee_role` | `technician` / `manager` / `executive` / `vendor` |
| `timeout_hours` | Hours before step is considered overdue |
| `on_timeout` | `escalate` / `skip` / `block` |

---

## 4. Execution States

| Status | Meaning |
|--------|---------|
| `pending` | Created, not yet started |
| `awaiting_approval` | Paused at approval gate; human decision required |
| `in_progress` | Approved and active; steps being worked |
| `escalated` | Manually escalated; priority raised to critical |
| `completed` | All steps complete |
| `cancelled` | Rejected at approval gate or cancelled by human |

---

## 5. Step Completion Protocol

1. Technician / assignee claims the queue item for the step
2. Work is performed and documented outside LumenAI (physical inspection, repair, etc.)
3. Assignee completes the step via `POST /executions/{id}/steps/{step_id}/complete`
4. Completion is audit-logged with `actor_email`, `outcome`, and `notes`
5. When the last required step completes, execution status transitions to `completed`

---

## 6. Escalation Protocol

Any manager or admin can escalate an active execution:

1. `POST /executions/{id}/escalate` with `escalated_by` and `reason`
2. Status transitions to `escalated`; priority escalates to `critical`
3. Command center escalation dashboard surfaces the execution immediately
4. A human decision is required to resolve: complete the execution or cancel

---

## 7. SLA Enforcement

- `sla_due_at` is computed at execution creation time: `now + sla_hours`
- The live dashboard counts overdue items (`due_at < now` and status not terminal)
- SLA breach does not automatically escalate — human action required
- Overdue count is surfaced on the command center risk dashboard

---

## 8. Governance Requirements

| Requirement | Implementation |
|-------------|----------------|
| Human approval gate | `approval_required=true` blocks execution until human acts |
| Audit trail | Every state transition is `compliance_flag=True` audit logged |
| No autonomous escalation | Escalation only by human actor (`manager` or `admin` role) |
| Immutable step records | Step executions are append-only; outcomes cannot be edited |
| Role-gated access | Step completion requires matching `assignee_role` or `admin` |

---

*All workflow outputs are operational support tools requiring human review and decision. LumenAI does not make autonomous clinical decisions.*
