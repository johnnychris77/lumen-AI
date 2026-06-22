# LumenAI Enterprise Executive Expansion Scorecard

> **Audience:** C-suite and VP-level health system leadership reviewing enterprise-wide LumenAI deployment performance and expansion readiness.

---

## Purpose

The Executive Expansion Scorecard provides a consolidated view of LumenAI deployment health across all active facilities in a health system. It is designed to support quarterly expansion go/no-go decisions with objective, data-informed signals.

> All scorecard outputs are candidate signals for human review. They do not constitute clinical recommendations, regulatory findings, or binding operational directives.

---

## Accessing the Scorecard

**API Endpoint:** `GET /api/enterprise/dashboards/executive-scorecard`

**Required Role:** `executive` or `admin`

Every scorecard access is logged to the audit trail with `compliance_flag: true`.

---

## Scorecard KPIs

The scorecard reports 7 enterprise-level KPIs with RAG (Red / Amber / Green) status:

| KPI | Target | Green | Amber | Red |
|-----|--------|-------|-------|-----|
| System Contamination Rate | ≤ 5% | ≤ 5% | ≤ 8% | > 8% |
| System-wide Training Completion | 100% | ≥ 95% | ≥ 80% | < 80% |
| Baseline Coverage | ≥ 80% | ≥ 80% | ≥ 64% | < 64% |
| CAPA Resolution Rate | ≥ 75% | ≥ 75% | ≥ 60% | < 60% |
| Active Facility Adoption | — | tracked | — | — |
| Facilities Ready for Expansion | — | tracked | — | — |
| Overall Readiness Score | ≥ 80 | ≥ 80 | ≥ 64 | < 64 |

**Overall RAG Status Logic:**
- **Green:** All targeted KPIs are Green
- **Amber:** One or more KPIs are Amber, none are Red
- **Red:** Any KPI is Red

---

## Facility Readiness Scoring

Each facility receives a composite Readiness Score (0–100) computed from five dimensions:

| Dimension | Weight | Green Threshold |
|-----------|--------|----------------|
| Training Completion | 20% | 100% |
| Inspection Adoption | 25% | ≥ 50 inspections/30 days |
| Baseline Coverage | 20% | ≥ 80% of trays covered |
| Inspection Volume | 20% | ≥ 20 inspections/30 days |
| Data Quality | 15% | < 5% error rate |

**Readiness Classification:**

| Score | Status |
|-------|--------|
| ≥ 80 | Ready |
| 60–79 | Conditional |
| < 60 | Not Ready |

Access readiness scores: `GET /api/enterprise/dashboards/readiness`

---

## System Quality Dashboard

The System Quality Dashboard (`GET /api/enterprise/dashboards/system-quality`) provides:

- Total inspections across all facilities (last 30 days)
- System-wide contamination rate (candidate signal, human review required)
- Contamination count by type (biofilm, organic, chemical, particulate, unknown)
- Per-facility inspection volume and contamination rate
- **Outlier facilities:** sites with contamination rate > 2× the system average

> Outlier identification is a candidate signal for quality review. It does not confirm a deficiency. Qualified personnel must investigate before any operational or clinical action.

---

## Enterprise Benchmarking

**API Endpoint:** `GET /api/enterprise/dashboards/benchmarking`

Provides facility-level performance relative to:
1. System average (your health system's aggregate)
2. AAMI ST79 external reference: 5% contamination threshold (industry reference standard)

Output includes per-facility deviation from system average and external reference.

> Benchmarking data is for quality improvement reference only. It does not constitute regulatory compliance assessment.

---

## Expansion Decision Framework

The scorecard supports a structured expansion decision:

### Expansion Candidate Criteria (All Required)
- [ ] System Readiness Score ≥ 80
- [ ] Pilot facility has ≥ 90 days of active use
- [ ] No open critical alerts at pilot facility
- [ ] CAPA resolution rate ≥ 75%
- [ ] Training completion ≥ 95% at pilot facility
- [ ] Baseline coverage ≥ 80% at pilot facility
- [ ] Executive scorecard overall status: Green

### Conditional Expansion Criteria (Requires Waiver)
- System Readiness Score 60–79
- Training completion 80–94%
- Baseline coverage 64–79%
- Overall scorecard status: Amber

Conditional expansion requires documented leadership approval and a corrective action plan with timeline.

### Expansion Hold Criteria (Any One Blocks Expansion)
- System Readiness Score < 60
- Open critical patient safety alerts unresolved
- Overall scorecard status: Red
- Active regulatory inquiry related to sterile processing

---

## Quarterly Review Cadence

| Review | Timing | Primary Audience |
|--------|--------|-----------------|
| Monthly Pulse | End of each month | Deployment Team, Customer Success |
| Quarterly Executive Review | End of Q1, Q2, Q3, Q4 | C-suite, VP Quality, VP Operations |
| Annual System Review | Year-end | Board / System Leadership |

The LumenAI Pilot Analytics dashboard supports quarterly review package generation: `GET /api/pilot-analytics/quarterly-review`

---

## Audit Trail

All executive scorecard views are automatically recorded with:
- Accessor identity
- Timestamp (UTC)
- `compliance_flag: true`
- Action: `enterprise_executive_scorecard_view`

Audit records are immutable and available to compliance teams on request.

---

## Limitations and Disclaimers

- LumenAI does not claim FDA clearance for any output
- All quality signals are candidate indicators requiring human review
- Contamination detection accuracy depends on image quality and baseline availability
- Scorecard KPIs reflect operational data available in the system — gaps in data entry affect score accuracy
- Readiness scores are point-in-time snapshots and may not reflect real-time conditions
- Cross-facility benchmarking uses anonymized data; facility identities in aggregates are never disclosed to other tenants

---

*For questions about scorecard interpretation, contact your LumenAI Customer Success Manager or Quality Advisor.*
