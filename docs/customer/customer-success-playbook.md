# LumenAI Customer Success Playbook
Version 1.0 | Customer Success — CONFIDENTIAL

## Overview
This playbook defines how LumenAI's Customer Success team manages post-sale
customer relationships to drive adoption, retention, expansion, and renewal.

---

## CSM Responsibilities and Cadence

### CSM Assignment by Tier
| Tier | CSM Model | Ratio |
|------|-----------|-------|
| Starter | Pooled CSM (email-first) | 1:50 |
| Professional | Named CSM | 1:20 |
| Enterprise | Dedicated CSM | 1:8 |
| Health System | Dedicated CSM + Executive Sponsor | 1:3 |

### Standard CSM Cadence
| Activity | Starter | Professional | Enterprise | Health System |
|----------|---------|-------------|------------|---------------|
| Kickoff call | Yes | Yes | Yes | Yes |
| Week 2 check-in | Email | Video call | Video call | On-site option |
| Monthly check-in | Email | Video call | Video call | Video call |
| Quarterly Business Review | No | Yes | Yes | Yes |
| Executive briefing | No | No | Annual | Quarterly |
| On-site visit | No | Annual | Semi-annual | Quarterly |

---

## Adoption Tracking Metrics

### Core Adoption KPIs
| Metric | Definition | Target (Healthy) | At-Risk Threshold |
|--------|-----------|-----------------|------------------|
| Weekly Active Users (WAU) | Unique users with >= 1 inspection session | >= 80% of licensed users | < 60% |
| Inspection Sessions/Week | Inspection sessions started in rolling 7 days | >= 3 sessions/week | < 1 session/week |
| AI Finding Acceptance Rate | % of AI findings accepted (not overridden) by technicians | 75–90% | < 60% or > 95% |
| Override Rate | % of AI findings overridden by technicians | < 15% | > 25% |
| Baseline Adoption | % of inspected instruments matched to a baseline | >= 80% | < 50% |
| Feature Depth Score | Breadth of features used (out of available tier features) | >= 60% of features used | < 30% |

### Trend Monitoring
- **Increasing override rate** (> 20% over 2 weeks): Indicates AI/baseline calibration issue or user training gap. Trigger: CSM review + engineering escalation.
- **Declining WAU** (> 10% week-over-week for 2 weeks): Indicates adoption friction. Trigger: CSM call within 48 hours.
- **Zero inspections for 7 days**: Trigger: CSM alert; outreach within 24 hours.

---

## Health Score Model (0–100)

### Health Score Components
| Component | Weight | Healthy Range | Scoring |
|-----------|--------|---------------|---------|
| User adoption (WAU %) | 30% | >= 80% | Linear: 80%+ = 30 pts |
| Inspection volume vs. contract | 25% | >= 70% of contracted volume | Linear: 100% = 25 pts |
| Feature usage depth | 20% | >= 60% of tier features used | Linear: 60%+ = 20 pts |
| Support ticket health | 15% | < 2 open tickets, no SEV1/2 | -5 per open ticket; -15 for any SEV1 |
| NPS / CSAT | 10% | NPS >= 40 or CSAT >= 4.0/5.0 | 10 pts at target; 0 pts below 30/3.5 |

### Health Score Bands
| Band | Score | CSM Action |
|------|-------|-----------|
| Green | 75–100 | Monthly cadence; expansion conversation at 80+ |
| Yellow | 50–74 | Bi-weekly check-in; identify and resolve friction |
| Red | 0–49 | Weekly escalation call; at-risk playbook activated |

---

## 30/60/90/180-Day Milestones

### Day 30 (Post Go-Live)
**Goal**: Technical success confirmed; adoption underway.
- [ ] >= 60% of users have completed >= 1 inspection
- [ ] No open P1/P2 technical issues
- [ ] Baseline adoption >= 60%
- [ ] CSM 30-day check-in call completed
- [ ] Health Score calculated and documented

### Day 60
**Goal**: Adoption established; value beginning to show.
- [ ] WAU >= 70% of licensed users
- [ ] >= 100 inspections completed
- [ ] First PDF report generated and shared with SPD Director
- [ ] Override rate reviewed and within healthy range (< 20%)
- [ ] CSM 60-day check-in; first value confirmation shared

### Day 90
**Goal**: Value proven; pilot conversion or renewal conversation begins.
- [ ] WAU >= 80% of licensed users
- [ ] AI-technician agreement rate confirmed >= 85%
- [ ] JC readiness score generated
- [ ] Pilot ROI report delivered (if on pilot)
- [ ] Expansion or renewal conversation initiated

### Day 180
**Goal**: Platform embedded; expansion in progress.
- [ ] Health Score >= 75 (Green)
- [ ] All tier features in active use
- [ ] Renewal secured or expansion contract signed
- [ ] QBR #1 completed
- [ ] Reference customer request made (if NPS >= 50)

