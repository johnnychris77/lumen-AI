# Traceability Matrix
LumenAI Surgical Instrument Inspection Software | Version 1.0
**Requirements to Hazards to Design to Tests to Validation Evidence**
**Subject to regulatory counsel review.**

This matrix extends the IEC 62304 V&V trace matrix in `docs/clinical/iec62304-vv-trace-matrix.md` with the addition of REQ-016 through REQ-020 and full cross-referencing to hazard IDs and regulatory documents.

---

## Requirements Index

| ID | Requirement Statement | Category |
|----|--------------------|---------|
| REQ-001 | System shall analyze digital images of surgical instruments and generate findings for contamination categories: blood, bone, tissue, residue, corrosion, crack, pitting, insulation damage | CV Detection |
| REQ-002 | System shall assign a confidence score (0.0-1.0) and severity classification (LOW/MEDIUM/HIGH/CRITICAL) to each AI-generated finding | CV Detection |
| REQ-003 | System shall identify instrument by barcode, UDI, QR code, or KeyDot and retrieve instrument history | Instrument Tracking |
| REQ-004 | System shall require technician review and acceptance or override of all AI findings before recording instrument disposition | Human-in-the-Loop |
| REQ-005 | System shall require supervisor co-signature for CRITICAL severity findings before instrument disposition is recorded | Escalation / Human-in-the-Loop |
| REQ-006 | System shall enforce role-based access control with minimum five roles: Technician, Educator, Manager, Infection Prevention Specialist, IT Administrator | Security / RBAC |
| REQ-007 | System shall enforce row-level multi-tenant isolation; no user may access data from a different tenant organization | Security / Multi-tenancy |
| REQ-008 | System shall maintain an immutable audit log recording all inspection events, AI findings, technician decisions, overrides, and supervisor actions with user ID and timestamp | Audit / Traceability |
| REQ-009 | System shall provide accreditation self-assessment tools covering AAMI ST79, Joint Commission, CMS, FDA, and ISO 13485/15189 standards | Accreditation |
| REQ-010 | System shall provide enterprise benchmarking analytics comparing facility performance to peer aggregated baselines | Benchmarking |
| REQ-011 | System shall aggregate vendor and manufacturer instrument defect trends and display recall information with data freshness indicator | Vendor Intelligence |
| REQ-012 | System shall generate predictive failure risk scores for instruments based on inspection history and usage patterns | Predictive Analytics |
| REQ-013 | System shall model SPD workflow throughput with digital twin simulation including bottleneck identification and what-if analysis | Digital Twin |
| REQ-014 | System shall support export of clinical validation datasets with integrity hashing for sealed test set evaluation | Clinical Validation |
| REQ-015 | System shall track real-world evidence metrics (PSI, CSI, per-category performance) for post-market surveillance | Post-Market Surveillance |
| REQ-016 | System shall enforce rate limiting on all public-facing inference and authentication endpoints | Cybersecurity |
| REQ-017 | System shall generate a Software Bill of Materials (SBOM) in CycloneDX format at every build | SBOM / Supply Chain |
| REQ-018 | System shall maintain RWE metrics for post-market surveillance including drift indicators and performance trend data | Post-Market Surveillance |
| REQ-019 | System shall provide a sealed test set registry tracking dataset SHA-256 hashes, access logs, and evaluation results for independent evaluation | Clinical Validation / Integrity |
| REQ-020 | System shall produce human-readable audit packages exportable as PDF including all inspection events, findings, decisions, and overrides | Audit / Reporting |

---

## Full Traceability Matrix

