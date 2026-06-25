# LumenAI Enterprise Command Center

> **Audience:** SPD directors, CNOs, quality directors, and operations leaders. Defines the operational risk, workload, backlog, and escalation dashboards available in LumenAI's Enterprise Command Center.

---

## 1. Purpose

Give operations leaders a single, real-time view of the health of all quality and compliance workflows — surfacing what's at risk, who is overloaded, what's overdue, and what has been escalated — without requiring manual aggregation across teams.

---

## 2. Dashboard Views

### 2.1 Risk Dashboard

Aggregates signals that indicate operational risk:

| Metric | Definition |
|--------|------------|
| `open_high_priority_items` | Open queue items with priority = `high` or `critical` |
| `overdue_items` | Items past `due_at` and not yet complete or cancelled |
| `risk_score` | Composite 0.0–1.0 score (higher = more risk); candidate indicator requiring human interpretation |
| `active_escalations` | Queue items or executions currently in escalated state |

### 2.2 Workload Dashboard

Queue depth by role to identify overloaded teams:

| Metric | Definition |
|--------|------------|
| `total_open_queue_items` | All open items across queues |
| `technician_queue_depth` | Open items in technician queue |
| `manager_queue_depth` | Open items in manager queue |
| `executive_queue_depth` | Open items in executive queue |
| `vendor_queue_depth` | Open items in vendor queue |
| `active_executions` | In-progress or awaiting-approval workflow executions |

### 2.3 Backlog Dashboard

Tracks items that have aged past SLA:

| Metric | Definition |
|--------|------------|
| `backlog_items_gt_sla` | Items overdue relative to workflow SLA |
| `avg_completion_hours` | Rolling average completion time across completed items |

### 2.4 Escalation Dashboard

Escalation trend visibility:

| Metric | Definition |
|--------|------------|
| `active_escalations` | Currently escalated items |
| `escalations_last_7d` | Escalation count over the trailing 7 days |

---

## 3. Live Dashboard vs. Snapshots

| Mode | Endpoint | Use |
|------|----------|-----|
| Live | `GET /command-center/dashboard` | Real-time queue + execution state aggregation |
| Snapshot | `GET /command-center/snapshots` | Historical point-in-time records for trend analysis |
| Publish | `POST /command-center/snapshots` | Store a computed snapshot (e.g., end-of-shift, weekly) |

Snapshots are published by `admin` or `executive` role users. Live dashboard is always derived from current queue and execution state.

---

## 4. Governance

| Principle | Enforcement |
|-----------|-------------|
| Candidate signals | Dashboard figures are operational support data, not autonomous directives |
| Human review | All risk scores and escalation counts require human interpretation |
| Tenant isolation | Dashboard data is strictly scoped to the requesting tenant |
| Audit trail | Snapshot creation is compliance-logged |
| No causation | Risk score is a composite indicator — not a clinical finding |

---

## 5. Operational Safety

The command center is a **visibility tool**, not a control system. It does not:
- Automatically escalate items based on thresholds
- Notify external parties without human action
- Make staffing or resource decisions
- Generate regulatory submissions

All actions triggered from command center data require explicit human initiation.

---

*LumenAI does not claim FDA clearance or regulatory approval. Command center dashboards are operational support indicators requiring human review and decision.*
