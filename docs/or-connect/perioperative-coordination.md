# Perioperative Coordination — Overview

Codename: Project Symphony · LumenAI OR Connect v2.8

## Mission

Coordinate the complete perioperative instrument workflow — from surgical
scheduling through instrument readiness — using explainable operational
intelligence. LumenAI OR Connect does not replace Epic, ReadySet, supply
chain, or clinical engineering. It coordinates quality intelligence across
them, remaining advisory and interoperable.

## Architecture

```
backend/app/models/or_connect.py            — SurgicalCase, VendorTray, RepairRequest,
                                               CaseRiskAlert, CaseNotification,
                                               CaseReadinessScoreRecord
backend/app/models/inspection.py            — additive Inspection.case_id column
backend/app/services/or_connect_service.py  — case coordination, readiness score,
                                               timeline, risk detection, notifications,
                                               dashboard, clinical engineering,
                                               executive dashboard
backend/app/services/or_connect_vendor_service.py — vendor-scoped portal reads/actions
backend/app/routes/or_connect.py            — /api/or-connect/*  (staff-facing)
backend/app/routes/or_connect_vendor_portal.py — /api/or-connect/vendor-portal/*
frontend/src/components/CaseIntelligenceDashboard.tsx
frontend/src/pages/CaseIntelligencePage.tsx — route: /case-intelligence
```

## Case Intelligence Dashboard (`/case-intelligence`)

Four tabs:

1. **Today's Cases** — `GET /api/or-connect/dashboard`: total cases, high-risk
   cases, vendor tray status tally, inspection completion %, outstanding
   blockers, projected delays (readiness score below 70 within 24h of the
   scheduled start).
2. **Case Detail** — look up a case by ID: identity fields, derived status
   (Inspection Status / Clinical Readiness / Repair Status / Supervisor
   Approval), the Case Readiness Score with its factor breakdown, the
   Intelligent Readiness Timeline, and open operational risks with a
   "Notify Stakeholders" action.
3. **Clinical Engineering** — open repair requests, average turnaround,
   replacement availability (Section 8).
4. **Executive Dashboard** — case readiness trend, delay causes, vendor
   performance, inspection turnaround, repair impact, quality alerts, and
   operational bottlenecks by service line (Section 9), gated to
   `admin`/`spd_manager`.

## What's deliberately out of scope

- No real integration with Epic/ReadySet/supply-chain systems — case
  creation today is manual/API-driven, matching the mission statement that
  LumenAI coordinates quality intelligence rather than replacing scheduling
  systems.
- No external channel (SMS/push) for stakeholder notifications — the
  in-app, role-scoped queue mirrors the existing v1.7 Workflow Notification
  pattern; wiring it to the existing Slack/Teams/email `AlertEvent`
  dispatcher is a natural fast-follow, not built in this pass.
- No self-service external vendor identity/registration for the
  Collaboration Portal — see `vendor-collaboration.md`.

## Governance

Every OR Connect response carries `human_review_required: true` and:

> LumenAI OR Connect coordinates quality intelligence across existing
> scheduling, vendor, and clinical-engineering systems — it does not
> replace them and does not make autonomous clinical or operational
> decisions. Case readiness, risk, and notification outputs are decision
> support only; human review and approval are required before any
> operational action.