| REQ ID | Requirement (Summary) | Hazard IDs | Risk Controls | Design Artifact (Milestone / File) | Test Evidence (File / Class) | Validation Evidence | Regulatory Doc |
|--------|----------------------|-----------|--------------|----------------------------------|-----------------------------|--------------------|---------------|
| REQ-001 | AI image analysis — contamination/defect detection | H-01, H-02, H-10 | Mandatory human review; low confidence banner; image quality validation | P4 / app/routers/inspections.py; app/services/cv_service.py | tests/test_cv_detection.py; tests/test_inspections.py | P12 clinical performance report (accuracy ~90%, sensitivity ~89%); critical finding subgroup (>=92%) | clinical-evidence-summary.md; risk-management-file.md H-01 |
| REQ-002 | Confidence score and severity classification | H-01, H-08 | LOW CONFIDENCE banner <0.70; CRITICAL requires supervisor | P4 / app/schemas/findings.py; P9 UI | tests/test_findings.py; tests/test_confidence_thresholds.py | P12 validation — confidence calibration review | risk-management-file.md H-08; user-labeling-and-instructions.md Section 7 |
| REQ-003 | Instrument identification (barcode, UDI, QR, KeyDot) | H-06 | Human identity confirmation; low confidence triggers manual ID | P4 / app/routers/instruments.py; app/services/tracking_service.py | tests/test_instrument_tracking.py; tests/test_udi_scanner.py | P12 tracking accuracy metrics | risk-management-file.md H-06; traceability-matrix.md |
| REQ-004 | Mandatory technician review before disposition | H-01, H-08 | Core safety control — enforced at API layer | P0-P4 / app/routers/inspections.py (disposition endpoint requires accepted findings) | tests/test_disposition_enforcement.py; tests/test_hitl_workflow.py | P12 reader study protocol — technician review step mandatory | intended-use-and-claims-boundary.md Section 8; risk-management-file.md H-01 |
| REQ-005 | Supervisor co-sign for CRITICAL findings | H-01, H-08 | Dual authorization at API layer for CRITICAL disposition | P9 / app/routers/escalations.py; app/services/escalation_service.py | tests/test_escalation_workflow.py; tests/test_supervisor_cosign.py | P12 escalation workflow validation | user-labeling-and-instructions.md Section 6.6; risk-management-file.md H-01 |
| REQ-006 | RBAC — 5 roles enforced | H-03, H-11 | JWT claims + middleware RBAC check on every endpoint | P1 / app/core/security.py; app/core/rbac.py | tests/test_rbac.py; tests/test_auth.py | P1 security audit | software-lifecycle-readiness.md Section 2; cybersecurity-readiness.md Section 3.2 |
| REQ-007 | Multi-tenant row-level isolation | H-03 | ORM-level tenant filter; middleware validation | P2 / app/core/tenant.py; app/db/base.py | tests/test_tenant_isolation.py; tests/test_cross_tenant_prevention.py | P2 tenant isolation test results | cybersecurity-readiness.md Section 3.4; risk-management-file.md H-03 |
| REQ-008 | Immutable audit log | H-07 | Append-only DB table; no DELETE permissions for app user; S3 archive | P0 / app/services/audit_service.py; app/models/audit_log.py | tests/test_audit_log.py; tests/test_audit_immutability.py | P0 audit log review | user-labeling-and-instructions.md Section 9; software-lifecycle-readiness.md Section 10 |
| REQ-009 | Accreditation self-assessment tools | None direct | Administrative module; no direct patient safety impact | P8 / app/routers/accreditation.py; app/services/accreditation_service.py | tests/test_accreditation.py; tests/test_standards_catalog.py | P8 module validation | samd-classification-assessment.md Module E; intended-use-and-claims-boundary.md Section 5 |
| REQ-010 | Enterprise benchmarking analytics | None direct | Administrative analytics; human review of all benchmark reports | P5 / app/routers/benchmarking.py; app/services/benchmark_service.py | tests/test_benchmarking.py; tests/test_peer_comparison.py | P5 module validation | samd-classification-assessment.md Module F |
| REQ-011 | Vendor intelligence and recall display | H-09 | Data freshness indicator; stale data alert; primary recall system remains hospital's | P6 / app/routers/vendor_intelligence.py; app/services/recall_service.py | tests/test_vendor_intelligence.py; tests/test_recall_freshness.py | P6 module validation; recall data latency tests | risk-management-file.md H-09; intended-use-and-claims-boundary.md Section 5 |
| REQ-012 | Predictive failure risk scoring | H-04 (indirect) | Decision support only; maintenance decision by qualified engineer | P7 / app/routers/predictive.py; app/services/predictive_service.py | tests/test_predictive_analytics.py; tests/test_failure_scoring.py | P7 module validation | samd-classification-assessment.md Module C; ai-ml-change-control-plan.md |
| REQ-013 | Digital twin SPD simulation | None direct | Operational planning tool; no clinical decisions | P10 / app/routers/digital_twin.py; app/services/simulation_service.py | tests/test_digital_twin.py; tests/test_simulation.py | P10 module validation | samd-classification-assessment.md Module H |
| REQ-014 | Clinical validation dataset export with integrity hashing | None direct | Administrative function; integrity of validation evidence | P12 / app/routers/validation.py; app/services/validation_service.py | tests/test_validation_export.py; tests/test_dataset_integrity.py | P12 validation module; sealed-test-set-protocol.md | clinical-evidence-summary.md; fda-submission-readiness-checklist.md Section 8 |
| REQ-015 | Real-world evidence metrics tracking | H-04 | Drift alerts trigger human review; no automatic model updates | P12 / app/routers/rwe.py; app/services/rwe_service.py | tests/test_rwe_metrics.py; tests/test_drift_detection.py | P12 RWE plan; real-world-evidence-plan.md | ai-ml-change-control-plan.md Section 11; risk-management-file.md H-04 |
| REQ-016 | Rate limiting on inference and auth endpoints | H-03 | Defense-in-depth against DoS and brute force attacks | P1/P11 / app/core/rate_limit.py; middleware configuration | tests/test_rate_limiting.py; tests/test_auth_lockout.py | P11 security hardening review | cybersecurity-readiness.md Section 1; risk-management-file.md H-03 |
| REQ-017 | SBOM generation at every build (CycloneDX) | H-03 (supply chain) | Enables rapid vulnerability identification in deployed components | P11 / .github/workflows/deploy.yml (CycloneDX step) | CI pipeline validation; SBOM artifact presence check | P11 build pipeline validation | cybersecurity-readiness.md Section 4; software-lifecycle-readiness.md Section 11 |
| REQ-018 | RWE metrics for post-market surveillance | H-04 | Provides ongoing performance monitoring signals | P12 / app/services/rwe_service.py; app/models/rwe_metrics.py | tests/test_rwe_metrics.py; tests/test_psi_calculation.py; tests/test_csi_calculation.py | P12 RWE plan; real-world-evidence-plan.md | ai-ml-change-control-plan.md Section 5; risk-management-file.md Section 5 |
| REQ-019 | Sealed test set registry with SHA-256 hashes | None direct | Ensures integrity and independence of evaluation datasets | P12 / app/routers/sealed_testset.py; app/services/testset_registry.py | tests/test_sealed_testset.py; tests/test_hash_integrity.py | P12 sealed test set module; sealed-test-set-protocol.md | clinical-evidence-summary.md Section 3.2; fda-submission-readiness-checklist.md 8.7 |
| REQ-020 | PDF audit package export | H-07 | Enables human-readable audit review for regulatory inspections | P12 / app/services/audit_export_service.py; ReportLab integration | tests/test_audit_pdf_export.py; tests/test_pdf_generation.py | P12 audit export module validation | user-labeling-and-instructions.md Section 9; software-lifecycle-readiness.md |

