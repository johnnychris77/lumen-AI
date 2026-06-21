# Design History File (DHF) Index
**LumenAI SPD Intelligence Platform** | Version 1.0-RC | DHF-001
**Status**: In Progress | **Last Updated**: 2026-06-21
**Subject to regulatory counsel review before submission.**

---

## Overview

This Design History File Index catalogs all records that comprise the LumenAI design history per 21 CFR 820.30(j) and ISO 13485:2016 Section 7.3.10. Each entry specifies document location, current status, last update date, and review status.

**Status Definitions**:
- **Complete** — Document exists and has been reviewed
- **In Progress** — Document exists in draft form; review pending
- **Planned** — Document planned; not yet created
- **Gap** — Required document; gap identified; remediation required before submission

---

## Section 1: User Needs & Intended Use

| Document Title | Location | Status | Last Updated | Review Status |
|---------------|----------|--------|--------------|---------------|
| Intended Use Statement | docs/regulatory/submission-strategy.md | Complete | 2026-06-21 | Pending Sign-Off |
| User Population Definition | docs/regulatory/submission-strategy.md | Complete | 2026-06-21 | Pending Sign-Off |
| Indications for Use Statement | docs/regulatory/submission-strategy.md | Complete | 2026-06-21 | Pending Sign-Off |
| Claim Boundaries (In/Out Scope) | docs/regulatory/intended-use-and-claims-boundary.md | Complete | 2026-06-21 | Pending Sign-Off |
| Stakeholder Requirements | docs/regulatory/software-requirements-specification.md | In Progress | 2026-06-21 | Not Started |
| Voice of Customer Inputs | docs/commercial/roi-model.md | In Progress | — | Not Started |
| Human Review Requirements | docs/regulatory/submission-strategy.md §5 | Complete | 2026-06-21 | Pending Sign-Off |

---

## Section 2: Software Requirements

| Document Title | Location | Status | Last Updated | Review Status |
|---------------|----------|--------|--------------|---------------|
| Software Requirements Specification | docs/regulatory/software-requirements-specification.md | Complete | 2026-06-21 | Pending Sign-Off |
| API Requirements | docs/regulatory/software-architecture-package.md | Complete | 2026-06-21 | Pending Sign-Off |
| Security Requirements | docs/regulatory/cybersecurity-readiness.md | Complete | 2026-06-21 | Pending Sign-Off |
| Integration Requirements | docs/integrations/healthcare-quality-safety-ecosystem.md | In Progress | — | Not Started |
| Performance Requirements (kappa ≥ 0.80) | docs/regulatory/software-requirements-specification.md §A | Complete | 2026-06-21 | Pending Sign-Off |
| Mobile/Offline Requirements | docs/regulatory/software-requirements-specification.md §I | Complete | 2026-06-21 | Pending Sign-Off |

---

## Section 3: Architecture & Design

| Document Title | Location | Status | Last Updated | Review Status |
|---------------|----------|--------|--------------|---------------|
| Software Architecture Package | docs/regulatory/software-architecture-package.md | Complete | 2026-06-21 | Pending Sign-Off |
| Device Master Record | docs/regulatory/device-master-record.md | Complete | 2026-06-21 | Pending Sign-Off |
| AI/ML Change Control Plan | docs/regulatory/ai-ml-change-control-plan.md | Complete | 2026-06-21 | Pending Sign-Off |
| Computer Vision Architecture (P4) | backend/app/routes/ (cv_inspection modules) | In Progress | — | Not Started |
| Database Schema (Alembic Migrations) | backend/alembic/versions/ | Complete | — | Not Started |
| Deployment Architecture (K8s) | k8s/ | Complete | — | Not Started |
| CI/CD Pipeline | .github/workflows/ | Complete | — | Not Started |
| API Route Map | docs/regulatory/software-architecture-package.md §2 | Complete | 2026-06-21 | Pending Sign-Off |

---

## Section 4: Risk Management

