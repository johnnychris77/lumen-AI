# Baseline Validation Protocol

## 1. Purpose

Validate that manufacturer, vendor, and hospital baselines established in P5
(Baseline Comparison module) correlate with real inspection outcomes from P4
CV findings. This protocol ensures that LumenAI's three-tier baseline system
provides clinically meaningful, evidence-backed comparisons rather than
arbitrary reference points.

**Document ID:** LUM-BVP-001
**Version:** 1.0
**Scope:** P5 Baseline Comparison module validation

---

## 2. Manufacturer Baseline Validation

### 2.1 Objective
Validate that LumenAI's manufacturer baseline scores align with the acceptance/rejection
criteria specified by instrument manufacturers in their Instructions for Use (IFU).

### 2.2 Data Sources
- Manufacturer-provided IFU (Instructions for Use) acceptance criteria
  (obtained from manufacturer quality/regulatory contacts)
- LumenAI baseline score computed from P4 CV findings on validated instrument images
- Independent inspection audit by SPD Educator panel (ground truth)

### 2.3 Methodology
1. For each instrument category (minimum 10 instrument types), obtain IFU pass/fail criteria
2. Process same instruments through LumenAI CV pipeline; record baseline score
3. SPD Educator panel independently evaluates instruments per IFU criteria
4. Compare: LumenAI pass/fail decision vs. IFU-based Educator decision

### 2.4 Metrics
- **Primary:** Concordance rate = % of cases where LumenAI decision agrees with IFU decision
- **Secondary:** Cohen's kappa (LumenAI vs. IFU/Educator)
- **Safety:** FN concordance rate (LumenAI pass when IFU requires fail)

### 2.5 Acceptance Threshold
- Concordance rate **≥ 90%** per instrument category
- No instrument category with concordance < 80% (floor threshold)
- Critical safety FN concordance (LumenAI passes what IFU fails): **≤ 1%**

---

## 3. Vendor Baseline Validation

### 3.1 Objective
Validate that LumenAI's vendor scorecard (P6) correlates with independent audit findings,
confirming that vendor performance rankings reflect actual instrument quality from those vendors.

### 3.2 Data Sources
- Purchase order inspection certificates from vendors (last 12 months)
- LumenAI vendor scorecard scores (P6 Vendor Intelligence module)
- Independent inspection audit of a stratified sample of instruments from each vendor

### 3.3 Methodology
1. Identify minimum 5 active vendors with ≥ 20 instruments in LumenAI system
2. For each vendor, pull LumenAI scorecard score (composite of finding rates, repair history, etc.)
3. Independent audit: SPD Educator panel inspects stratified random sample (n=20 per vendor)
4. Record audit outcome score (% pass on IFU criteria)
5. Compute Spearman rank correlation between LumenAI vendor score and audit outcome

### 3.4 Metrics
- **Primary:** Spearman rank correlation (ρ) between vendor scorecard rank and audit outcome rank
- **Secondary:** Kendall's tau (ordinal agreement)

### 3.5 Acceptance Threshold
- Spearman ρ **≥ 0.75**
- P-value < 0.05 (statistical significance)
- No vendor where LumenAI score is > 20 percentile points above audit outcome
  (guards against systematic over-rating of poor vendors)

---

## 4. Hospital Baseline Validation

### 4.1 Objective
Validate that LumenAI risk scores from the hospital baseline (P5) are associated with
documented adverse events linked to instrument failures, establishing clinical validity
of the risk stratification.

### 4.2 Data Sources
- Hospital QA records (past 12 months of infection events linked to instrument failures)
- Instrument failure reports (biomed/SPD incident logs)
- LumenAI risk scores at the time of last inspection for involved instruments
- Control instruments: matched instruments from same category with no adverse event

### 4.3 Methodology
1. Obtain de-identified adverse event records from participating sites
2. Link events to instrument IDs in LumenAI system (where instrument tracking exists)
3. Retrieve last LumenAI risk score before each event date
4. Select matched controls (same instrument type, same site, same date window, no event)
5. AUC-ROC analysis: LumenAI risk score as predictor of adverse event (binary outcome)

### 4.4 Metrics
- **Primary:** AUC-ROC for predicting instrument-linked adverse events
- **Secondary:** Sensitivity/specificity at the clinical threshold score (currently 0.70)
- **Calibration:** Hosmer-Lemeshow goodness-of-fit test

### 4.5 Acceptance Threshold
- AUC-ROC **≥ 0.80**
- 95% CI lower bound ≥ 0.70
- Hosmer-Lemeshow p > 0.05 (good calibration)

### 4.6 Limitations & Caveats
- Adverse events are rare; sample size may limit power at initial validation
- Confounding factors (sterilization methods, instrument age, user variability) not fully controlled
- AUC < 0.80 does not necessarily indicate model failure — may reflect rarity of events
  or incomplete adverse event reporting at site
- Longitudinal data required for full validation; initial assessment treated as exploratory

---

## 5. Validation Cadence

| Validation Type | Frequency | Trigger |
|----------------|-----------|---------|
| Manufacturer baseline concordance | Initial deployment | Always |
| Manufacturer baseline concordance | Annual | Scheduled |
| Vendor scorecard correlation | Initial deployment | Always |
| Vendor scorecard correlation | Bi-annual | Scheduled |
| Hospital AUC-ROC | 12 months post-deployment | First annual |
| Hospital AUC-ROC | Annual thereafter | Scheduled |
| All baselines | Immediate | Performance drift detected |

---

## 6. Drift Detection

### 6.1 Population Stability Index (PSI)
Monitors shifts in the distribution of CV finding rates over time.

**PSI formula:**
```
PSI = Σ (Actual% - Expected%) × ln(Actual% / Expected%)
```

- Expected distribution: baseline period (first 90 days post-deployment)
- Actual distribution: rolling 30-day window
- Computed per finding category and for overall finding rate

**Thresholds:**
| PSI Value | Interpretation | Action |
|-----------|---------------|--------|
| < 0.10 | Stable | Continue monitoring |
| 0.10 – 0.20 | Moderate shift | Investigate; no immediate action |
| > 0.20 | Significant shift | Alert CVC; trigger drift review |

### 6.2 Concept Stability Index (CSI)
Monitors shifts in the relationship between CV findings and baseline scores.

- Computed as change in rank correlation between finding severity and baseline score
- Baseline: initial deployment period
- Threshold: CSI > 0.15 triggers drift review

### 6.3 Alert Workflow
1. Quarterly drift report auto-generated by P12 validation engine
2. If PSI > 0.2 or CSI > 0.15: automated alert to Clinical AI Validation Lead
3. Within 5 business days: preliminary assessment report to CVC
4. Within 30 days: determination — remediation required vs. natural variation
5. If remediation required: model update → change control → mini-validation → re-deployment