---

## Hazard-to-Requirement Cross-Reference

| Hazard ID | Hazard Summary | Controlling Requirements |
|-----------|---------------|------------------------|
| H-01 | False Negative — Contamination Missed | REQ-001, REQ-002, REQ-004, REQ-005 |
| H-02 | False Positive — Clean Instrument Flagged | REQ-001, REQ-002, REQ-004 |
| H-03 | Unauthorized Data Access | REQ-006, REQ-007, REQ-016, REQ-017 |
| H-04 | AI Model Drift | REQ-015, REQ-018, REQ-012 (indirect) |
| H-05 | System Downtime (Moderate) | REQ-004 (fallback documented), REQ-008 |
| H-06 | Incorrect Instrument Identification | REQ-003, REQ-004 |
| H-07 | Audit Log Tampering | REQ-008, REQ-020 |
| H-08 | UI Misinterpretation | REQ-002, REQ-004, REQ-005 |
| H-09 | Incorrect Recall Information | REQ-011 |
| H-10 | Training Data Bias | REQ-001, REQ-014, REQ-019 |
| H-11 | Configuration Error | REQ-006, REQ-008 |
| H-12 | Extended System Outage | REQ-008 (audit), REQ-004 (fallback) |

---

## Validation Evidence Summary

| Validation Category | Evidence Source | Performance Summary | Status |
|--------------------|----------------|--------------------|----|
| Overall AI accuracy | docs/clinical/clinical-performance-report.md | ~90% (mock data) | Complete (mock) |
| Overall sensitivity | docs/clinical/clinical-performance-report.md | ~89% (mock data) | Complete (mock) |
| Cohen's Kappa | docs/clinical/clinical-performance-report.md | ~0.79 (mock data; below 0.80 threshold) | At Risk (mock) |
| Critical findings sensitivity | docs/regulatory/clinical-evidence-summary.md | >=92% for crack/corrosion/insulation (mock) | Complete (mock) |
| Human vs. AI comparison | docs/clinical/human-vs-ai-study-protocol.md | Protocol defined; study pending | Not Started |
| Sealed test set evaluation | docs/clinical/sealed-test-set-protocol.md | Protocol defined; evaluation pending | Not Started |
| Usability study | IEC 62366 formative + summative | Not yet planned in detail | Not Started |
| Security tests | 1,163 pytest tests; ruff | All passing | Complete |
| Penetration test | Third-party | Planned Q2 2026 | Not Started |
| Real-world evidence | docs/clinical/real-world-evidence-plan.md | Plan complete; enrollment pending launch | Not Started |

