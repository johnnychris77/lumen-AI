# First Customer Deployment Guide

**Version:** Phase 12  
**Date:** 2026-06-23  
**Audience:** LumenAI Customer Success, Implementation Leads  
**Purpose:** End-to-end workflow for successfully deploying LumenAI at the first enterprise customer

---

## Overview

This guide covers the complete first-customer deployment lifecycle — from signed contract to 30-day value realization. The goal is a hospital that can onboard users, train staff, upload baselines, perform inspections, review findings, and demonstrate ROI within the first 30 days.

---

## Phase 1 — Onboarding Workflow (Days –10 to 0)

### Week –2: Pre-Kick-Off

1. **Contract signed** — CS Lead assigned; kickoff scheduled within 5 business days
2. **Stakeholder map** — identify SPD Director, SPD Manager (platform owner), IT contact, vendor contacts
3. **Facility profile** — document facility name, department, active scope types in fleet, estimated user count by role
4. **Infrastructure check** — confirm network access to `api.lumenai.com`, browser version (Chrome 110+), imaging hardware

### Week –1: Tenant Configuration

1. **Provision tenant** — LumenAI DevOps creates tenant record (`POST /api/admin/tenants`)
2. **Generate admin key** — `secrets.token_urlsafe(40)`, SHA-256 stored, raw key delivered via 1Password Send
3. **Create user accounts** — admin, spd_manager (1–2), spd_technician (all), vendor (1 per vendor)
4. **Confirm environment** — `ENABLE_DEV_AUTH=false`, `SECRET_KEY` set, `SMTP_HOST` configured
5. **Kick-off call** — walk stakeholders through `/go-live-center` live

### Kick-Off Day Agenda (90 min)

| Time | Topic | Owner |
|------|-------|-------|
| 0–10 | Welcome and introductions | CS Lead |
| 10–25 | Platform overview — inspection workflow demo | CS Lead |
| 25–40 | IT setup review — logins, network, hardware | CS Lead + IT |
| 40–60 | Vendor baseline submission walkthrough | CS Lead |
| 60–75 | Training schedule — dates, roles, outcomes | CS Lead |
| 75–90 | Questions and next steps | CS Lead |

---

## Phase 2 — Training Workflow (Days 1–7)

### Session 1: SPD Technician Training (2 hrs)

**Audience:** All SPD technicians  
**Outcome:** Each technician can independently submit a new inspection with image

Modules:
1. Platform login and role overview (15 min)
2. New inspection form — required fields, barcode scan, image capture (30 min)
3. Borescope image quality guidelines (20 min)
4. Submitting and tracking inspections (15 min)
5. Practice: submit 3 test inspections per technician (40 min)

### Session 2: SPD Manager Training (2 hrs)

**Audience:** SPD Manager(s), quality lead  
**Outcome:** Manager can review findings, open CAPAs, track baselines

Modules:
1. Review queue walkthrough — findings, risk scores, confidence (30 min)
2. CAPA creation and management (20 min)
3. Baseline library and approval workflow (20 min)
4. Customer Health Dashboard — health score interpretation (15 min)
5. Executive Command Center overview (15 min)
6. Audit evidence bundle generation (20 min)

### Session 3: Vendor / Manufacturer Training (1 hr)

**Audience:** Vendor field reps, manufacturer quality contacts  
**Outcome:** Vendor can submit baseline images via portal

Modules:
1. Vendor baseline portal login (10 min)
2. Image capture guidelines — lighting, angle, focus (20 min)
3. Submitting baseline images by scope type (20 min)
4. Q&A and escalation path (10 min)

### Session 4: Executive Training (45 min)

**Audience:** SPD Director, VP/C-suite sponsor  
**Outcome:** Executive understands KPIs, ROI, and renewal value

Modules:
1. Executive Command Center — 16 KPIs (15 min)
2. Surgical Readiness Dashboard (10 min)
3. ROI Center — how value is calculated (10 min)
4. Value Realization report generation (10 min)

---

## Phase 3 — Baseline Workflow (Days 1–14)

### Step 1: Scope Type Inventory

Work with the SPD Manager to list all active scope types in the reprocessing fleet. Minimum: capture top 5 by volume.

### Step 2: Vendor Outreach

CS Lead facilitates a vendor call:
1. Walk vendor through `/vendor-baseline-portal`
2. Share image capture guidelines (`docs/pilot/pilot-image-ingestion-guide.md`)
3. Set deadline: first baseline submission within 5 business days

### Step 3: Baseline Review and Approval

SPD Manager reviews at `/baseline-review`:
- Accept: confident image, correct scope type, sufficient detail
- Reject: blurry, incorrect scope, missing channel view

**Target:** ≥1 approved baseline per active scope type before go-live (Day 21)  
**Minimum:** ≥1 approved baseline for the highest-volume scope type before first live inspection

### Step 4: Baseline Coverage Monitoring

Track at `/baseline-readiness`. Alert CS Lead if:
- Coverage stalls below 50% by Day 10
- Any baseline is rejected twice (escalate to manufacturer)

---

## Phase 4 — Inspection Workflow (Days 1–30)

### Day 1–7: Guided Inspections

CS Lead joins first 2–3 live inspections via screen share to confirm:
- Technician logs in, navigates to `/inspection/new`
- All required fields populated (instrument type, barcode, image)
- Submission succeeds, record appears in `/intake-history`

### Day 7–14: Solo Inspections

Technicians submit independently. CS Lead monitors at `/inspection-readiness`:
- Image capture rate target: ≥ 90%
- Barcode scan rate target: ≥ 70%

### Day 14–30: Full Volume

Target: ≥50 inspections by Day 21. SPD Manager reviews `/findings` daily (target turnaround ≤8 hours).

---

## Phase 5 — Executive Workflow (Days 21–30)

### Day 21: Go-Live Review

1. Open `/go-live-center` — confirm Go-Live Readiness Score ≥ 75
2. Walk SPD Director through Executive Command Center
3. Show first critical findings (if any) and associated CAPA
4. Confirm audit evidence bundle at `/audit-evidence`

### Day 30: First Value Report

1. Generate Value Realization report at `/value-realization`
2. Export for SPD Director — time saved, findings caught, estimated cost avoidance
3. Schedule 60-day ROI review (full report) and 90-day QBR

---

## Escalation Paths

| Issue | Escalation |
|-------|-----------|
| API down / login failures | engineering@lumenai.com — SLA: 2hr response |
| Vendor not submitting baselines | CS Lead facilitates direct vendor call |
| SPD Manager not approving findings | Escalate to SPD Director |
| Customer Health Score Red at Day 14 | Account Executive + emergency intervention |
| Critical finding not reviewed in 24h | CS Lead calls SPD Manager directly |

---

*LumenAI Customer Success — Internal Use Only*  
*LumenAI makes no claim of FDA clearance or regulatory approval.*  
*All AI findings require qualified human review before clinical action.*
