# Human vs. AI Reader Study Protocol
Version: 1.0

## 1. Study Overview

Prospective, blinded, multi-reader multi-case (MRMC) study comparing LumenAI CV
findings against human readers across SPD professional roles.

**Study title:** LumenAI Human vs. AI Inspection Reader Study (HAIRS-001)
**Design:** Prospective, blinded, MRMC
**Setting:** 3 hospital SPD sites minimum
**Primary comparator:** AI system vs. senior SPD Technician (CRCST > 2 years)
**Analysis type:** Non-inferiority (primary), superiority analysis (exploratory)

### Hypothesis

H₀: AI agreement with ground truth is inferior to senior technician by > 5% (kappa margin)
H₁: AI is non-inferior to senior technician within 5% kappa margin

---

## 2. Reader Groups

| Role | N | Qualification |
|------|---|---------------|
| SPD Technician (entry) | 10 | CRCST ≤ 2 years |
| SPD Technician (senior) | 10 | CRCST > 2 years |
| SPD Educator | 5 | CS educator certification |
| SPD Manager | 5 | CHL or equivalent |
| Infection Prevention Specialist | 5 | CIC certification |
| LumenAI AI System | 1 | P4 CV module |

**Total human readers:** 35
**Recruitment:** Via SPD professional networks, IAHCSMM chapters, site coordinator outreach
**Exclusion criteria:** Readers who participated in LumenAI development or beta testing;
readers with < 6 months SPD experience at time of study

---

## 3. Case Set

### 3.1 Case Set Composition
- **Minimum 500 instrument images** (target: 600 for attrition buffer)
- **Stratified:** 50 images per finding category × 12 categories = 600 images
- **Prevalence-matched** to real SPD encounter rates (contamination findings more frequent)
- **Ground truth:** consensus of 3 SPD educators (majority vote = 2/3 agreement)

### 3.2 Case Set Construction
- Cases assembled from validation dataset (see Validation Dataset Specification)
- Randomized presentation order per reader (different seed per reader)
- No identifying information: instrument images only, no hospital, patient, or staff data
- Cases balanced: minimum 40% positive (finding present), maximum 60% negative

### 3.3 Instrument Coverage
Cases must include instruments from all major SPD categories:
- Laparoscopic instruments (graspers, scissors, dissectors)
- Open surgical instruments (clamps, retractors, needle holders)
- Powered instruments (where applicable)
- Flexible endoscopes (excluded from structural defect cases, included for contamination)
- Tracking label instruments (all UDI/barcode/QR categories)

---

## 4. Metrics

For each reader vs. ground truth:

| Metric | Formula | Description |
|--------|---------|-------------|
| Agreement rate | (TP + TN) / N | Overall correct classifications |
| Precision | TP / (TP + FP) | Positive predictive value |
| Recall (Sensitivity) | TP / (TP + FN) | True positive rate |
| Specificity | TN / (TN + FP) | True negative rate |
| F1 | 2 × (P × R) / (P + R) | Harmonic mean of precision and recall |
| Cohen's kappa | (Po - Pe) / (1 - Pe) | Agreement adjusted for chance |
| AUC-ROC | Area under ROC curve | Per finding category |
| False Negative Rate | FN / (FN + TP) | Miss rate (safety-critical) |

**Primary metric:** Cohen's kappa (AI vs. ground truth)
**Safety metric:** FN rate for critical findings (crack, corrosion, insulation)

---

## 5. Statistical Analysis Plan

### 5.1 Primary Analysis
- **Test:** One-sided non-inferiority test
- **Comparator:** AI system vs. senior technician (CRCST > 2 years, mean performance)
- **Non-inferiority margin:** δ = 0.05 kappa units
- **Significance level:** α = 0.05 (one-sided)
- **Power:** 80% at true difference = 0

### 5.2 Confidence Intervals
- 95% bootstrap confidence intervals (10,000 bootstrap resamples)
- Wilson score CIs for proportions (sensitivity, specificity, FN rate)
- DeLong method for AUC-ROC CIs