| Document Title | Location | Status | Last Updated | Review Status |
|---------------|----------|--------|--------------|---------------|
| Risk Management File | docs/regulatory/risk-management-file.md | Complete | 2026-06-21 | Pending Sign-Off |
| Risk Management Addendum (P19) | docs/regulatory/risk-management-addendum-p19.md | Complete | 2026-06-21 | Pending Sign-Off |
| Cybersecurity Threat Model | docs/clinical/cybersecurity-threat-model.md | Complete | — | Pending Sign-Off |
| Master Traceability Matrix | docs/regulatory/master-traceability-matrix.md | Complete | 2026-06-21 | Pending Sign-Off |
| SaMD Classification Assessment | docs/regulatory/samd-classification-assessment.md | Complete | — | Pending Sign-Off |
| Benefit-Risk Determination | docs/regulatory/risk-management-file.md §6 | In Progress | — | Not Started |

---

## Section 5: Verification & Validation

| Document Title | Location | Status | Last Updated | Review Status |
|---------------|----------|--------|--------------|---------------|
| Clinical Validation Plan | docs/clinical/clinical-validation-plan.md | Complete | — | Pending Sign-Off |
| Human vs AI Study Protocol | docs/clinical/human-vs-ai-study-protocol.md | Complete | — | Pending Sign-Off |
| Validation Dataset Specification | docs/clinical/validation-dataset-specification.md | Complete | — | Pending Sign-Off |
| Clinical Performance Report | docs/clinical/clinical-performance-report.md | Complete | — | Pending Sign-Off |
| Sealed Test Set Protocol | docs/clinical/sealed-test-set-protocol.md | Complete | — | Pending Sign-Off |
| IEC 62304 V&V Trace Matrix | docs/clinical/iec62304-vv-trace-matrix.md | Complete | — | Pending Sign-Off |
| Baseline Validation Protocol | docs/clinical/baseline-validation-protocol.md | Complete | — | Pending Sign-Off |
| Software Lifecycle Readiness | docs/regulatory/software-lifecycle-readiness.md | Complete | — | Pending Sign-Off |
| Unit/Integration Test Suite | backend/tests/ | Complete | — | CI Validated |
| Real-World Validation Study | Planned — not yet initiated | Gap | — | Not Started |
| Multi-Site Validation Study | Planned — not yet initiated | Gap | — | Not Started |

---

## Section 6: Clinical Evidence

| Document Title | Location | Status | Last Updated | Review Status |
|---------------|----------|--------|--------------|---------------|
| Clinical Evidence Package | docs/regulatory/clinical-evidence-package.md | Complete | 2026-06-21 | Pending Sign-Off |
| Clinical Evidence Summary | docs/regulatory/clinical-evidence-summary.md | Complete | — | Pending Sign-Off |
| Real World Evidence Plan | docs/clinical/real-world-evidence-plan.md | Complete | — | Pending Sign-Off |
| 510(k) Predicate Analysis | docs/clinical/510k-predicate-analysis.md | Complete | — | Pending Sign-Off |
| 510(k) Predicate Search Log | docs/regulatory/510k-predicate-search-log.md | Complete | — | Pending Sign-Off |
| Clinical Safety Review | docs/clinical/clinical-safety-review.md | Complete | — | Pending Sign-Off |
| Real-World Clinical Validation | Not yet initiated | Gap | — | Not Started |

---

## Section 7: Human Factors

| Document Title | Location | Status | Last Updated | Review Status |
|---------------|----------|--------|--------------|---------------|
| Human Factors Validation Plan | docs/regulatory/human-factors-validation-plan.md | Complete | 2026-06-21 | Pending Sign-Off |
| User Labeling and Instructions for Use | docs/regulatory/user-labeling-and-instructions.md | Complete | — | Pending Sign-Off |
| Formative Evaluation Report | Not yet initiated | Gap | — | Not Started |
| Summative Validation Report | Not yet initiated | Gap | — | Not Started |
| Use Error Risk Assessment | docs/regulatory/human-factors-validation-plan.md §5 | Complete | 2026-06-21 | Pending Sign-Off |

---

## Section 8: Cybersecurity

| Document Title | Location | Status | Last Updated | Review Status |
|---------------|----------|--------|--------------|---------------|
| Cybersecurity Submission Package | docs/regulatory/cybersecurity-submission-package.md | Complete | 2026-06-21 | Pending Sign-Off |
| Cybersecurity Readiness Assessment | docs/regulatory/cybersecurity-readiness.md | Complete | — | Pending Sign-Off |
| External Penetration Test Scope | docs/regulatory/external-pentest-scope.md | Complete | — | Pending Sign-Off |
| Cybersecurity Threat Model (STRIDE) | docs/clinical/cybersecurity-threat-model.md | Complete | — | Pending Sign-Off |
| Penetration Test Report | Not yet initiated | Gap | — | Not Started |
| SBOM (CycloneDX/SPDX) | Not yet generated | Gap | — | Not Started |
| DAST Report (OWASP ZAP) | Not yet initiated | Gap | — | Not Started |

