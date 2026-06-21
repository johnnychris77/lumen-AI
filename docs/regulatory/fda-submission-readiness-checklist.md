# FDA Submission Readiness Checklist
LumenAI Surgical Instrument Inspection Software | Version 1.0
**Subject to regulatory counsel review. This checklist does not constitute regulatory advice.**
**LumenAI does not claim FDA clearance. This document supports preparation for a future submission.**

Status Legend: Complete | In Progress | Not Started

---

## Section 1: Regulatory Strategy

| Item | Status | Evidence / Notes |
|------|--------|-----------------|
| 1.1 Regulatory pathway selected (510(k), De Novo, or PMA) | In Progress | Preliminary: 510(k) for CV Detection module; awaiting counsel confirmation |
| 1.2 Predicate device(s) identified for 510(k) | In Progress | Preliminary candidates in docs/clinical/510k-predicate-analysis.md; substantial equivalence analysis pending |
| 1.3 Qualified regulatory counsel engaged | Not Started | Required before Q-Sub or submission |
| 1.4 Pre-Submission (Q-Sub) meeting with FDA requested | Not Started | Target: Q2 2026 |
| 1.5 Module classification (Device vs. Non-Device CDS) determined | In Progress | Preliminary assessment in docs/regulatory/samd-classification-assessment.md |
| 1.6 PCCP strategy defined | In Progress | Draft in docs/regulatory/ai-ml-change-control-plan.md; requires counsel review |
| 1.7 International regulatory strategy (EU MDR, Health Canada, TGA) | Not Started | Out of scope for V1.0 submission |

---

## Section 2: Intended Use

| Item | Status | Evidence / Notes |
|------|--------|-----------------|
| 2.1 Intended use statement finalized | In Progress | Draft in docs/regulatory/intended-use-and-claims-boundary.md; requires counsel review |
| 2.2 Indications for use statement drafted | In Progress | Derived from intended use; requires formal drafting for submission |
| 2.3 Claims boundary documented | Complete | docs/regulatory/intended-use-and-claims-boundary.md Section 7 |
| 2.4 Excluded uses documented | Complete | docs/regulatory/intended-use-and-claims-boundary.md Section 6 |
| 2.5 Human-in-the-loop requirement documented | Complete | docs/regulatory/intended-use-and-claims-boundary.md Section 8 |
| 2.6 Intended user population defined | Complete | docs/regulatory/intended-use-and-claims-boundary.md Section 3 |
| 2.7 Intended environment defined | Complete | docs/regulatory/intended-use-and-claims-boundary.md Section 4 |

---

## Section 3: Device Description

| Item | Status | Evidence / Notes |
|------|--------|-----------------|
| 3.1 Device function description | Complete | docs/regulatory/software-lifecycle-readiness.md Section 1 |
| 3.2 Software architecture documented | Complete | docs/regulatory/software-lifecycle-readiness.md Section 1 |
| 3.3 Hardware/operating environment specified | Complete | docs/regulatory/software-lifecycle-readiness.md Section 1.3 |
| 3.4 Module descriptions (A through H) | Complete | docs/regulatory/samd-classification-assessment.md Section 2 |
| 3.5 External interfaces documented | Complete | docs/regulatory/software-lifecycle-readiness.md Section 1.3 |
| 3.6 SOUP list complete | Complete | docs/regulatory/software-lifecycle-readiness.md Section 11 |

---

## Section 4: Risk Management

| Item | Status | Evidence / Notes |
|------|--------|-----------------|
| 4.1 Risk management plan documented | Complete | docs/regulatory/risk-management-file.md Section 1 |
| 4.2 Hazard identification complete (all modules) | Complete | docs/regulatory/risk-management-file.md — 12 hazards analyzed |
| 4.3 Risk acceptability policy defined | Complete | docs/regulatory/risk-management-file.md Section 2 |
| 4.4 Risk controls implemented for all unacceptable risks | Complete | All risks reduced to Acceptable (RPN 1-6) |
| 4.5 Residual risk evaluation complete | Complete | docs/regulatory/risk-management-file.md Section 4 |
| 4.6 Overall benefit-risk determination | Complete | docs/regulatory/risk-management-file.md Section 4.2 |
| 4.7 Post-market surveillance signals defined | Complete | docs/regulatory/risk-management-file.md Section 5 |
| 4.8 Risk management file approved by team | Not Started | Requires team signatures before submission |
| 4.9 Cybersecurity risks integrated into risk file | Complete | H-03 (unauthorized access); H-07 (audit log); H-11 (configuration) |

