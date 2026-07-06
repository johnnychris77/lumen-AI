# 30-Day Go-Live Plan

Builds on `docs/customer/customer-onboarding-playbook.md` with a
week-by-week execution plan for the first 30 days after contract signature.

## Week 1 — Provisioning & Access

- Tenant provisioned (`docs/deployment/multi-tenant-deployment-guide.md`)
- Executive Sponsor and SPD Champion identified (see
  `docs/customer/executive-sponsor-guide.md`,
  `docs/customer/spd-champion-guide.md`)
- Initial users created with correct RBAC roles
  (`docs/security/lumenai-rbac-matrix-v1.md`)
- Kickoff call: review the 30/60/90-day plan, confirm success criteria

## Week 2 — Baseline & Configuration

- Manufacturer/vendor baselines loaded for the site's top instrument
  families (`docs/architecture/...` baseline governance; see
  `app/models/baseline_library.py`)
- Facility/department/tray structure configured
- SPD Champion and technicians trained on capture workflow (see
  `docs/customer/training-matrix.md`)

## Week 3 — Supervised Pilot Inspections

- SPD technicians begin running real inspections
- Supervisors begin reviewing AI recommendations
  (`POST /inspections/{id}/supervisor-review`) — every review also
  creates a Phase 18 ground-truth label and a Phase 23 Decision Ledger
  entry automatically
- Daily check-ins with the SPD Champion to unblock workflow friction

## Week 4 — Go-Live Readiness Review

- Review Phase 18 pilot validation metrics
  (`/api/pilot-validation/dashboard`) and Phase 20 command center
  readiness (`/api/pre-sterilization-command-center/dashboard`)
- Confirm the go/no-go criteria in
  `docs/validation/pilot-go-no-go-criteria.md` are met for the pilot
  cohort collected so far
- Executive Sponsor review meeting — go-live decision
- Transition to `docs/customer/60-day-optimization-plan.md`

## Exit criteria for Day 30

- [ ] At least one full week of unsupervised, routine daily use
- [ ] Supervisor agreement rate tracked and trending toward the
  go/no-go threshold (`docs/validation/pilot-go-no-go-criteria.md`)
- [ ] No unresolved critical safety queue items
  (`/api/pre-sterilization-command-center/high-risk-findings`)
- [ ] Customer Success Checklist (`docs/customer/customer-success-checklist.md`)
  Week 1–4 items complete

## Escalation path

Any blocker that risks the Day-30 go-live date should be raised to the
Executive Sponsor and the LumenAI implementation lead within 24 hours —
see the escalation contacts in `docs/customer/executive-sponsor-guide.md`.