---

## Section 9: Manufacturing & Quality System

| Document Title | Location | Status | Last Updated | Review Status |
|---------------|----------|--------|--------------|---------------|
| QMS Readiness Gap Analysis | docs/regulatory/qms-readiness-gap-analysis.md | Complete | 2026-06-21 | Pending Sign-Off |
| Software Lifecycle Readiness | docs/regulatory/software-lifecycle-readiness.md | Complete | — | Pending Sign-Off |
| Document Control SOP | Not yet initiated | Gap | — | Not Started |
| CAPA SOP | Not yet initiated | Gap | — | Not Started |
| Complaint Handling SOP | Not yet initiated | Gap | — | Not Started |
| Training Records System | Not yet initiated | Gap | — | Not Started |
| Supplier Qualification Procedure | Not yet initiated | Gap | — | Not Started |
| Management Review Records | Not yet initiated | Gap | — | Not Started |

---

## Section 10: Post-Market

| Document Title | Location | Status | Last Updated | Review Status |
|---------------|----------|--------|--------------|---------------|
| Post-Market Surveillance Plan | docs/regulatory/post-market-surveillance-plan.md | Complete | — | Pending Sign-Off |
| Predetermined Change Control Plan | docs/regulatory/predetermined-change-control-plan.md | Complete | — | Pending Sign-Off |
| Real World Evidence Plan | docs/clinical/real-world-evidence-plan.md | Complete | — | Pending Sign-Off |
| AI/ML Change Control Plan | docs/regulatory/ai-ml-change-control-plan.md | Complete | — | Pending Sign-Off |
| kappa-Monitor Operational Plan | docs/regulatory/risk-management-addendum-p19.md §PMS | Complete | 2026-06-21 | Pending Sign-Off |
| MDR/Vigilance Reporting Procedure | Not yet initiated | Gap | — | Not Started |

---

## Section 11: Submission

| Document Title | Location | Status | Last Updated | Review Status |
|---------------|----------|--------|--------------|---------------|
| Submission Readiness Review | docs/regulatory/submission-readiness-review.md | Complete | 2026-06-21 | Pending Sign-Off |
| Q-Submission Preparation | docs/regulatory/q-submission-preparation.md | Complete | — | Pending Sign-Off |
| FDA Submission Readiness Checklist | docs/regulatory/fda-submission-readiness-checklist.md | Complete | — | Pending Sign-Off |
| Submission Strategy | docs/regulatory/submission-strategy.md | Complete | 2026-06-21 | Pending Sign-Off |
| Regulatory Pathway Decision Record | docs/regulatory/submission-strategy.md §7 | Complete | 2026-06-21 | Pending Sign-Off |

---

## DHF Completeness Summary

| Section | Total Items | Complete | In Progress | Gap |
|---------|------------|----------|-------------|-----|
| 1. User Needs | 7 | 5 | 2 | 0 |
| 2. Software Requirements | 6 | 4 | 2 | 0 |
| 3. Architecture & Design | 9 | 6 | 3 | 0 |
| 4. Risk Management | 6 | 5 | 1 | 0 |
| 5. V&V | 11 | 9 | 0 | 2 |
| 6. Clinical Evidence | 7 | 6 | 0 | 1 |
| 7. Human Factors | 5 | 3 | 0 | 2 |
| 8. Cybersecurity | 7 | 4 | 0 | 3 |
| 9. QMS | 8 | 2 | 0 | 6 |
| 10. Post-Market | 6 | 5 | 0 | 1 |
| 11. Submission | 5 | 5 | 0 | 0 |
| **TOTAL** | **77** | **54** | **8** | **15** |

**Gap remediation required before FDA submission. See submission-readiness-review.md for prioritized action plan.**

---

*Document Owner: Regulatory Affairs Lead | Review Cycle: Quarterly | Next Review: 2026-09-21*
