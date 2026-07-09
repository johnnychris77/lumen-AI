# Operational Risk Engine

Codename: Project Symphony · LumenAI OR Connect v2.8

## Detected risk types

`GET /api/or-connect/cases/{case_id}/risks` (backed by
`or_connect_service.detect_operational_risks`) scans a case's real linked
state and emits a `CaseRiskAlert` for each risk found, idempotently — a
risk type already open for a case is never duplicated:

| Risk type | Trigger |
|---|---|
| `vendor_tray_not_received` | A vendor tray is still `requested`/`shipped` and the case is within 24h of its scheduled start |
| `inspection_overdue` | A linked inspection has been pending analysis for over 8h |
| `baseline_missing` | A linked inspection has no approved baseline |
| `repair_incomplete` | A linked repair request is still `pending`/`in_progress` |
| `critical_finding_unresolved` | A linked inspection has a critical finding with no recorded supervisor review |
| `supervisor_review_pending` | A linked inspection requires supervisor review and none has been recorded |

## Severity

Time-sensitive risks (vendor tray, overdue inspection, pending supervisor
review) scale severity by how close the case is to its scheduled start:
`critical` at 6h or less (or already past due), `high` within 24h, `medium`
otherwise. `critical_finding_unresolved` is always `critical` — a critical
finding doesn't become less urgent because the case is far out.

## Readiness Timeline

`GET /api/or-connect/cases/{case_id}/timeline`
(`or_connect_service.build_case_timeline`) visualizes the same staged
pipeline as the sprint's Intelligent Readiness Timeline:

```
Case Scheduled → Vendor Confirmed → Tray Received → Inspection Complete →
Supervisor Approved → Packaging → Ready for OR
```

Following the honesty principle already established by
`readiness_timeline_service.py`: a step only gets a timestamp when a real,
independently-timed record exists (e.g. a tray's actual `received_at`) —
never a fabricated, evenly-spaced guess. Incomplete steps are surfaced as
`blockers`, flagged `delayed: true` once the case is past its scheduled
start.

## Stakeholder Notifications

`POST /api/or-connect/cases/{case_id}/notifications/generate` runs risk
detection, then fans each open risk out to the relevant stakeholder
role(s) as a `CaseNotification` (mirroring `WorkflowNotification`'s
recipient-role fan-out, extended with OR-specific roles):

| Risk type | Notified roles |
|---|---|
| `vendor_tray_not_received` | Vendor Representative, Supply Chain |
| `inspection_overdue` | SPD |
| `baseline_missing` | SPD |
| `repair_incomplete` | Clinical Engineering |
| `critical_finding_unresolved` | Surgeon, SPD |
| `supervisor_review_pending` | SPD |

Notifications are in-app and role-scoped (`GET /api/or-connect/notifications
?recipient_role=...`), the same idiom as the existing v1.7 Workflow
Notification queue — not a new external-channel dispatcher.