---

## Document Cross-Reference Index

| Document | Location | Purpose |
|---------|---------|--------|
| Intended Use and Claims Boundary | docs/regulatory/intended-use-and-claims-boundary.md | Intended use; prohibited claims; HITL model |
| SaMD Classification Assessment | docs/regulatory/samd-classification-assessment.md | IMDRF risk classification; FDA pathway |
| Risk Management File | docs/regulatory/risk-management-file.md | ISO 14971 hazard analysis; risk controls |
| Software Lifecycle Readiness | docs/regulatory/software-lifecycle-readiness.md | IEC 62304 compliance; SOUP; architecture |
| AI/ML Change Control Plan | docs/regulatory/ai-ml-change-control-plan.md | Model versioning; drift; PCCP; rollback |
| Cybersecurity Readiness | docs/regulatory/cybersecurity-readiness.md | FDA 2023 cybersecurity guidance compliance |
| Clinical Evidence Summary | docs/regulatory/clinical-evidence-summary.md | Performance data; study design; gaps |
| User Labeling and Instructions | docs/regulatory/user-labeling-and-instructions.md | IFU; warnings; escalation; override |
| FDA Submission Readiness Checklist | docs/regulatory/fda-submission-readiness-checklist.md | Submission gap analysis; priority actions |
| Traceability Matrix | docs/regulatory/traceability-matrix.md | This document |
| IEC 62304 V&V Trace Matrix | docs/clinical/iec62304-vv-trace-matrix.md | Detailed test-level traceability |
| Clinical Performance Report | docs/clinical/clinical-performance-report.md | Quantitative performance results |
| Cybersecurity Threat Model | docs/clinical/cybersecurity-threat-model.md | STRIDE threat analysis |
| 510(k) Predicate Analysis | docs/clinical/510k-predicate-analysis.md | Predicate device candidates |
| Real-World Evidence Plan | docs/clinical/real-world-evidence-plan.md | Post-market RWE enrollment |
| Sealed Test Set Protocol | docs/clinical/sealed-test-set-protocol.md | Independent evaluation protocol |
| Human vs. AI Study Protocol | docs/clinical/human-vs-ai-study-protocol.md | MRMC reader study design |
| Validation Dataset Specification | docs/clinical/validation-dataset-specification.md | Dataset composition and annotation |
| Baseline Validation Protocol | docs/clinical/baseline-validation-protocol.md | Baseline comparison methodology |
| Clinical Safety Review | docs/clinical/clinical-safety-review.md | Safety assessment summary |
