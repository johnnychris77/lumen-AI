# Clinical Evidence Summary
LumenAI Surgical Instrument Inspection Software | Version 1.0
**For regulatory package. Subject to regulatory counsel review.**
**IMPORTANT: All performance data at Version 1.0 is derived from mock/simulated datasets. Live multi-site clinical study is pending. This data should not be used as the basis for regulatory submissions without completion of the live reader study.**

---

## 1. Evidence Overview

This document summarizes all clinical evidence generated through P12. It is structured to support a future FDA premarket submission but does not constitute a complete clinical evidence package for submission purposes. See Section 8 for gaps to be resolved before submission.

---

## 2. Validation Dataset

### 2.1 Dataset Specification
| Parameter | Value |
|-----------|-------|
| Total mock cases | 1,200 |
| Cases per category | 100 |
| Number of categories | 12 |
| Total images specified | 3,600 (3 images per instrument) |
| Image status | Specification defined; live image collection pending |
| Dataset type | Mock/synthetic (structured per validation-dataset-specification.md) |
| Annotation protocol | Dual-annotator with adjudication; AAMI ST79 defect taxonomy |

### 2.2 Instrument Categories (12 Categories)
| Category | Contamination/Defect Types Covered |
|---------|------------------------------------|
| Scissors | Blood, tissue residue, corrosion, pitting |
| Forceps | Blood, bone residue, misalignment, crack |
| Retractors | Residue buildup, crack, bent components |
| Needle holders | Blood, insulation damage (if applicable), wear |
| Clamps/Hemostats | Residue, corrosion, ratchet failure |
| Laparoscopic instruments | Insulation damage, crack, seal integrity |
| Electrosurgical instruments | Insulation damage, residue, electrode damage |
| Endoscopic components | Residue, scope damage, channel contamination |
| Rigid scopes | Lens contamination, shaft damage, light guide damage |
| Powered instruments | Residue, mechanical wear, drive system damage |
| Implant trial instruments | Surface damage, dimensional assessment (visual) |
| General instruments | Mixed contamination types |

### 2.3 Dataset Limitations
- Images are mock/simulated; not collected from live SPD environments
- Not collected across multiple geographic sites or hospital types
- Annotators are internal (not independent clinical experts)
- Novel contamination presentations not in training data are not represented

Reference: `docs/clinical/validation-dataset-specification.md`

---

## 3. Study Design

### 3.1 MRMC Reader Study Protocol
| Parameter | Value |
|-----------|-------|
| Study design | Multi-reader multi-case (MRMC) |
| Number of reader roles | 5 (Entry Technician, Senior Technician, Educator, Manager, Infection Prevention Specialist) |
| Number of readers | 35 total (7 per role) |
| Case set size | 500 cases (subset of 1,200-case dataset) |
| Reference standard | Dual-annotator consensus with board-certified infection prevention expert adjudication |
| Blinding | Readers blinded to AI findings; separate AI reading arm |
| Washout period | 4 weeks between reading arms |
| Statistical analysis | MRMC ANOVA (Obuchowski-Rockette method); Wilson score 95% CIs |
| Study status | Protocol defined; pending live execution |

Reference: `docs/clinical/human-vs-ai-study-protocol.md`

### 3.2 Sealed Test Set Protocol
| Parameter | Value |
|-----------|-------|
| Test set size | 20% of total dataset (240 cases) withheld |
| SHA-256 lock | Applied at dataset freeze; manifest recorded |
| Access control | No model developer access until formal evaluation |
| Evaluation trigger | Prior to 510(k) submission and any major model update |

Reference: `docs/clinical/sealed-test-set-protocol.md`

---

## 4. AI Performance (Mock Data)

**All values are from mock/simulated dataset. Live data pending.**

### 4.1 Overall Performance
| Metric | Value | 95% CI (Wilson Score) | Acceptance Threshold | Status |
|--------|-------|----------------------|---------------------|--------|
| Accuracy | ~90% | [87.8%, 92.1%] | 85% | Met |
| Precision | ~90% | [88.0%, 91.9%] | 85% | Met |
| Recall (Sensitivity) | ~89% | [86.7%, 91.1%] | 85% | Met |
| F1 Score | ~89% | [87.1%, 90.9%] | 85% | Met |
| Cohen's Kappa | ~0.79 | [0.76, 0.82] | 0.80 (primary endpoint) | At Risk |
| AUC (ROC) | ~0.93 | [0.91, 0.95] | 0.88 | Met |
| Critical FN Rate | ~1.8% | [1.2%, 2.6%] | <2% | Met (marginally) |

**Primary endpoint status**: Kappa 0.79 is marginally below the 0.80 threshold. The 95% CI lower bound (0.76) confirms the point estimate is close to but below threshold. This is a risk flag for the primary endpoint; live study results will be determinative.

Reference: `docs/clinical/clinical-performance-report.md`

### 4.2 Critical Findings Subgroup Analysis
| Finding Category | Sensitivity | 95% CI | Threshold |
|----------------|------------|--------|----------|
| Crack | 93.1% | [88.2%, 96.4%] | 88% |
| Corrosion | 92.4% | [87.3%, 95.8%] | 88% |
| Insulation damage | 91.8% | [86.5%, 95.3%] | 88% |
| Blood contamination | 94.2% | [89.5%, 97.0%] | 88% |
| Bone residue | 91.3% | [86.0%, 94.9%] | 88% |

All critical finding categories meet the 88% sensitivity threshold on mock data.

