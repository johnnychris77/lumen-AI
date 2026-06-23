# Go-Live Runbook

**Version:** Phase 12  
**Date:** 2026-06-23  
**Audience:** LumenAI CS Lead, DevOps, Account Executive  
**Purpose:** Operational runbook for go-live day and the first four weeks of production

---

## Pre-Go-Live (Day –3 to Day –1)

### T–3 Days: Final Configuration Check

- [ ] `ENABLE_DEV_AUTH=false` confirmed in production environment
- [ ] `SECRET_KEY` is 64+ chars, randomly generated, not in source control
- [ ] Database connection uses `sslmode=require`
- [ ] SMTP tested: send test notification from approval workflow
- [ ] Image storage bucket accessible: upload a test image via `/baseline-image-upload`
- [ ] All tenant users can log in: verify each role (admin, spd_manager, spd_technician, vendor)
- [ ] `GET /api/health` returns `200 {"status": "ok"}`

### T–2 Days: Readiness Gates

- [ ] Go-Live Readiness Score ≥ 75 at `/go-live-center`
- [ ] Baseline Readiness Score ≥ 60 (≥1 approved baseline per top scope type)
- [ ] ≥5 practice inspections completed by at least 2 technicians
- [ ] SPD Manager has approved ≥1 finding in the review queue
- [ ] All role-based training sessions complete (`/training-compliance` shows ≥80% overall)

### T–1 Day: Go/No-Go Call

Participants: CS Lead, SPD Director, LumenAI Account Executive, LumenAI DevOps

| Gate | Threshold | Status |
|------|-----------|--------|
| Go-Live Readiness Score | ≥ 75 | ___ |
| Baseline coverage | ≥ 50% | ___ |
| Training completion | ≥ 80% | ___ |
| API health | Green | ___ |
| SPD Manager confirmed available | Yes | ___ |
| Escalation path confirmed | Yes | ___ |

If all gates pass → **GO**. If any gate fails → negotiate 48-hour extension or accept risk and proceed with documented exception.

---

## Go-Live Day

### Hour 0 — Launch (9:00 AM local time)

1. CS Lead joins stand-up with SPD Manager and lead technician (15 min)
2. Open `/go-live-center` — confirm score is still ≥ 75 after overnight
3. Send "Go-Live" notification to LumenAI Slack `#deployments` channel
4. CS Lead on call / available via phone for first 4 hours

### Hour 1–4 — First Live Inspections

- [ ] First live inspection submitted by technician
- [ ] CS Lead confirms record appears in `/intake-history`
- [ ] First finding reviewed by SPD Manager in `/findings`
- [ ] No critical auth or API errors in logs

### Hour 4 — Check-In

CS Lead reviews:
- Inspection count (target: ≥3 submitted)
- Any failed submissions (review error logs)
- Any technician questions / friction points

### End of Day 1 — Summary

Send written summary to SPD Director:
- Inspections submitted today: N
- Any issues encountered and resolution
- Tomorrow's focus (volume, baseline submissions)

---

## Week 1 (Days 2–7)

### Daily Checks (CS Lead)

| Check | Target | Action if Miss |
|-------|--------|----------------|
| Inspections submitted | ≥3/day | Call SPD Manager |
| Review queue turnaround | ≤8 hours | Remind SPD Manager |
| API health | Green | Page DevOps |
| Any login failures | 0 | Check auth logs |

### Day 3: Vendor Follow-Up

- Confirm vendor has submitted ≥1 baseline per scope type
- If not, schedule 30-min vendor call to troubleshoot image upload

### Day 5: Week 1 Check-In Call (30 min)

Participants: CS Lead, SPD Manager  
Agenda:
1. Volume review — inspections, findings, CAPAs
2. Blocker resolution
3. Baseline coverage update
4. Training gaps (check `/training-compliance`)
5. Preview: Week 2 targets

### Day 7: First Week Report

Pull from `/value-realization`:
- Time saved (hrs)
- Inspections completed
- Critical findings (if any)
- Baseline coverage %
Send to SPD Director.

---

## Week 2 (Days 8–14)

### Targets