---

## Section 5: Software Documentation

| Item | Status | Evidence / Notes |
|------|--------|-----------------|
| 5.1 IEC 62304 safety classification documented | Complete | docs/regulatory/software-lifecycle-readiness.md Section 2 |
| 5.2 Software requirements specification | Complete | REQ-001 through REQ-020; traced in traceability-matrix.md |
| 5.3 Software architecture description | Complete | docs/regulatory/software-lifecycle-readiness.md Section 1 |
| 5.4 Detailed software design (unit level) | In Progress | Code-level design in repository; formal design document pending |
| 5.5 Software unit implementation and verification | Complete | 1,163 passing tests; ruff passing |
| 5.6 Software integration and testing | Complete | Integration tests in pytest suite |
| 5.7 Software system testing | Complete | API and end-to-end tests in pytest suite |
| 5.8 Traceability (requirements to tests) | Complete | docs/regulatory/traceability-matrix.md |
| 5.9 SOUP list (all third-party components) | Complete | docs/regulatory/software-lifecycle-readiness.md Section 11 |
| 5.10 Revision level history | Complete | Git history + CHANGELOG |
| 5.11 Known anomalies (defects) list | In Progress | DEF-001, DEF-002 from P12; GitHub Issues tracking |
| 5.12 Unresolved anomalies justification | In Progress | Required for submission; pending final defect review |

---

## Section 6: AI/ML Documentation

| Item | Status | Evidence / Notes |
|------|--------|-----------------|
| 6.1 Algorithm description (architecture, inputs, outputs) | Complete | docs/regulatory/ai-ml-change-control-plan.md Section 2; software-lifecycle-readiness.md Section 1 |
| 6.2 Training data description | Complete | docs/clinical/validation-dataset-specification.md |
| 6.3 Training methodology | In Progress | Training protocol document pending formalization |
| 6.4 Performance metrics defined | Complete | docs/regulatory/clinical-evidence-summary.md Section 4 |
| 6.5 Locked model confirmation | Complete | docs/regulatory/ai-ml-change-control-plan.md Section 2 |
| 6.6 PCCP drafted | In Progress | docs/regulatory/ai-ml-change-control-plan.md Section 7; requires counsel review |
| 6.7 Drift detection plan | Complete | docs/regulatory/ai-ml-change-control-plan.md Section 5 |
| 6.8 Model update control plan | Complete | docs/regulatory/ai-ml-change-control-plan.md |
| 6.9 Dataset versioning and integrity controls | Complete | docs/regulatory/ai-ml-change-control-plan.md Section 3.2 |
| 6.10 Bias analysis (subgroup performance) | In Progress | Preliminary in clinical-performance-report.md; live study required |

---

## Section 7: Cybersecurity

| Item | Status | Evidence / Notes |
|------|--------|-----------------|
| 7.1 Threat model (STRIDE) | Complete | docs/clinical/cybersecurity-threat-model.md |
| 7.2 Security architecture documented | Complete | docs/regulatory/cybersecurity-readiness.md Section 3 |
| 7.3 SBOM generation process | Complete | CycloneDX in GitHub Actions deploy.yml |
| 7.4 Vulnerability management program | Complete | docs/regulatory/cybersecurity-readiness.md Section 5 |
| 7.5 Patch management timeline | Complete | docs/regulatory/cybersecurity-readiness.md Section 8 |
| 7.6 Penetration test results | Not Started | Planned Q2 2026 |
| 7.7 DAST results | Not Started | Planned Q2 2026 |
| 7.8 Container image scanning in CI | Not Started | Planned Q1 2026 |
| 7.9 Cybersecurity labeling elements | Complete | docs/regulatory/cybersecurity-readiness.md Section 9 |
| 7.10 Incident response plan | Complete | docs/regulatory/cybersecurity-readiness.md Section 7; P11 reliability docs |
| 7.11 FDA 2023 cybersecurity guidance checklist | In Progress | docs/regulatory/cybersecurity-readiness.md covers main elements; formal gap analysis pending |

