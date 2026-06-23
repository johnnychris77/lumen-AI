# ROI Reporting Framework

**Version:** Phase 11  
**Date:** 2026-06-23  
**Audience:** LumenAI CS Team, Account Management, Customer SPD Directors  
**Purpose:** Standardize ROI measurement and reporting for LumenAI deployments

---

## ROI Categories

LumenAI delivers measurable value across four categories:

### 1. Operational Efficiency
Time savings from AI-assisted inspection vs. manual paper-log processes.

**Primary metric:** Minutes saved per inspection × total inspections  
**Benchmark:** 8 minutes saved per inspection (LumenAI internal time study)  
**Conservative range:** 5–12 minutes depending on instrument complexity  

**Calculation:**
```
Time Saved (hrs) = (Inspections × 8 min) / 60
Labor Value ($) = Time Saved × SPD Technician hourly rate
```

Typical SPD technician cost: $28–$42/hr including benefits.

---

### 2. Clinical Risk Avoidance
Value of critical findings detected before instruments reach the OR.

**Primary metric:** Critical findings (risk score ≥ 80) × avoidance value  
**Benchmark:** $5,000 per critical finding (instrument repair + event avoidance)  
**Conservative range:** $2,500–$15,000 depending on finding type and instrument value  

**Calculation:**
```
Risk Avoidance ($) = Critical Findings × $5,000
```

Note: Crack and insulation damage findings on high-value scopes (ureteroscopes, bronchoscopes) carry higher avoidance value due to instrument replacement cost ($15k–$50k).

---

### 3. SSI Risk Reduction
Estimated reduction in surgical site infection risk from improved reprocessing documentation.

**Primary metric:** Baseline coverage × SSI risk coefficient  
**Benchmark:** 2% SSI risk reduction per 10% increase in baseline coverage  
**SSI event cost:** $28,000 average (APIC/AORN 2024)  

**Calculation:**
```
SSI Risk Reduction (%) = (Baseline Coverage % / 10) × 2
Annual Events Avoided = Annual Case Volume × SSI Rate × Risk Reduction %
SSI Avoidance Value ($) = Events Avoided × $28,000
```

> Note: This is a directional estimate for business case purposes. LumenAI does not claim clinical outcome guarantees.

---

### 4. CAPA and Quality Workflow Value
Efficiency gains from automated corrective action workflows vs. manual spreadsheet tracking.

**Primary metric:** CAPAs completed × estimated CAPA value  
**Benchmark:** $2,500 per completed CAPA (audit readiness + staff time + documentation)  

---

## Standard ROI Report Template

Available as CSV export from `/roi-center`. Sections:

```
LumenAI ROI Report
Facility: [Facility Name]
Period: [Go-Live Date] – [Report Date]
Prepared by: [CS Rep Name]

── Operational Metrics ──────────────────────
Inspections Completed:     [N]
Critical Findings Detected: [N]
CAPAs Completed:           [N]
Baseline Coverage:         [N]%

── Estimated Value ──────────────────────────
Time Saved:                [N] hours
Labor Value:               $[N]
Critical Finding Avoidance: $[N]
CAPA Workflow Value:       $[N]
SSI Risk Reduction:        [N]% estimated
Total Estimated Value:     $[N]

── Methodology ──────────────────────────────
Time Savings:  8 min/inspection vs. paper log
Finding Value: $5,000 per critical finding
CAPA Value:    $2,500 per closed CAPA
SSI:           APIC/AORN benchmarks

── Disclaimers ──────────────────────────────
Estimates are for business case purposes only.
LumenAI makes no claim of clinical outcome guarantees.
LumenAI makes no claim of FDA clearance or regulatory approval.
All AI outputs require qualified human review before clinical action.
```

---

## Presentation Tips

1. **Lead with critical findings** — "We caught X critical findings before they reached the OR" is the most compelling ROI story.
2. **Anchor to familiar costs** — Hospital executives know SSI costs. Use the $28k benchmark to frame the stakes.
3. **Show the trend** — Even if absolute numbers are low (pilot stage), an upward trend in inspections and baseline coverage signals future value.
4. **Tie to Joint Commission** — AORN ST91:2021 recommends documented reprocessing outcomes. LumenAI is that documentation.
5. **Never overstate** — Use "estimated," "potential," "based on industry benchmarks." The disclaimer matters in healthcare.

---

## Quarterly ROI Review Cadence

| Review | Timing | Audience | Output |
|--------|--------|----------|--------|
| 30-Day Check | Day 30 post go-live | CS + SPD Manager | Health score + early adoption metrics |
| 60-Day Report | Day 60 | CS + SPD Director | ROI preliminary report |
| 90-Day QBR | Day 90 | CS + SPD Director + Executive Sponsor | Full ROI report + renewal discussion |
| Annual Report | Contract anniversary | CS + C-Suite | Full-year ROI + expansion proposal |

---

*LumenAI Customer Success — Internal Use Only*  
*All ROI figures are estimates for business case purposes. LumenAI makes no claim of FDA clearance or regulatory approval.*
