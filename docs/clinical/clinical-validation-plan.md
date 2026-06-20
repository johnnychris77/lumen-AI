# LumenAI Clinical Validation Plan
Version: 1.0 | Classification: CONFIDENTIAL — Clinical Use Only

## 1. Purpose & Scope

This Clinical Validation Plan (CVP) defines the strategy, methodology, and acceptance
criteria for validating LumenAI's AI-assisted surgical instrument inspection capabilities
prior to commercial deployment in hospital Sterile Processing Departments (SPD).

LumenAI is a Software as a Medical Device (SaMD) that applies computer vision (CV) and
machine learning to identify instrument contamination, structural defects, and
tracking/identification failures. This plan governs pre-market validation of the
inspection intelligence, ranking, baseline comparison, and CV capabilities introduced
in product milestones P4–P12.

**In Scope:**
- CV finding detection (12 finding categories: blood, bone, tissue, residue, corrosion,
  crack, pitting, insulation, barcode, udi, qr, keydot)
- AI ranking and prioritization of inspection findings
- Manufacturer/vendor/hospital baseline comparison (P5)
- Human vs. AI reader agreement study
- False Positive (FP) and False Negative (FN) analysis

**Out of Scope:**
- Autonomous clinical decision-making (LumenAI is decision-support only)
- Surgical outcome measurement
- Post-market surveillance (addressed separately in post-market plan)

---

## 2. Regulatory Context

### 2.1 FDA SaMD Classification (Class II, 510(k) Pathway)

LumenAI is classified as a Class II medical device under FDA 21 CFR Part 880 (General
Hospital and Personal Use Devices). The software meets the definition of SaMD under
FDA's Digital Health Center of Excellence guidance. The intended pathway is 510(k)
premarket notification with a predicate device in the instrument inspection decision
support category.

**Key regulatory references:**
- FDA Guidance: "Artificial Intelligence/Machine Learning (AI/ML)-Based Software as a
  Medical Device (SaMD) Action Plan" (January 2021)
- FDA Guidance: "Software as a Medical Device (SaMD): Clinical Evaluation" (December 2017)
- FDA 21 CFR Part 820: Quality System Regulation
- FDA 21 CFR Part 11: Electronic Records and Signatures

### 2.2 ISO 14971 Risk Management Alignment

LumenAI's risk management program follows ISO 14971:2019 (Application of Risk Management
to Medical Devices). A Hazard Analysis has been conducted identifying six primary hazard
classes (see Clinical Safety Review document). Risk control measures include:
- Sensitivity thresholds (≥95% recall on critical findings)
- Mandatory technician review and sign-off workflow
- UI disclosure: "AI-assisted, not definitive"
- Immutable audit logging of all AI findings and overrides

### 2.3 IEC 62304 Software Lifecycle Alignment

Software development follows IEC 62304:2006+AMD1:2015 (Medical Device Software — Software
Life Cycle Processes). LumenAI is classified as Software Safety Class B (serious injury
possible if software fails). Key compliance activities:
- Software requirements specification (SRS) maintained per milestone
- Verification and validation (V&V) testing suite (1,053+ tests)
- Configuration management via Git with branch protection
- Defect tracking and traceability

### 2.4 AAMI TIR45 AI/ML Guidance Alignment

AAMI TIR45:2012 (Guidance on the Use of Agile Practices in the Development of Medical
Device Software) and the AAMI AI/ML working group guidance inform LumenAI's approach to:
- Iterative model validation with defined re-validation triggers
- Transparency of AI model performance to end users
- Human factors considerations in AI-assisted workflows
- Post-market performance monitoring (drift detection via PSI/CSI metrics)

---

## 3. Validation Objectives

### Primary Objective
AI inspection finding agreement with expert human reviewers (SPD educators) achieves
**Cohen's kappa ≥ 0.80** (strong agreement per Landis & Koch classification).

### Secondary Objectives
- **Sensitivity (recall) for critical findings ≥ 95%** (crack, corrosion, insulation damage)
- **Specificity ≥ 80%** across all finding categories
- **Precision ≥ 85%** overall (operational threshold for SPD workflow acceptance)

### Safety Objective
- **False Negative (FN) rate for critical findings ≤ 2%**
  Critical findings: crack, insulation damage, corrosion
  Rationale: These findings are directly linked to patient safety (SSI risk, burns,
  instrument failure during procedure).

---

## 4. Study Design

### 4.1 Multi-Site Reader Study

- **Sites:** Minimum 3 hospital SPD sites (geographically and operationally diverse)
- **Site selection criteria:** ≥50 instrument inspections/day, accredited SPD program,
  IRB or Quality Assurance committee approval
- **Study duration:** 12 weeks data collection per site

### 4.2 Blinded Evaluation

- Human readers review cases without knowledge of AI findings
- AI system evaluated on same case set without access to human annotations
- No cross-contamination: readers do not see other readers' assessments until after
  ground truth is established
- Study coordinator enforces blinding protocol; violations logged and adjudicated

### 4.3 Stratified Sampling by Finding Category

- Cases stratified across 12 finding categories to ensure adequate representation
- Prevalence matching: case mix reflects real SPD encounter rates
  (contamination findings more prevalent than structural findings)
- Minimum 100 positive and 100 negative examples per category in validation set

### 4.4 Ground Truth: Consensus Panel

- 3 independent SPD Educators (CS educator certification required)
- Ground truth = majority vote (2 of 3 agree)
- Disagreements adjudicated by Clinical Validation Committee (CVC) chair
- All ground truth decisions documented with rationale