| Metric | Target |
|--------|--------|
| Total inspections | ≥20 |
| Baseline coverage | ≥60% |
| Critical findings reviewed | 100% (within 24h) |
| Customer Health Score | ≥50 (Yellow) |

### Day 10: Mid-Point Check

CS Lead reviews Customer Health Score at `/customer-success`. If Red (< 40):
1. Emergency call with SPD Director within 24 hours
2. Root cause analysis: technical, workflow, or leadership barrier
3. Escalate to Account Executive

### Day 14: Validation Review

- [ ] ≥20 inspections completed
- [ ] ≥1 CAPA opened (if any critical finding detected)
- [ ] Baseline coverage on track for ≥75% by Day 30
- [ ] Data completeness ≥70% (inspections with barcode + instrument type + image)

---

## Week 4 (Days 22–30)

### Targets

| Metric | Target |
|--------|--------|
| Total inspections | ≥50 |
| Baseline coverage | ≥75% |
| Customer Health Score | ≥70 (Green) |
| CAPAs closed | ≥1 |
| Value realization report | Generated and shared |

### Day 21: Go-Live Milestone Review

CS Lead + SPD Director (30 min):
1. Review Go-Live Readiness Score (now a retrospective measure)
2. Show Executive Command Center with live data
3. Review first Value Realization report
4. Confirm 60-day ROI review date

### Day 30: 30-Day Health Report

Pull from `/customer-success` and `/value-realization`:
- Customer Health Score band (Green/Yellow/Red)
- Total inspections and findings
- Estimated time saved
- Critical findings caught
- Baseline coverage achieved
- Open questions and next steps

Deliver to SPD Director + CS file.

---

## Executive Review (Day 90)

### QBR Preparation (Day 80–89)

1. Pull fresh data from `/roi-center` — export CSV
2. Pull Value Realization report from `/value-realization`
3. Review Customer Health Score trend (last 90 days)
4. Identify expansion opportunities (additional departments, facilities)
5. Prepare QBR deck using ROI Center data

### QBR Agenda (60 min)

| Section | Time | Content |
|---------|------|---------|
| Platform Performance | 10 min | Health score trend, inspection volume, baseline coverage |
| ROI Summary | 15 min | Time saved, critical findings, cost avoidance, SSI risk |
| Compliance Readiness | 10 min | Audit trail, CAPA closure, evidence bundle |
| Roadmap | 10 min | Upcoming features, Global Registry, network intelligence |
| Renewal / Expansion | 15 min | Tier comparison, renewal terms, expansion opportunities |

### Renewal Readiness Gates

- [ ] Customer Health Score ≥ 70 (Green) or improving trend
- [ ] Total inspections ≥ 200 (strong) or ≥ 50 (adequate for early renewal)
- [ ] At least 1 CAPA closed
- [ ] Executive champion confirmed
- [ ] No unresolved critical incidents in last 30 days

---

## Incident Escalation

| Severity | Definition | Response SLA | Contacts |
|----------|-----------|--------------|---------|
| P1 — Production Down | No users can log in or submit inspections | 2 hours | DevOps pager + Account Exec |
| P2 — Partial Outage | Some users affected, core workflow degraded | 4 hours | Engineering |
| P3 — Feature Issue | Non-critical workflow issue | Next business day | CS Lead → Engineering |
| P4 — Question / Enhancement | Usage question or feature request | 3 business days | CS Lead |

---

## Communication Templates

### Go-Live Day Announcement (to CS team Slack)

> 🚀 [Facility Name] is LIVE. First inspection expected by 10:00 AM. CS Lead: [Name]. Escalation: [Phone].

### Day 30 Summary (to SPD Director)

> LumenAI 30-Day Summary — [Facility Name]  
> Inspections: [N] | Critical Findings: [N] | Time Saved: [N] hrs | Value: $[N]  
> Health Score: [Green/Yellow/Red] | Baseline Coverage: [N]%  
> Next: 60-day ROI review on [Date].

---

*LumenAI Engineering & Customer Success — Internal Use Only*  
*LumenAI makes no claim of FDA clearance or regulatory approval.*  
*All AI findings require qualified human review before clinical action.*