### 4.3 Non-Critical Findings Subgroup Analysis
| Finding Category | Sensitivity | 95% CI | Threshold |
|----------------|------------|--------|----------|
| Tissue residue | 88.6% | [83.1%, 92.7%] | 87% |
| Pitting | 87.9% | [82.3%, 92.1%] | 87% |
| Residue buildup | 87.2% | [81.5%, 91.5%] | 87% |

All non-critical finding categories meet the 87% sensitivity threshold on mock data.

---

## 5. Human Reader Performance (Simulated)

**Values are simulated based on literature benchmarks for SPD technician performance. Not from live reader study.**

### 5.1 Performance by Reader Role
| Reader Role | Recall | Precision | Kappa | Notes |
|-------------|--------|----------|-------|-------|
| Entry Technician | ~79% | ~76% | ~0.67 | Simulated; per literature benchmarks |
| Senior Technician | ~87% | ~85% | ~0.75 | Simulated |
| SPD Educator | ~93% | ~91% | ~0.84 | Simulated |
| SPD Manager | ~85% | ~83% | ~0.73 | Simulated |
| Infection Prevention Specialist | ~88% | ~87% | ~0.77 | Simulated |

### 5.2 AI vs. Best Human Reader
| Metric | AI | Best Human (Educator) | AI vs. Best Human |
|--------|----|-----------------------|------------------|
| Recall | ~89% | ~93% | Educator superior by ~4pp |
| Precision | ~90% | ~91% | Comparable |
| Kappa | ~0.79 | ~0.84 | Educator superior by ~0.05 |

Note: AI performance is comparable to or exceeds senior technician performance, and approaches educator-level performance. AI provides a meaningful floor for facilities without experienced educators.

### 5.3 Inter-Rater Reliability (Simulated)
| Reader Pair | Kappa | Interpretation |
|------------|-------|---------------|
| Entry vs. Senior Technician | ~0.72 | Substantial agreement |
| Senior vs. Educator | ~0.79 | Substantial agreement |
| Educator vs. Manager | ~0.76 | Substantial agreement |
| Manager vs. IP Specialist | ~0.80 | Substantial agreement |
| AI vs. Educator (best human) | ~0.79 | Substantial agreement |

---

## 6. Statistical Methods

### 6.1 Primary Analysis Methods
| Metric | Method |
|--------|--------|
| Sensitivity, Specificity, Precision | Exact binomial with Wilson score 95% CI |
| Cohen's Kappa | Standard kappa with bootstrap 95% CI (n=1000 bootstrap iterations) |
| AUC | DeLong method for 95% CI |
| MRMC (reader study) | Obuchowski-Rockette (OR) method |
| Subgroup analysis | Stratified Wilson score CIs; no multiple comparison correction (exploratory) |

### 6.2 Statistical Significance Policy
- Primary endpoint (kappa): One-sided test; H0: kappa <= 0.70; alpha = 0.05
- Secondary endpoints: Two-sided tests; alpha = 0.05 per endpoint
- Confidence intervals: 95% Wilson score for proportions; 95% bootstrap for kappa

---

## 7. Real-World Evidence Plan

Post-market RWE collection per `docs/clinical/real-world-evidence-plan.md`:
- Enroll participating sites starting at commercial launch
- Collect de-identified inspection outcomes with AI finding and technician decision
- Monthly PSI/CSI drift monitoring
- Quarterly performance analysis on labeled production subset
- Annual full RWE report submitted to Regulatory Affairs

---

## 8. Gaps to Regulatory Submission

The following gaps must be resolved before this evidence summary can support a 510(k) submission:

| Gap | Description | Resolution Plan | Target |
|----|------------|----------------|--------|
| GAP-01 | All performance data is mock/simulated | Execute live multi-site MRMC reader study | Q3 2026 |
| GAP-02 | Live reader study not executed | Recruit 35 readers; 5 sites minimum | Q2-Q3 2026 |
| GAP-03 | Sealed test set evaluation pending | Execute after live study completion | Q4 2026 |
| GAP-04 | Usability study not conducted | IEC 62366 formative + summative study | Q2 2026 |
| GAP-05 | Primary endpoint (kappa) at risk (0.79 < 0.80 threshold) | Confirm with live study; may require threshold negotiation with FDA via Q-Sub | Q3-Q4 2026 |
| GAP-06 | Multi-site RWE enrollment not started | Begin at commercial launch | Q3 2026 |
| GAP-07 | External annotator validation | Engage independent clinical expert panel for annotation review | Q1-Q2 2026 |
| GAP-08 | Geographic diversity in training data | Expand dataset to include sites in different regions | Q2-Q3 2026 |

---

## 9. Clinical Evidence Summary Statement

LumenAI Version 1.0 has completed a comprehensive pre-clinical validation using 1,200 mock cases across 12 instrument categories. AI performance on mock data meets or exceeds acceptance thresholds for all metrics except the primary endpoint (kappa 0.79 vs. threshold 0.80 — marginally below).

The live multi-site MRMC reader study (Q3 2026) will be the determinative clinical evidence for regulatory submission. Until that study is completed, LumenAI's clinical claims should be framed as "based on pre-clinical simulation" and should not be used as the sole basis for regulatory submission or broad commercial deployment in a clinical setting.

**This evidence summary requires review by qualified regulatory counsel and clinical validation experts before use in any regulatory submission.**

Reference documents:
- `docs/clinical/clinical-performance-report.md`
- `docs/clinical/clinical-validation-plan.md`
- `docs/clinical/human-vs-ai-study-protocol.md`
- `docs/clinical/validation-dataset-specification.md`
- `docs/clinical/sealed-test-set-protocol.md`
- `docs/clinical/real-world-evidence-plan.md`
- `docs/clinical/baseline-validation-protocol.md`
- `docs/clinical/clinical-safety-review.md`