---

## Quarterly Business Review (QBR) Agenda Template

**Duration**: 60 minutes
**Attendees**: CSM + AE (LumenAI); SPD Director + stakeholder (Customer)

### Agenda
1. **Business update** (5 min) — Customer shares any organizational changes, goals
2. **Adoption scorecard** (10 min) — WAU, inspection volume, feature usage
3. **AI performance review** (10 min) — Finding accuracy, override rate, agreement rate
4. **Compliance/regulatory update** (10 min) — JC readiness score, open CAPAs, audit events
5. **Value delivered** (10 min) — ROI summary: labor, instrument, audit savings
6. **Open issues and roadmap** (10 min) — Outstanding tickets, product roadmap preview
7. **Next quarter goals** (5 min) — Agreed targets for WAU, inspection volume, value metrics

**Output**: QBR summary document delivered within 5 business days.

---

## Renewal Playbook

### Renewal Timeline
| Month | Activity |
|-------|---------|
| Month 9 | CSM flags renewal in CRM; pulls health score and usage report |
| Month 10 | CSM delivers "Success Report" — 12-month value delivered |
| Month 11 | AE presents renewal proposal; multi-year discount offered |
| Month 12 | Contract renewed or churn risk escalated to VP CS |

### Renewal Success Report Contents
1. Total inspections completed (12 months)
2. AI findings summary by category
3. Contamination events flagged and resolved
4. Instruments quarantined or redirected before patient contact
5. JC/AAMI readiness score trend
6. Labor savings estimate (from CFO dashboard)
7. Override rate trend (declining = good AI calibration)
8. 12-month vs. pilot success criteria comparison

### Multi-Year Renewal Offer
- 2-year: 10% discount
- 3-year: 15% discount
- Includes tier upgrade credit: customers can upgrade tier mid-term at pro-rated cost

---

## Expansion Triggers

### Signal-Based Expansion Conversations
| Signal | Expansion Play |
|--------|---------------|
| Customer mentions second facility | Propose Enterprise tier; multi-facility pricing |
| Override rate declining (< 10%) | "AI is calibrated — expand to more staff/instruments" |
| JC survey upcoming | "Upgrade to full regulatory automation before survey" |
| New VP/CNO joins | Executive briefing; re-sell value; expansion opportunity |
| Contamination event at facility | Escalate to Enterprise for predictive analytics |
| Manufacturer contract renewal | "Use our vendor scorecard data in your negotiation" |

### Expansion Plays by Tier
| Current Tier | Primary Expansion Play |
|--------------|----------------------|
| Starter | Upgrade to Professional (predictive analytics, copilot) |
| Professional | Add facility; upgrade to Enterprise |
| Enterprise | Add Health System; add Manufacturer Portal |
| Health System | Add custom baseline training; expand manufacturer subscriptions |

---

## At-Risk Indicators and Churn Prevention

### At-Risk Signals
| Signal | Severity | CSM Action |
|--------|----------|-----------|
| WAU < 60% for 2+ weeks | High | Call within 48 hours; identify root cause |
| Override rate > 25% | High | AI calibration review; involve engineering |
| Zero inspections for 7 days | Critical | Same-day outreach; escalate to VP CS if no response |
| Open SEV1/2 ticket > 72 hours | Critical | Daily status until resolved |
| NPS < 20 | High | Executive call; recovery plan within 1 week |
| Budget freeze or re-org mentioned | Medium | Engage executive sponsor; build internal champion |
| Key champion (SPD Director) leaves | High | Re-engage within 48 hours; onboard new champion |

### Churn Prevention Playbook
1. **Identify**: Health Score drops to Yellow; CSM flags in weekly team review
2. **Diagnose**: Root cause call with SPD Director (not IT) — adoption, AI accuracy, or value perception?
3. **Recovery plan**: Written plan within 5 business days with specific milestones
4. **Executive escalation** (if no improvement in 2 weeks): VP CS + customer VP-level call
5. **Last resort**: Offer tier downgrade (retain at lower ARR vs. churn)
6. **Post-churn analysis**: Document reason in CRM; share with Product for roadmap input

### At-Risk Recovery Milestones
- Week 1: Root cause identified
- Week 2: Recovery plan agreed with customer
- Week 4: First KPI improvement visible
- Week 8: Health Score restored to Yellow or above
- Week 12: Health Score Green; at-risk flag cleared

---

## CSM Tooling Requirements
- **CRM**: Salesforce (customer health, renewal dates, expansion opportunities)
- **Health Score dashboard**: Auto-calculated from API usage metrics
- **QBR template**: Standardized slide deck in Google Slides / PowerPoint
- **Success Report template**: Automated from executive dashboard data
- **Escalation path**: Slack channel `#cs-at-risk` with VP CS and AE tagged
