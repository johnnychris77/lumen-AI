# Clinical Evidence Package
**LumenAI SPD Intelligence Platform** | CEP-LUM-001 | Version 1.0-DRAFT
**Status**: In Review | **Classification**: Regulatory Confidential
**Subject to regulatory counsel and clinical review before any FDA submission.**
**IMPORTANT: Current validation data is simulated (seeded mock). This package represents the evidence organization framework; real-world validation is required before submission.**

---

## 1. Executive Summary

LumenAI's Computer Vision Detection module (Module A) has been evaluated in a simulated multi-reader multi-case (MRMC) reader study framework developed during Milestone P12 (Clinical Validation). The primary endpoint for FDA submission is Cohen's kappa ≥ 0.80 comparing AI performance to an expert human panel.

**Current status**: Seeded mock performance data shows overall kappa of approximately 0.79 — marginally below the 0.80 primary threshold, with 95% confidence interval overlapping the threshold. This is insufficient for FDA submission.

**Clinical program requirement**: A real-world validation study using actual instrument images from operational SPD departments is required before any regulatory submission. This package documents the evidence structure, study design, current gaps, and pre-submission requirements.

---

## 2. Regulatory Context

This clinical evidence package is prepared in anticipation of a 510(k) Premarket Notification submission for Module A (Computer Vision Detection). The package addresses FDA's requirements for:
- Performance testing of AI/ML-based SaMD (per FDA AI/ML Action Plan)
- Substantial equivalence demonstration to predicate device
- Clinical study data supporting the intended use claims
- Evidence of human-in-the-loop design

---

## 3. Validation Study Design (Reference P12 Artifacts)

### 3.1 Study Type
Multi-reader multi-case (MRMC) reader study, simulated environment

### 3.2 Reader Panel Composition (Simulated)
| Role | Count | Experience Level |
|------|-------|-----------------|
| SPD Technicians (Entry-Level) | 7 | 0–2 years |
| SPD Technicians (Senior) | 7 | 2+ years, CRCST |
| SPD Educators | 7 | 3+ years |
| SPD Managers | 7 | 5+ years |
| Infection Prevention Specialists | 7 | CIC certified |
| **Total** | **35** | — |

### 3.3 Finding Categories (12)
1. Blood residue
2. Bone fragments
3. Tissue residue
4. Chemical/cleaning residue
5. Corrosion
6. Crack/fracture
7. Pitting
8. Insulation damage (robotic instruments)
9. Barcode failure
10. UDI failure
11. QR code failure
12. KeyDot identification failure

### 3.4 Primary Endpoint
**Cohen's kappa (κ) ≥ 0.80** — inter-rater agreement between AI system and expert human panel

### 3.5 Secondary Endpoints
- Sensitivity per finding category (target ≥ 0.80)
- Specificity per finding category (target ≥ 0.85)
- Area Under the ROC Curve (AUC) per category
- False positive rate (FPR) per category
- False negative rate (FNR) per category
- Time-to-review (workflow efficiency)

### 3.6 Statistical Methodology
- Cohen's kappa with Wilson 95% confidence intervals
- Per-category analysis with Bonferroni correction for multiple comparisons
- MRMC analysis using Obuchowski-Rockette (OR) method
- Minimum sample size: N ≥ 200 cases per primary analysis (P12 framework)
- Power target: 80% power to detect kappa ≥ 0.80 with α = 0.05

### 3.7 P12 Validation Artifacts (Supporting Evidence)
| Artifact | Location | Status |
|---------|----------|--------|
| Clinical Validation Plan | docs/clinical/clinical-validation-plan.md | Complete |
| Human vs AI Study Protocol | docs/clinical/human-vs-ai-study-protocol.md | Complete |
| Validation Dataset Specification | docs/clinical/validation-dataset-specification.md | Complete |
| Clinical Performance Report | docs/clinical/clinical-performance-report.md | Complete (seeded) |
| Sealed Test Set Protocol | docs/clinical/sealed-test-set-protocol.md | Complete |
| IEC 62304 V&V Trace Matrix | docs/clinical/iec62304-vv-trace-matrix.md | Complete |
| Baseline Validation Protocol | docs/clinical/baseline-validation-protocol.md | Complete |
| Clinical Safety Review | docs/clinical/clinical-safety-review.md | Complete |

