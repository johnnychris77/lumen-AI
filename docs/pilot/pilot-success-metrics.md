# LumenAI Pilot Success Metrics

**Version:** 1.0  
**Effective Date:** 2026-06-21  
**Review Cadence:** Weekly during pilot; monthly thereafter  

---

## 1. Metric Categories

Success is evaluated across four categories:
1. **Adoption** — Is the system being used?
2. **Data Quality** — Is the data collected suitable for analysis?
3. **Operational Value** — Is the system improving SPD operations?
4. **User Satisfaction** — Are users finding the system useful?

---

## 2. Adoption Metrics

| Metric | Definition | Pilot Target | Measurement Source |
|--------|-----------|-------------|-------------------|
| Weekly Active Users | Unique users who submit ≥1 inspection per week | ≥ 80% of enrolled users | `/api/history/summary` |
| Inspection Submission Rate | Inspections submitted vs. estimated inspection volume | ≥ 60% by week 4 | Site coordinator estimate vs. DB count |
| Login Frequency | Average logins per enrolled user per week | ≥ 3 | Auth log analysis |
| Feature Adoption — Images | % of inspections with at least one image attached | ≥ 30% by week 8 | Inspection records with sha256 populated |
| Multi-Finding Capture | % of inspections with 2+ finding types selected | Tracked (no threshold) | DB analysis |

### Adoption Milestones

| Milestone | Trigger | Action |
|-----------|---------|--------|
| Early Concern | WAU < 40% for 2 consecutive weeks | CS Lead schedules site visit |
| Adoption Risk | WAU < 25% for 3 weeks | Pilot review meeting; possible extension |
| Adoption Success | WAU ≥ 80% for 4 consecutive weeks | Document as adoption case study |

---

## 3. Data Quality Metrics

| Metric | Definition | Target | Measurement Source |
|--------|-----------|--------|-------------------|
| Mandatory Field Completeness | % of records with all mandatory fields populated | ≥ 95% | DB field null check |
| Issue Consistency Rate | % of stain_detected=true records with detected_issue populated | 100% | DB validation query |
| Duplicate Rate | % of records that appear to be duplicates (same instrument, same time ±5 min) | < 2% | DB analysis |
| Invalidation Rate | % of records marked `status=invalidated` | < 1% | DB query |
| Volume Target Achievement | Site meets weekly volume target (≥25/week) | ≥ 80% of weeks | DB count |

---

## 4. Operational Value Metrics

These metrics assess whether LumenAI is creating measurable value for SPD operations. All values are *potential associations* requiring human review and should not be interpreted as causal findings.

| Metric | Definition | Measurement Method | Notes |
|--------|-----------|-------------------|-------|
| Quality Signal Detection Rate | Number of emerging risk signals generated per month | Count from `/api/intelligence/emerging-risks` | Requires ≥3 events/90 days per instrument type to trigger |
| CAPA Initiation Rate | Number of CAPAs opened following signal review | Site coordinator report | Human-initiated; not auto-triggered |
| Instrument Type Coverage | Unique instrument types logged as % of facility inventory | Site coordinator estimate vs. DB | Target: ≥ 70% of high-volume instrument types |
| Time-to-Log | Estimated time from physical inspection to record submission | Weekly survey (5-point scale) | Target: users report < 5 min per record |
| Findings Review Utilization | % of flagged inspections reviewed within 48 hours | DB query on reviewed_at field | Target: ≥ 80% reviewed within 48 hours |

### Value Demonstration Threshold

The pilot is considered to demonstrate operational value if, by week 12:
- At least 2 quality signals are generated from real data
- At least 1 CAPA is initiated based on a signal
- Site coordinator rates system value ≥ 4/5 on exit survey

---

## 5. User Satisfaction Metrics

### 5.1 Weekly Pulse Survey (3 Questions, 1–5 Scale)

Sent to all active users every Friday:

1. How easy was LumenAI to use this week? (1=Very difficult, 5=Very easy)
2. How useful was the information LumenAI provided? (1=Not useful, 5=Very useful)
3. Would you recommend LumenAI to a colleague? (1=Definitely not, 5=Definitely yes)

**Targets:**
- Ease of use: ≥ 3.5 average by week 4
- Usefulness: ≥ 3.5 average by week 8
- NPS proxy (Q3): ≥ 4.0 average by week 12

### 5.2 Pilot Exit Survey (Week 12)

Administered to all enrolled users. Key questions:

- Overall satisfaction with LumenAI (1–5)
- Top 3 features used most frequently (multi-select)
- Top 3 pain points or missing features (open text)
- Would your facility continue using LumenAI after the pilot? (Yes/No/Maybe)
- Would you recommend LumenAI to peer facilities? (Yes/No/Maybe)

**Target:** ≥ 70% of surveyed users respond "Yes" or "Maybe" to continuation question.

---

## 6. Pilot Go/No-Go Scorecard (Week 12 Assessment)

| Category | Weight | Pass Threshold | Score |
|----------|--------|---------------|-------|
| Adoption (WAU ≥ 80% for last 4 weeks) | 30% | Pass/Fail | |
| Data Quality (completeness ≥ 95%) | 25% | Pass/Fail | |
| Operational Value (≥ 1 CAPA from signal) | 25% | Pass/Fail | |
| User Satisfaction (exit survey ≥ 3.5/5) | 20% | Pass/Fail | |

**Recommendation to proceed to commercial deployment:** Pass ≥ 3 of 4 categories.

---

## 7. Metrics Reporting Schedule

| Report | Frequency | Audience | Owner |
|--------|-----------|---------|-------|
| Daily metrics snapshot | Daily | LumenAI Ops | Automated |
| Weekly pilot summary | Weekly (Friday) | CS Lead + Site Coordinator | CS Lead |
| Monthly stakeholder report | Monthly | Leadership + Investors | Product Lead |
| Pilot exit report | Week 12 | All stakeholders | CS Lead + Product Lead |