---

## 5. Endpoints

### 5.1 Primary Endpoint
- **Overall finding agreement:** Cohen's kappa ≥ 0.80 between AI and ground truth
- Analysis: Per-case agreement across all 12 finding categories

### 5.2 Secondary Endpoints
- **Per-category sensitivity:** TP / (TP + FN) for each of 12 categories
- **Per-category specificity:** TN / (TN + FP) for each of 12 categories
- **AI vs. senior technician non-inferiority:** One-sided test, AI not inferior to
  senior CRCST technician at δ = 5% margin

### 5.3 Safety Endpoint
- **Critical finding FN rate:** FN / (FN + TP) for crack + corrosion + insulation combined
- Upper bound must be ≤ 2% with 95% confidence (Wilson CI upper bound ≤ 2%)

---

## 6. Acceptance Thresholds

| Metric | Threshold | Rationale |
|--------|-----------|-----------|
| Overall kappa | ≥ 0.80 | Strong agreement (Landis & Koch) |
| Critical finding sensitivity | ≥ 95% | Patient safety |
| Specificity | ≥ 80% | Workflow efficiency |
| FN rate (critical) | ≤ 2% | Risk-based (ISO 14971 ALARP) |
| Precision | ≥ 85% | Operational threshold |
| Per-category kappa | ≥ 0.70 | Substantial agreement minimum |

**Decision rule:** All thresholds must be met for study success. Failure of the safety
endpoint (critical FN rate > 2%) is a stop-study criterion requiring immediate model
remediation and CVC review before re-initiation.

---

## 7. Governance

### 7.1 Clinical Validation Committee (CVC)

The CVC provides independent oversight of the validation program:
- **Chair:** Medical Director or equivalent (physician or PhD-level clinical scientist)
- **Members:** Lead SPD Educator, Infection Prevention Specialist, Biomedical Engineer,
  Regulatory Affairs Lead, LumenAI Clinical AI Lead
- **Meetings:** Monthly during study; ad hoc for safety events
- **Authority:** Stop-study decisions, protocol deviations, endpoint interpretation

### 7.2 IRB/Ethics Review

IRB review required if:
- Cases include patient-identifiable information (PI)
- Staff are identifiable as study participants
- Hospital data is used beyond quality improvement

Instrument images with no patient linkage and anonymized metadata may qualify for
IRB waiver (quality improvement / device validation exemption). Hospital legal/compliance
review required at each site.

### 7.3 Change Control Process for Model Updates

Any update to the CV model (weights, architecture, preprocessing, confidence thresholds)
requires:
1. Change impact assessment (Clinical AI Lead + Engineering)
2. Regression testing (full 1,053+ test suite must pass)
3. Mini-validation: 200-case subset re-validation before production deployment
4. CVC sign-off for major updates (architecture change, new finding category)
5. Full re-validation for changes that cross re-validation triggers

### 7.4 Revalidation Triggers

Full re-validation required when:
- Performance drift > 5% on any primary metric (PSI > 0.2 or CSI > 0.15)
- New finding categories added to the CV model
- Major model architecture update (new backbone, training paradigm)
- Change in intended use or clinical setting
- Post-market adverse event linked to AI finding error
- 24 months since last full validation (scheduled re-validation)

---

## 8. Timeline

| Milestone | Target Date | Deliverable |
|-----------|-------------|-------------|
| Protocol finalization | M+0 | Signed CVP and study protocol |
| Site selection & IRB | M+1 to M+2 | Site agreements, IRB approvals |
| Case set assembly | M+2 to M+3 | Validation dataset (≥3,600 images) |
| Annotation & ground truth | M+3 to M+5 | Annotated dataset with consensus GT |
| Reader study execution | M+5 to M+8 | Case evaluations from all readers |
| Statistical analysis | M+8 to M+9 | SAP-defined analyses complete |
| Clinical Performance Report | M+9 to M+10 | Draft CPR for CVC review |
| CVC final review | M+10 | CVC sign-off or remediation |
| Regulatory submission package | M+11 to M+12 | 510(k) submission ready |

---

## 9. Roles & Responsibilities

| Role | Responsibility |
|------|---------------|
| CVC Chair | Protocol approval, endpoint adjudication, stop-study decisions |
| Clinical AI Validation Lead | Day-to-day study coordination, data integrity, report authorship |
| SPD Educator (GT panel) | Ground truth determination, annotation adjudication |
| Site Coordinator (per site) | Reader recruitment, case administration, blinding enforcement |
| Biostatistician | SAP execution, sample size verification, CI calculations |
| Regulatory Affairs Lead | 510(k) package preparation, FDA correspondence |
| LumenAI Engineering | AI system operation, data export, bug remediation |
| IRB | Ethics oversight (per-site) |

---

## 10. Document Control

| Field | Value |
|-------|-------|
| Document ID | LUM-CVP-001 |
| Version | 1.0 |
| Status | Draft — Pending CVC Review |
| Author | Clinical AI Validation Lead |
| Reviewers | CVC Members |
| Classification | CONFIDENTIAL — Clinical Use Only |
| Retention | 10 years minimum (FDA 21 CFR Part 820.180) |
| Change history | v1.0: Initial draft (P12 milestone) |

**Distribution:** CVC members, Regulatory Affairs, LumenAI Executive Team only.
Not for external distribution without written authorization from the CVC Chair.