---

## 4. Performance Results Summary (Simulated Mock Data)

**CRITICAL DISCLAIMER**: The performance figures below are derived from seeded mock data generated for software testing and regulatory framework development. They do NOT represent performance on real clinical instrument images. These figures must NOT be submitted to FDA or used in marketing materials.

### 4.1 Overall Performance (Seeded Mock)

| Metric | Value | 95% CI | Threshold | Status |
|--------|-------|--------|-----------|--------|
| Overall Cohen's kappa | ~0.79 | [0.74, 0.84] | ≥ 0.80 | MARGINAL — CI overlaps threshold |
| Overall Sensitivity | ~0.81 | [0.77, 0.85] | ≥ 0.80 | Marginal |
| Overall Specificity | ~0.87 | [0.83, 0.91] | ≥ 0.85 | Marginal |
| Overall AUC | ~0.84 | [0.80, 0.88] | ≥ 0.80 | Marginal |

### 4.2 Per-Category Performance (Reference clinical-performance-report.md)

Performance by category is documented in detail in docs/clinical/clinical-performance-report.md. Summary:
- Blood residue: highest performance category (~0.82 kappa)
- Bone fragments: high performance (~0.81 kappa)
- Tissue residue: moderate (~0.78 kappa)
- Chemical residue: lowest performance (~0.74 kappa) — below individual threshold
- Structural defects (crack, pitting, corrosion): moderate (~0.77–0.80 kappa)
- Identification categories (barcode, UDI, QR, KeyDot): variable (~0.80–0.88 kappa)

### 4.3 False Negative Analysis

False negatives (missed findings) are the primary safety concern. Per seeded mock analysis:
- FNR for blood residue: ~12% (before human confirmation step)
- FNR reduction with human confirmation: estimated 60–80% (human review catches AI misses)
- Net FNR estimate with human-in-the-loop: ~3–5%

Note: These estimates require real-world validation. Human review effectiveness varies significantly by user experience, attention state, and viewing conditions.

---

## 5. Study Limitations

1. **Simulated data only**: All current performance data is derived from seeded mock images generated for software testing. No real clinical instrument images have been used.
2. **No real patients or instruments**: The study framework has not been executed with actual SPD departments or real instrument samples.
3. **Performance may vary by**: instrument type, manufacturer, image quality, lighting conditions, camera hardware, image capture technique, user experience level.
4. **Kappa below primary threshold**: Even the simulated data does not consistently achieve the ≥ 0.80 primary endpoint. Additional algorithm development or threshold adjustment is required.
5. **Single simulated site**: No multi-site variability assessment.
6. **No temporal validation**: No assessment of performance over time (model drift).
7. **No adversarial testing**: No stress testing with edge-case, artificially degraded, or adversarial images.

---

## 6. Clinical Evidence Gaps (Pre-Submission Requirements)

The following gaps must be addressed before any FDA submission. These represent the clinical critical path.

### Gap 1: Real-World Clinical Validation Study
**Description**: Execute the P12 MRMC study framework using real instrument images from operational SPD departments.
**Requirement**: N ≥ 500 cases per finding category; or statistical justification for lower N with equivalent power
**Timeline**: 12–18 months (site identification, IRB/QA process, data collection, analysis)
**Owner**: Clinical Validation Lead + contracted CRO
**Reference**: docs/clinical/clinical-validation-plan.md

### Gap 2: Multi-Site Validation
**Description**: Validation must include images from minimum 3 geographically and operationally distinct facilities.
**Rationale**: Single-site data may not generalize to different instrument sets, camera hardware, lighting, or workflow practices.
**Timeline**: Concurrent with Gap 1
**Owner**: Clinical Validation Lead

### Gap 3: Prospective Real-World Evidence (RWE)
**Description**: Post-validation prospective data collection from enrolled facilities per docs/clinical/real-world-evidence-plan.md (P15 program).
**Requirement**: Minimum 6 months prospective data; kappa-monitor trending
**Timeline**: Concurrent with/after Gap 1
**Owner**: Clinical Operations Lead