---

## Section 8: Clinical Evidence

| Item | Status | Evidence / Notes |
|------|--------|-----------------|
| 8.1 Validation dataset specification | Complete | docs/clinical/validation-dataset-specification.md |
| 8.2 Clinical validation plan | Complete | docs/clinical/clinical-validation-plan.md |
| 8.3 Reader study protocol | Complete | docs/clinical/human-vs-ai-study-protocol.md |
| 8.4 Baseline validation protocol | Complete | docs/clinical/baseline-validation-protocol.md |
| 8.5 Performance data collected (mock) | Complete | docs/clinical/clinical-performance-report.md |
| 8.6 Live reader study completed | Not Started | Target Q3 2026 — REQUIRED before submission |
| 8.7 Sealed test set evaluation | Not Started | Target Q4 2026 — REQUIRED before submission |
| 8.8 Usability study (IEC 62366) | Not Started | Target Q2 2026 — REQUIRED before submission |
| 8.9 Clinical evidence summary | Complete | docs/regulatory/clinical-evidence-summary.md |
| 8.10 Primary endpoint (kappa >=0.80) met | In Progress | Currently 0.79 (mock); live study determinative |
| 8.11 Subgroup analysis (critical findings) | Complete | docs/regulatory/clinical-evidence-summary.md Section 4.2 |
| 8.12 Real-world evidence enrollment | Not Started | Begins at commercial launch |

---

## Section 9: Labeling

| Item | Status | Evidence / Notes |
|------|--------|-----------------|
| 9.1 Intended use statement (label text) | In Progress | Draft in docs/regulatory/user-labeling-and-instructions.md |
| 9.2 Indications for use (label text) | In Progress | To be derived from intended use with counsel review |
| 9.3 Warnings documented | Complete | docs/regulatory/user-labeling-and-instructions.md Warnings section |
| 9.4 Instructions for use (IFU) | Complete | docs/regulatory/user-labeling-and-instructions.md |
| 9.5 Contraindications | Complete | docs/regulatory/user-labeling-and-instructions.md Section 4 |
| 9.6 Image quality requirements | Complete | docs/regulatory/user-labeling-and-instructions.md Section 5 |
| 9.7 Cybersecurity labeling | Complete | docs/regulatory/cybersecurity-readiness.md Section 9.2 |
| 9.8 Symbols defined (ISO 15223 / ANSI/AAMI) | In Progress | Abbreviated list in IFU Section 15; full symbol glossary pending |
| 9.9 Electronic labeling compliance | In Progress | eIFU approach to be determined with counsel |
| 9.10 Labeling review by qualified counsel | Not Started | Required before finalization |

---

## Section 10: Traceability

| Item | Status | Evidence / Notes |
|------|--------|-----------------|
| 10.1 Requirements to hazards traceability | Complete | docs/regulatory/traceability-matrix.md |
| 10.2 Requirements to design artifacts traceability | Complete | docs/regulatory/traceability-matrix.md |
| 10.3 Requirements to tests traceability | Complete | docs/regulatory/traceability-matrix.md |
| 10.4 Requirements to validation evidence traceability | Complete | docs/regulatory/traceability-matrix.md |
| 10.5 Risk controls to verification evidence traceability | Complete | docs/regulatory/risk-management-file.md (Verification Evidence column) |
| 10.6 Full Design History File (DHF) compiled | In Progress | Documents exist; formal DHF compilation and index pending |

---

## Section 11: Test Evidence

| Item | Status | Evidence / Notes |
|------|--------|-----------------|
| 11.1 Automated test suite passing | Complete | 1,163 tests passing; pytest |
| 11.2 Ruff (static analysis) passing | Complete | Zero violations |
| 11.3 Frontend build passing | Complete | npm run build success |
| 11.4 Load test results | Not Started | Planned Q1 2026; K6 or Locust |
| 11.5 Security scan (automated) | In Progress | Dependabot active; DAST pending |
| 11.6 Penetration test | Not Started | Planned Q2 2026 |
| 11.7 SBOM clean (no critical vulnerabilities) | In Progress | Dependabot monitoring; periodic manual review |
| 11.8 Test results archived (7 years) | In Progress | GitHub Actions artifacts; S3 archival setup pending |

