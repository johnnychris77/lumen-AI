# Software Requirements Specification (SRS)
**LumenAI SPD Intelligence Platform** | SRS-LUM-001 | Version 1.0-RC
**IEC 62304 Compliant** | **Status**: In Review
**Subject to regulatory counsel review before submission.**

---

## 1. Purpose and Scope

This Software Requirements Specification defines functional, performance, safety, and security requirements for LumenAI Version 1.0-RC across all software modules (A–J). Requirements are numbered for traceability to risk controls, test cases, and clinical evidence.

**Verification Methods**:
- **T** — Automated test in `backend/tests/`
- **I** — Inspection of code or configuration
- **A** — Analysis / design review
- **D** — Demonstration in staging/production environment

---

## 2. Module A — Computer Vision Detection (SaMD)

| REQ-ID | Description | Rationale | Verification | Test Reference |
|--------|-------------|-----------|-------------|----------------|
| REQ-A-001 | System SHALL detect blood residue on instrument surfaces with agreement ≥ 0.80 Cohen's kappa vs. expert human panel | Primary safety endpoint; missed blood contamination is a patient harm hazard | T + A | test_p12_clinical_validation.py::TestValidationReport::test_report_has_kappa |
| REQ-A-002 | System SHALL detect bone fragments with agreement ≥ 0.80 Cohen's kappa | Bone fragments indicate inadequate decontamination | T + A | test_p12_clinical_validation.py::test_findings_by_category |
| REQ-A-003 | System SHALL detect tissue residue with agreement ≥ 0.80 Cohen's kappa | Tissue residue is a cross-contamination hazard | T + A | test_p12_clinical_validation.py::test_findings_by_category |
| REQ-A-004 | System SHALL detect chemical residue with agreement ≥ 0.75 Cohen's kappa | Chemical residue may cause patient tissue damage | T + A | test_p12_clinical_validation.py::test_findings_by_category |
| REQ-A-005 | System SHALL provide a confidence score (0.0–1.0) with each CV finding | Confidence score enables human reviewer to assess AI certainty | T + I | test_p4_inspection.py::test_finding_has_confidence_score |
| REQ-A-006 | System SHALL NOT make autonomous pass/fail decisions without human confirmation | Human-in-the-loop safety requirement | T + I | test_p4_inspection.py::test_no_autonomous_disposition |
| REQ-A-007 | System SHALL process inspection image submissions within 10 seconds (p95) | Workflow usability; excessive latency leads to workarounds | T + D | test_p4_inspection.py::test_processing_latency |
| REQ-A-008 | System SHALL support detection across 12 finding categories: blood, bone, tissue, residue, corrosion, crack, pitting, insulation, barcode, UDI, QR, KeyDot | Complete coverage of SPD inspection taxonomy | T + I | test_p4_inspection.py::test_finding_categories |
| REQ-A-009 | System SHALL display the AI finding alongside image evidence allowing the reviewer to independently assess the finding | CDS transparency — reviewer must be able to verify AI output | I + D | UI inspection; test_p4_inspection.py::test_finding_display |
| REQ-A-010 | System SHALL log all AI findings with model version, confidence score, timestamp, and reviewer action | Audit trail for post-market surveillance | T + I | test_p0_security.py::test_audit_log_completeness |

---

## 3. Module B — AI Ranking Engine

| REQ-ID | Description | Rationale | Verification | Test Reference |
|--------|-------------|-----------|-------------|----------------|
| REQ-B-001 | System SHALL rank instruments by inspection priority using risk-weighted scoring | Prioritization supports efficient review of high-risk instruments first | T + A | test_p3_ranking.py::test_priority_ranking |
| REQ-B-002 | Ranking algorithm SHALL incorporate: finding type, finding severity, instrument history, baseline deviation, recall status | Multi-factor ranking reduces missed high-risk items | A + I | test_p3_ranking.py::test_ranking_factors |
| REQ-B-003 | System SHALL display ranking rationale to the human reviewer | Transparency — reviewer must understand why instrument is flagged | T + D | test_p3_ranking.py::test_rationale_display |
| REQ-B-004 | Ranking SHALL be recalculated upon new inspection data or recall alert | Real-time risk awareness | T + I | test_p3_ranking.py::test_ranking_update_on_new_finding |