### Gap 4: Sealed Test Set Performance ≥ 0.80
**Description**: Primary endpoint must be demonstrated on the sealed (held-out) test set per docs/clinical/sealed-test-set-protocol.md.
**Requirement**: Overall kappa ≥ 0.80 on sealed test set; per-category analysis
**Timeline**: After training data collection and model refinement
**Owner**: AI Engineering Lead + Clinical Validation Lead

### Gap 5: Human Factors Validation Study
**Description**: Summative human factors study demonstrating safe use by intended user population.
**Requirement**: ≤ 10% critical use error rate; 15 users per critical role per ANSI/AAMI HE75
**Timeline**: Concurrent with Gap 1; 6 months
**Owner**: Human Factors Lead
**Reference**: docs/regulatory/human-factors-validation-plan.md

### Gap 6: Multi-Reader Generalization
**Description**: Performance must be demonstrated across all 5 intended user role types, not just senior technicians.
**Requirement**: Kappa ≥ 0.75 per role group (senior technicians may perform better; entry-level may not)
**Timeline**: Part of Gap 1 study design

---

## 7. Pre-Submission Clinical Strategy

### 7.1 Algorithm Improvement Plan (Before Real-World Study)
1. Expand training data with additional synthetic and augmented images for low-performing categories (chemical residue, tissue)
2. Tune confidence thresholds to optimize kappa for targeted categories
3. Consider ensemble approach for categories below 0.80 threshold
4. Validate improvements on internal held-out set before initiating clinical study

### 7.2 Real-World Study Execution Plan
1. Identify 3–5 academic medical centers or large community hospitals with active SPD research programs
2. Establish data use agreements and IRB/quality assurance review
3. Collect de-identified instrument images with expert annotation ground truth
4. Execute MRMC study per docs/clinical/human-vs-ai-study-protocol.md
5. Conduct sealed test set evaluation per docs/clinical/sealed-test-set-protocol.md
6. Submit clinical performance report to regulatory counsel for review

### 7.3 FDA Engagement Strategy
1. Submit Q-Submission (Pre-Sub) request to discuss study design before initiation
2. Provide FDA proposed study protocol for feedback
3. Incorporate FDA feedback into final protocol
4. Conduct study per FDA-reviewed protocol

---

## 8. Reference to P12 Validation Framework

The following P12 documents constitute the clinical evidence framework and are incorporated by reference:

| Document | Key Content | Submission Role |
|----------|-------------|----------------|
| clinical-validation-plan.md | Study design, endpoints, statistical plan | Clinical study protocol |
| human-vs-ai-study-protocol.md | MRMC reader study protocol | FDA study report basis |
| validation-dataset-specification.md | Dataset curation, annotation standards | Data quality evidence |
| clinical-performance-report.md | Performance results (currently seeded mock) | Primary clinical evidence (upon real data) |
| sealed-test-set-protocol.md | Sealed test set methodology | Independent validation |
| iec62304-vv-trace-matrix.md | Software V&V traceability | Software documentation |
| real-world-evidence-plan.md | Post-market RWE program | Post-market surveillance evidence |
| 510k-predicate-analysis.md | Predicate device analysis | Substantial equivalence argument |
| clinical-safety-review.md | Safety analysis | Benefit-risk documentation |

---

## 9. Evidence Package Completeness Assessment

| Evidence Category | Status | Gap |
|------------------|--------|-----|
| Study design & protocol | Complete (framework) | Real-world execution needed |
| Reader panel definition | Complete (framework) | Actual panel recruitment needed |
| Statistical methodology | Complete | — |
| Seeded mock results | Complete | Not for submission; illustrative only |
| Real-world performance data | Not initiated | Critical gap |
| Multi-site data | Not initiated | Critical gap |
| Sealed test set results | Not initiated | Critical gap |
| Human factors study | Not initiated | Critical gap |
| Predicate device confirmation | In progress | See 510k-predicate-search-log.md |
| RWE program baseline | Not initiated | Post-submission requirement |

**Overall Clinical Evidence Readiness: NOT READY FOR SUBMISSION**

Estimated time to clinical evidence readiness: 18–24 months with dedicated clinical research resources.

---

*Document Owner: Clinical Validation Lead | Review Cycle: Quarterly*
*This document contains preliminary estimates from simulated data. It does not constitute clinical evidence for regulatory submission.*