### 5.3 Sample Size Justification
- **500 cases** achieves 80% power at α = 0.05
- Assuming base kappa = 0.82, SD = 0.08, non-inferiority margin = 0.05
- Attrition adjustment: 20% buffer → target 600 cases
- Software: Python scipy.stats, statsmodels

### 5.4 Secondary Analyses
- Per-reader group comparison (ANOVA / Kruskal-Wallis)
- Per-finding-category sensitivity/specificity (12 tests; Bonferroni correction applied)
- Learning curve analysis: early vs. late case performance per reader
- Experience level subgroup analysis (entry vs. senior vs. educator)

### 5.5 Missing Data
- Cases where reader did not provide a judgment: excluded from that reader's analysis
- Readers with > 10% missing cases: excluded from primary analysis
- Sensitivity analysis: worst-case imputation for missing critical finding judgments

---

## 6. Blinding & Controls

### 6.1 Reader Blinding
- Human readers receive cases via web-based case review platform
- Cases presented one at a time; no access to other readers' results
- Readers blinded to AI output until after study completion
- AI system evaluated on same case set in batch mode (no access to human annotations)

### 6.2 Ground Truth Blinding
- Ground truth panel (3 SPD educators) evaluate cases independently
- Panel members blinded to each other until consensus meeting
- Consensus meeting: disagreements adjudicated by structured discussion; final decision by CVC chair if 3-way disagreement

### 6.3 Study Coordinator Controls
- Site coordinators monitor for protocol deviations
- Readers may not discuss cases with colleagues during study period
- Electronic case delivery system timestamps all reader interactions
- Any deviation documented in protocol deviation log

---

## 7. Data Collection Protocol

### 7.1 Reader Onboarding
1. Provide written consent / participation agreement
2. Complete 30-minute orientation module (case platform tutorial; no training on finding categories)
3. Complete 10 calibration cases (not included in primary analysis) to familiarize with platform
4. Confirm understanding of protocol; sign attestation

### 7.2 Case Review Workflow
For each case, readers provide:
- Finding present / absent (binary judgment per category shown)
- Confidence rating (1–5 Likert scale)
- Time to decision (auto-captured by platform)
- Optional free-text notes

### 7.3 Data Export & Integrity
- Case platform exports data in CSV and JSON formats
- Exports include: reader ID (anonymized), case ID, finding category, judgment, confidence, timestamp
- Data integrity check: row counts vs. expected; hash verification
- Raw data archived in HIPAA-compliant encrypted S3 bucket

---

## 8. Adverse Finding Escalation Protocol

During the study, if a reader identifies a finding that raises an immediate patient safety
concern (e.g., instrument with visible critical defect in active clinical use):

1. Reader flags case as "Urgent — Safety Concern" in platform
2. Site coordinator notified within 15 minutes
3. Site coordinator escalates to SPD Manager per hospital protocol
4. Study coordinator documents event in adverse finding log
5. Case is retained in study but flagged for sensitivity analysis
6. CVC notified of all safety escalations within 24 hours

**Note:** This protocol applies to instruments identified as being in active clinical
service. Study-only cases (images of decommissioned instruments) do not trigger
this protocol.

---

## 9. Reporting Requirements

### 9.1 Interim Reports
- After 50% case completion: interim safety review (CVC)
- Stopping rules: if critical finding FN rate > 5% at interim, study paused for CVC review

### 9.2 Final Report
The Clinical Performance Report must include:
- Reader demographics and qualification summary
- Case set composition and prevalence table
- Primary endpoint result with CI and non-inferiority decision
- Per-reader group performance table
- Per-category sensitivity/specificity table
- Critical finding FN rate with CI
- AI vs. senior technician comparison
- Protocol deviations and their impact assessment
- Recommendations for regulatory submission

### 9.3 Regulatory Package
Documents for 510(k) submission:
- This protocol (signed)
- Clinical Performance Report (final)
- Statistical Analysis Report (signed by biostatistician)
- Ground truth adjudication log
- Site agreements and IRB approvals
- Raw data (de-identified) on secure media