---

## 4. Module C — Baseline Intelligence

| REQ-ID | Description | Rationale | Verification | Test Reference |
|--------|-------------|-----------|-------------|----------------|
| REQ-C-001 | System SHALL compare inspection images to manufacturer-approved instrument baselines | Baseline deviation detection supports identification of instrument degradation | T + I | test_p4_inspection.py::test_baseline_comparison |
| REQ-C-002 | Baseline match score SHALL be displayed to the human reviewer with the comparison image | Reviewer transparency | I + D | UI inspection |
| REQ-C-003 | Baseline deviations above configurable threshold SHALL trigger human review flag | Configurable sensitivity to institution policy | T + I | test_p4_inspection.py::test_baseline_deviation_flag |
| REQ-C-004 | Baseline images SHALL be versioned and tied to specific instrument manufacturer and model | Ensures correct baseline is used for comparison | T + I | test_p4_inspection.py::test_baseline_versioning |

---

## 5. Module D — Identification (Barcode/UDI/QR/KeyDot)

| REQ-ID | Description | Rationale | Verification | Test Reference |
|--------|-------------|-----------|-------------|----------------|
| REQ-D-001 | System SHALL decode Code 128 barcodes from captured instrument images | Code 128 is common in SPD instrument labeling | T + D | test_p4_inspection.py::test_barcode_decode_code128 |
| REQ-D-002 | System SHALL decode GS1 UDI format (AI-01 GTIN + AI-21 serial number) | FDA UDI requirement for medical device tracking | T + D | test_p4_inspection.py::test_udi_decode_gs1 |
| REQ-D-003 | System SHALL decode QR codes from instrument labels | QR increasingly used in modern instrument sets | T + D | test_p4_inspection.py::test_qr_decode |
| REQ-D-004 | System SHALL support KeyDot optical identification markers | Proprietary identification system used by some SPD facilities | T + D | test_p4_inspection.py::test_keydot_decode |
| REQ-D-005 | System SHALL flag identification failures for human review rather than silently proceeding | Silent failure could result in wrong instrument being processed | T + I | test_p4_inspection.py::test_id_failure_flagged |
| REQ-D-006 | Dual confirmation SHALL be required when identification scan result does not match expected instrument record | Mismatch creates risk of wrong-instrument release | T + I | test_p4_inspection.py::test_dual_confirm_on_mismatch |

---

## 6. Module E — Vendor Intelligence (Non-Device)

| REQ-ID | Description | Rationale | Verification | Test Reference |
|--------|-------------|-----------|-------------|----------------|
| REQ-E-001 | System SHALL track vendor performance metrics aggregated by vendor_id | Quality management — vendor performance visibility | T + I | test_p6_vendor.py::test_vendor_metrics |
| REQ-E-002 | System SHALL generate vendor scorecards with configurable thresholds | Institution-specific thresholds for vendor quality alerts | T + D | test_p6_vendor.py::test_vendor_scorecard |
| REQ-E-003 | FDA MedWatch recall data SHALL be integrated via MedWatch feed integration | Real-time recall awareness is patient safety critical | T + I | test_p6_vendor.py::test_recall_integration |
| REQ-E-004 | Recall alerts SHALL be surfaced to the relevant tenant within 1 business day of MedWatch publication | Timely recall response requirement | T + I | test_p6_vendor.py::test_recall_alert_latency |

---

## 7. Module F — Enterprise Benchmarking (Non-Device)

