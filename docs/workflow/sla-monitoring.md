# SLA Monitoring & Escalation

`GET /api/workflow/sla-monitoring`, `GET /api/workflow/escalations`
(admin/spd_manager only)

## Inspection Workflow State Machine (Deliverable 4)

Every inspection moves through an append-only, audited log of transitions
(`WorkflowStateEvent`) rather than a single mutable "current state" column
— the full history is always reconstructable via
`GET /api/inspections/{id}/workflow-state`.

States: `Waiting → Assigned → Image Capture → AI Analysis → Supervisor
Review → Reclean / Repair → Completed`, with `Cancelled` reachable at any
point as an explicit, terminal action
(`POST /api/inspections/{id}/workflow/cancel`, reason required).

Transitions are appended at the real moment they happen:

- **Image Capture** + **AI Analysis** — recorded together when an image is
  submitted (`POST /api/inspections`), since both happen synchronously in
  that one request. This mirrors the same honesty principle already used
  by `readiness_timeline_service.py`: no fabricated gap between two events
  that really happened in the same call.
- **Supervisor Review** — entered automatically when the disposition
  engine recommends `Supervisor Review Required`.
- **Reclean / Repair / Completed** — driven by a supervisor's disposition
  action (`POST /api/inspections/{id}/disposition-action`, v1.6).
- **Assigned** — only when assignment happens while still `Waiting`
  (see `operations-board.md`).

## SLA targets

| Stage | Target |
|---|---|
| Supervisor Review | 8 hours |
| Reclean turnaround | 4 hours |
| Repair referral | 24 hours |
| Overall turnaround (creation → Completed) | 24 hours |

Averages are computed only from real, completed stage transitions — a
stage an inspection hasn't reached yet contributes no data point.
`sla_breaches` lists any inspection still *open* in a stage past its
target, using the real elapsed time so far (never estimated).

## Escalation rules (Deliverable 7)

`escalation_engine.evaluate_escalation()` fires when any of these real
signals are true — never a generic "flagged" verdict:

- Critical contamination/risk finding (risk tier `Critical`).
- Repeated failure history (prior repair/removal + a current critical
  finding).
- Low AI confidence (< 60%).
- No approved baseline available.
- 2+ prior non-approve supervisor overrides on this inspection.
- High-priority OR instrument (emergency/trauma procedure priority).

Each escalated inspection lists exactly which rule(s) fired.
