# Customer Health Framework

**Version:** Phase 11  
**Date:** 2026-06-23  
**Audience:** LumenAI Customer Success, Account Management  
**Purpose:** Define how customer health is measured, scored, and acted upon

---

## Overview

The LumenAI Customer Health Score (CHS) is a five-factor composite score (0–100) that predicts renewal likelihood and identifies customers needing proactive intervention. It is computed automatically and displayed on the Customer Success Dashboard (`/customer-success`).

---

## Health Score Factors

### 1. Adoption Score (20% weight)
Measures breadth of feature utilization.

| Score | Condition |
|-------|-----------|
| 100 | ≥ 70% of available workflows actively used |
| 50 | 40–69% of workflows used |
| 0 | < 40% of workflows used |

**Key signals:** New Inspection form usage, Review Queue activity, CAPA workflow usage, Baseline Library access.

---

### 2. Inspection Score (20% weight)
Measures inspection volume relative to expected fleet activity.

| Score | Condition |
|-------|-----------|
| 100 | ≥ 50 inspections completed |
| 50 | 10–49 inspections completed |
| 0 | < 10 inspections completed |

**Key signals:** Total inspections, inspections per week, trend (growing vs. declining).

---

### 3. Baseline Score (20% weight)
Measures approved baseline coverage relative to active instrument fleet.

| Score | Condition |
|-------|-----------|
| 100 | ≥ 75% of instrument types have approved baselines |
| 50 | 50–74% coverage |
| 0 | < 50% coverage |

**Key signals:** Approved baselines, pending backlog, rejection rate, time-to-approval.

---

### 4. Engagement Score (20% weight)
Measures platform engagement depth and frequency.

| Score | Condition |
|-------|-----------|
| 100 | ≥ 5 logins/week average |
| 50 | 2–4 logins/week |
| 0 | < 2 logins/week |

**Key signals:** Login frequency, session depth (pages visited per session), executive dashboard views.

---

### 5. Data Completeness Score (20% weight)
Measures quality and completeness of submitted records.

| Score | Condition |
|-------|-----------|
| 100 | ≥ 80% of inspection records have all key fields |
| 50 | 60–79% completeness |
| 0 | < 60% completeness |

**Key signals:** Inspections with barcode captured, inspections with instrument type, inspections with confidence score.

---

## Health Bands

| Band | CHS Range | Color | Meaning |
|------|-----------|-------|---------|
| Healthy | 70–100 | 🟢 Green | On track for renewal. Standard CS cadence. |
| At-Risk | 40–69 | 🟡 Yellow | Adoption lagging. Proactive check-in within 2 weeks. |
| Critical | 0–39 | 🔴 Red | Churn risk. Immediate intervention required. |

---

## CS Playbooks by Health Band

### Green (70–100)
**Cadence:** Monthly check-in  
**Actions:**
- Review ROI report with SPD Director
- Identify expansion opportunities (additional departments, users)
- Begin renewal conversation at Day 75
- Prepare QBR materials at Day 90

### Yellow (40–69)
**Cadence:** Bi-weekly check-in  
**Actions:**
- Identify specific adoption gaps (which workflows are unused)
- Schedule targeted training session for lagging workflows
- Review baseline coverage — offer vendor onboarding assistance
- Escalate to account executive if no improvement in 30 days

### Red (0–39)
**Cadence:** Weekly check-in  
**Actions:**
- Emergency call with SPD Director and IT lead within 48h
- Root cause analysis: technical barrier, workflow barrier, or leadership barrier
- If technical: escalate to engineering with SLA
- If workflow: schedule on-site training
- If leadership: escalate to account executive + executive sponsor

---

## Renewal Risk Indicators

Beyond the CHS, the following signals independently indicate renewal risk:

| Signal | Risk Level |
|--------|-----------|
| No logins in 14+ days | High |
| Zero inspections in 30 days | High |
| Baseline coverage declining | Medium |
| Review turnaround > 48h | Medium |
| Admin not responding to CS emails | High |
| Open critical findings not reviewed | High |
| CAPAs open > 60 days | Medium |

---

## QBR (Quarterly Business Review) Template

### Section 1 — Platform Performance (10 min)
- Customer Health Score trend (last 90 days)
- Inspection volume vs. baseline
- Baseline coverage progress

### Section 2 — ROI Summary (10 min)
- Time saved vs. paper log
- Critical findings detected
- CAPAs completed
- Estimated cost avoidance

### Section 3 — Joint Commission / Accreditation Readiness (5 min)
- Audit trail completeness
- Evidence bundle status
- Open findings / CAPA backlog

### Section 4 — Roadmap Preview (5 min)
- Upcoming phase releases
- Features relevant to customer's specific gaps

### Section 5 — Renewal / Expansion (10 min)
- Current tier vs. usage
- Expansion opportunities
- Renewal terms and timeline

---

*LumenAI Customer Success — Internal Use Only*  
*All AI outputs require qualified human review before clinical action.*