| REQ-ID | Description | Rationale | Verification | Test Reference |
|--------|-------------|-----------|-------------|----------------|
| REQ-F-001 | System SHALL aggregate anonymized inspection benchmarks across network participants | Network intelligence supports quality improvement | T + I | test_p5_benchmark.py::test_benchmark_aggregation |
| REQ-F-002 | Individual facility data SHALL be pseudonymized before network aggregation | Privacy protection; k-anonymity enforcement | T + I | test_p5_benchmark.py::test_pseudonymization |
| REQ-F-003 | Cohorts with fewer than 5 facilities SHALL be suppressed from benchmarking output | k-anonymity (k≥5) prevents facility re-identification | T + I | test_p5_benchmark.py::test_minimum_cohort_suppression |
| REQ-F-004 | Facility-level data SHALL NOT be recoverable from aggregated benchmark outputs | Re-identification prevention | A + T | test_p5_benchmark.py::test_no_reidentification |

---

## 8. Module G — Predictive Analytics (Non-Device)

| REQ-ID | Description | Rationale | Verification | Test Reference |
|--------|-------------|-----------|-------------|----------------|
| REQ-G-001 | System SHALL generate instrument failure risk scores based on inspection history and finding trends | Predictive maintenance supports proactive quality management | T + I | test_p7_predictive.py::test_risk_score_generation |
| REQ-G-002 | All predictive outputs SHALL be labeled as estimates, not determinations | Prevents overreliance on predictions | I + D | UI inspection; test_p7_predictive.py::test_estimate_labeling |
| REQ-G-003 | Human review SHALL be required before any maintenance or withdrawal action triggered by predictive alerts | Advisory only; human judgment required | T + I | test_p7_predictive.py::test_human_review_required |
| REQ-G-004 | Prediction confidence intervals SHALL be displayed when available | Uncertainty quantification supports informed human review | T + D | test_p7_predictive.py::test_confidence_interval_display |

---

## 9. Module H — Patient Safety Intelligence (Non-Device — Association Only)

| REQ-ID | Description | Rationale | Verification | Test Reference |
|--------|-------------|-----------|-------------|----------------|
| REQ-H-001 | System SHALL identify potential associations between quality signals and safety events | Safety signal detection supports proactive risk management | T + I | test_p16_patient_safety.py::TestCorrelation::test_association_detection |
| REQ-H-002 | System SHALL NEVER assert causation between instrument quality and patient outcomes | Causation claims require clinical study; association only is appropriate | T + I | test_p16_patient_safety.py::TestGovernance::test_no_causation_in_correlation_output |
| REQ-H-003 | All Module H outputs SHALL include disclaimer: "potential association for human review — does not establish causation" | Required warning to prevent misinterpretation | T + I | test_p16_patient_safety.py::TestGovernance::test_disclaimer_present |
| REQ-H-004 | Human review SHALL be required before any action (CAPA, incident report) is initiated based on Module H outputs | Advisory only; no autonomous actions | T + I | test_p16_patient_safety.py::TestGovernance::test_human_review_gate |
| REQ-H-005 | PHI SHALL NOT be stored in Module H association outputs | HIPAA compliance; de-identification required | T + I | test_p16_patient_safety.py::TestPHI::test_phi_not_stored |

---

## 10. Module I — Mobile/Offline Platform