---

## Section 12: Post-Market Plan

| Item | Status | Evidence / Notes |
|------|--------|-----------------|
| 12.1 Real-world evidence enrollment plan | Complete | docs/clinical/real-world-evidence-plan.md |
| 12.2 Drift monitoring plan | Complete | docs/regulatory/ai-ml-change-control-plan.md Section 5 |
| 12.3 Adverse event reporting process (MDR) | In Progress | Process defined in cybersecurity-readiness.md; formal MDR SOP pending |
| 12.4 Annual post-market report plan | In Progress | Described in ai-ml-change-control-plan.md Section 11; formal plan pending |
| 12.5 Customer complaint handling | Not Started | SOP required |
| 12.6 Recall procedure | Not Started | SOP required |
| 12.7 Post-market surveillance signals defined | Complete | docs/regulatory/risk-management-file.md Section 5 |

---

## Section 13: Quality System

| Item | Status | Evidence / Notes |
|------|--------|-----------------|
| 13.1 Design History File (DHF) | In Progress | Components exist (P0-P13 docs); formal DHF index pending |
| 13.2 Change control process | Complete | docs/regulatory/software-lifecycle-readiness.md Section 8; ai-ml-change-control-plan.md |
| 13.3 Configuration management | Complete | docs/regulatory/software-lifecycle-readiness.md Section 7.3 |
| 13.4 Supplier/SOUP management | Complete | docs/regulatory/software-lifecycle-readiness.md Section 11 |
| 13.5 Training records management | In Progress | System tracks completion; formal SOP pending |
| 13.6 Document control | In Progress | Git version control; formal document control SOP pending |
| 13.7 Quality Management System (ISO 13485) assessment | Not Started | Formal QMS assessment required for 510(k) |

---

## Section 14: Regulatory Counsel Review

| Item | Status | Evidence / Notes |
|------|--------|-----------------|
| 14.1 Regulatory counsel identified and engaged | Not Started | Required before any submission activity |
| 14.2 All regulatory documents reviewed by counsel | Not Started | Required before finalization |
| 14.3 Pre-Submission (Q-Sub) meeting request prepared | Not Started | Target Q2 2026 |
| 14.4 Q-Sub meeting completed | Not Started | Target Q2-Q3 2026 |
| 14.5 510(k) submission package complete | Not Started | Target Q2 2027 (subject to study completion) |

---

## Summary: Submission Readiness Assessment

| Section | Complete | In Progress | Not Started | % Complete |
|---------|---------|------------|------------|-----------|
| 1. Regulatory Strategy | 0 | 5 | 2 | 0% |
| 2. Intended Use | 5 | 2 | 0 | 71% |
| 3. Device Description | 6 | 0 | 0 | 100% |
| 4. Risk Management | 7 | 0 | 2 | 78% |
| 5. Software Documentation | 8 | 3 | 1 | 67% |
| 6. AI/ML Documentation | 6 | 3 | 1 | 60% |
| 7. Cybersecurity | 7 | 2 | 3 | 58% |
| 8. Clinical Evidence | 6 | 2 | 4 | 50% |
| 9. Labeling | 6 | 3 | 1 | 60% |
| 10. Traceability | 5 | 1 | 0 | 83% |
| 11. Test Evidence | 3 | 2 | 3 | 38% |
| 12. Post-Market Plan | 3 | 2 | 2 | 43% |
| 13. Quality System | 3 | 3 | 1 | 43% |
| 14. Regulatory Counsel | 0 | 0 | 5 | 0% |

**Overall Readiness**: Approximately 55% of submission requirements complete. Critical gaps are in live clinical evidence (Section 8), regulatory counsel engagement (Section 14), and formal quality system documentation (Section 13).

**Priority Actions Before 510(k) Submission**:
1. Engage qualified regulatory counsel (immediate)
2. Request Pre-Submission (Q-Sub) meeting with FDA (Q2 2026)
3. Execute usability study — IEC 62366 (Q2 2026)
4. Complete external penetration test (Q2 2026)
5. Execute live MRMC reader study (Q3 2026)
6. Complete sealed test set evaluation (Q4 2026)
7. Compile formal Design History File index (Q1 2027)
8. Formalize QMS per ISO 13485 (Q1 2027)
