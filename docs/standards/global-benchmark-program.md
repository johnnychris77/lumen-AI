# Global Benchmark Program

**Version:** 1.0
**Status:** Published
**Maintained by:** GSIN Analytics Committee

---

## Purpose

The Global Benchmark Program provides participating healthcare facilities with anonymized, aggregate performance comparisons against network peers. Reports are published on annual, semi-annual, and quarterly cadences. All data is anonymized — no individual facility, patient, or instrument is identified.

**Disclaimer:** Benchmark data represents anonymized aggregate patterns. Association identified in benchmark outputs does not establish causation. Human review required before any operational, clinical, or regulatory decisions.

---

## 1. Annual Benchmark Report

### Coverage

Published annually (Q1 of following year) covering the full prior calendar year.

| Dimension | Metric |
|-----------|--------|
| Contamination | Network contamination rate by instrument category |
| Defects | Network defect rate by grade and category |
| Inspection | Network inspection pass rate and score distribution |
| CAPA | CAPA opening rate, closure rate, time-to-close |
| Baseline adherence | Facilities within/outside tolerance zones |
| Trend | Year-over-year delta for each metric |

### Eligibility Requirements

- Minimum 10 contributing facilities (k-anonymity ≥10)
- Data contribution for ≥9 months of the report year
- Governance Board approval before publication

### Report Sections

1. Executive Summary (1 page)
2. Network Performance Overview
3. Contamination Analysis by Category and Region
4. Defect Trend Analysis
5. Inspection Scoring Distribution
6. CAPA Performance Analysis
7. Regional Breakdowns
8. Year-over-Year Comparison
9. Methodology and Disclaimer

---

## 2. Contamination Benchmark Report

### Cadence

Semi-annual (H1 and H2). Published within 45 days of period close.

### Metrics

| Metric | Description |
|--------|-------------|
| Contamination rate | Events per 1,000 inspection cycles by instrument category |
| Tier distribution | % of contamination findings by Tier 1–4 classification |
| Regional comparison | Anonymized regional rate comparison |
| Trend | 6-month rolling trend vs prior period |
| Alert zone prevalence | % of network in alert or critical deviation zones |
| Emerging signals | Patterns meeting early warning threshold |

### Governance Trigger

If ≥3 facilities report the same contamination pattern in the same quarter, the Contamination Benchmark data automatically triggers a recall early warning review.

---

## 3. Reliability Benchmark Report

### Cadence

Semi-annual (H1 and H2).

### Metrics

| Metric | Description |
|--------|-------------|
| Reliability score | Composite 0–1 score (inspection + functional + documentation) |
| Pass rate | % of instruments passing all inspection domains |
| Defect grade distribution | Network distribution of Grade A–D defects |
| Category reliability | Reliability score by instrument category |
| Cycle count compliance | % of instruments within recommended service cycle |
| Out-of-service rate | % removed from service per inspection cycle |

### Scoring Methodology

Reliability scores use the Inspection Scoring Standard (v3.0) as the basis. Network percentile positions are computed from the distribution of all contributing facilities.

---

## 4. Executive Scorecard

### Cadence

Quarterly. Published within 21 days of quarter close.

### Format

One-page summary for quality leadership and executives:

| Section | Content |
|---------|---------|
| Network Quality Index | Composite 0–100 score (weighted average of contamination, reliability, CAPA) |
| Your Percentile | Where this tenant sits in the network distribution |
| Active Governance Items | Open recall warnings, baseline alerts, CAPA backlog |
| Trend Arrow | vs prior quarter: improving / stable / declining |
| Top 3 Watchpoints | Network-level signals requiring human review |
| Key Metric Table | Contamination rate, inspection pass rate, reliability score, CAPA closure rate |

### Confidentiality

Each scorecard is tenant-specific. No other facility's individual data appears in the scorecard — only aggregate network distributions for comparison.

---

## 5. Network Percentile Methodology

### Computation

1. Collect metric values from all contributing facilities
2. Apply Laplace noise (ε = 0.5) for differential privacy on aggregate statistics
3. Compute network distribution (percentile ranks)
4. Report facility position within distribution (not raw value of other facilities)

### Disclaimer on Percentile Positions

Percentile position is based on the contributing network subset, not all healthcare facilities globally. Facilities not participating in GSIN are not represented. Results reflect the specific reporting period only.

---

## 6. Data Quality Standards

### Contribution Requirements

| Requirement | Standard |
|-------------|----------|
| Minimum facilities | ≥10 for network publication |
| Data period | ≥6 months for semi-annual reports |
| Completeness | ≥80% of mandatory fields populated |
| Validation | Automated range checks + human spot-check |
| k-Anonymity | Verified before any report is published |

### Exclusion Criteria

Data contributions are excluded from benchmark reports if:
- Facility count for a segment falls below 5 (anonymization threshold)
- Data quality validation fails
- Contributing facility withdraws consent

---

## 7. Report Distribution

| Report | Recipients | Format |
|--------|-----------|--------|
| Annual | All GSIN participants | PDF + API access |
| Contamination | All GSIN participants | PDF + API access |
| Reliability | All GSIN participants | PDF + API access |
| Executive Scorecard | Admin + Executive roles | In-app dashboard + PDF |

---

## 8. Governance

- Reports are reviewed by the GSIN Analytics Committee before publication
- Governance Board approves annual reports before public distribution
- All reports include the standard disclaimer and `human_review_required: true` in API responses
- Published reports are archived for minimum 10 years

---

*Benchmark data does not identify individual facilities, patients, or instruments. Association identified in benchmark outputs does not establish causation. Human review required before operational decisions.*