| REQ-ID | Description | Rationale | Verification | Test Reference |
|--------|-------------|-----------|-------------|----------------|
| REQ-I-001 | System SHALL support offline inspection session creation when network connectivity is unavailable | SPD environments may have intermittent connectivity | T + D | test_p17_mobile.py::test_offline_session_creation |
| REQ-I-002 | Offline session data SHALL synchronize to the server when network connectivity is restored | Data integrity — no permanent data loss due to connectivity | T + I | test_p17_mobile.py::test_offline_sync |
| REQ-I-003 | Offline sessions SHALL be marked PENDING_SYNC until server confirmation is received | User awareness of sync state prevents false confidence | T + I | test_p17_mobile.py::test_pending_sync_state |
| REQ-I-004 | Failed synchronization attempts SHALL be retried with exponential backoff | Resilience against transient network failures | T + I | test_p17_mobile.py::test_sync_retry_backoff |
| REQ-I-005 | Sessions that fail synchronization after maximum retries SHALL generate a SYNC_FAILED alert | Data loss prevention — ensures failed syncs are not silently dropped | T + I | test_p17_mobile.py::test_sync_failed_alert |
| REQ-I-006 | PENDING_SYNC badge SHALL be prominently displayed on unsynced sessions | Human awareness — use error prevention | I + D | UI inspection |

---

## 11. Module J — Security & Audit Infrastructure

| REQ-ID | Description | Rationale | Verification | Test Reference |
|--------|-------------|-----------|-------------|----------------|
| REQ-J-001 | All API endpoints SHALL require authentication (JWT bearer token or authorized dev-token in non-production only) | Prevents unauthorized data access | T + I | test_p0_security.py::test_auth_required |
| REQ-J-002 | Tenant data SHALL be isolated — cross-tenant data access SHALL be architecturally prevented | Multi-tenant data breach prevention | T + I | test_p0_security.py::test_tenant_isolation |
| REQ-J-003 | All data in transit SHALL be encrypted using TLS 1.2 or higher | Standard encryption in transit requirement | I + D | nginx.conf inspection; TLS scan |
| REQ-J-004 | Audit logs SHALL be append-only and SHALL capture: tenant_id, user_id, action_type, timestamp, ip_address for all user actions | Immutable audit trail for regulatory compliance | T + I | test_p0_security.py::test_audit_log_completeness |
| REQ-J-005 | System SHALL support role-based access control (RBAC) with at minimum: technician, supervisor, manager, admin, enterprise roles | Least privilege access control | T + I | test_p0_security.py::test_rbac_enforcement |
| REQ-J-006 | API rate limiting SHALL be enabled in production (RATELIMIT_ENABLED=1) | DoS attack prevention | I + D | test_p0_security.py::test_rate_limiting_active |
| REQ-J-007 | Passwords SHALL be stored using bcrypt hashing with minimum cost factor 12 | Password storage security | I + T | test_p0_security.py::test_password_hashing |
| REQ-J-008 | JWT secrets SHALL be minimum 32 characters and SHALL NOT be hardcoded in source code | Secure secrets management | I | Code inspection; environment variable review |
| REQ-J-009 | CORS policy SHALL restrict allowed origins to configured domains; wildcard (*) SHALL NOT be permitted in production | CORS security | I + D | nginx.conf inspection |
| REQ-J-010 | Audit log retention SHALL be minimum 1 year (starter tier) and 7 years (enterprise tier) | Regulatory compliance retention requirements | I + D | Configuration review; database retention policy |

---

## 12. Requirements Traceability Summary

| Module | Requirements Count | Test Files |
|--------|-------------------|-----------|
| A — CV Detection | 10 | test_p12_clinical_validation.py, test_p4_inspection.py |
| B — AI Ranking | 4 | test_p3_ranking.py |
| C — Baseline | 4 | test_p4_inspection.py |
| D — Identification | 6 | test_p4_inspection.py |
| E — Vendor Intelligence | 4 | test_p6_vendor.py |
| F — Benchmarking | 4 | test_p5_benchmark.py |
| G — Predictive | 4 | test_p7_predictive.py |
| H — Patient Safety | 5 | test_p16_patient_safety.py |
| I — Mobile/Offline | 6 | test_p17_mobile.py |
| J — Security | 10 | test_p0_security.py |
| **TOTAL** | **57** | — |

Full traceability: see docs/regulatory/master-traceability-matrix.md

---

*Document Owner: Software Engineering Lead | Review Cycle: Per release*
*This document is subject to formal design review and sign-off before submission.*
