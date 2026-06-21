# Master Requirements Traceability Matrix
**LumenAI SPD Intelligence Platform** | MTM-LUM-001 | Version 1.0
**Status**: In Review | **Subject to regulatory counsel review before submission.**

Maps: User Need → Requirement → Risk → Control → Test → Evidence

---

## Traceability Matrix

| REQ-ID | Requirement (Summary) | Risk ID | Hazard Summary | Control Measure | Test File | Test Name | Evidence Document |
|--------|----------------------|---------|----------------|----------------|-----------|-----------|-------------------|
| REQ-A-001 | Detect blood residue; kappa ≥ 0.80 | RISK-001 | Missed blood contamination → patient exposure | CV model + mandatory human review | test_p12_clinical_validation.py | TestValidationReport::test_report_has_kappa | clinical-evidence-package.md |
| REQ-A-002 | Detect bone fragments; kappa ≥ 0.80 | RISK-002 | Missed bone fragment → retained debris risk | CV model + human confirmation gate | test_p12_clinical_validation.py | test_findings_by_category | clinical-evidence-package.md |
| REQ-A-003 | Detect tissue residue; kappa ≥ 0.80 | RISK-003 | Missed tissue residue → cross-contamination | CV model + human confirmation gate | test_p12_clinical_validation.py | test_findings_by_category | clinical-evidence-package.md |
| REQ-A-004 | Detect chemical residue; kappa ≥ 0.75 | RISK-004 | Missed chemical residue → patient chemical exposure | CV model + human confirmation; lower threshold acknowledged | test_p12_clinical_validation.py | test_findings_by_category | clinical-evidence-package.md |
| REQ-A-005 | Confidence score (0.0–1.0) with each finding | P19-007 | No confidence shown → reviewer acts without uncertainty awareness | Confidence score mandatory display; server-side storage | test_p4_inspection.py | test_finding_has_confidence_score | risk-management-addendum-p19.md |
| REQ-A-006 | No autonomous pass/fail without human confirmation | RISK-005 | Autonomous AI decision → patient harm without human review | Human confirmation gate enforced at data layer | test_p4_inspection.py | test_no_autonomous_disposition | submission-strategy.md §5 |
| REQ-A-007 | Image processed within 10 seconds (p95) | RISK-006 | Excessive latency → workflow workaround → inspection skipped | Performance target enforced; monitoring active | test_p4_inspection.py | test_processing_latency | software-requirements-specification.md |
| REQ-A-008 | Support 12 finding categories | RISK-007 | Incomplete taxonomy → finding type not detectable | 12 categories defined and implemented | test_p4_inspection.py | test_finding_categories | software-requirements-specification.md §2 |
| REQ-A-009 | AI finding displayed with image evidence | RISK-008 | Finding without evidence → reviewer cannot independently assess | Image evidence co-displayed with finding | test_p4_inspection.py | test_finding_display | human-factors-validation-plan.md §8 |
| REQ-A-010 | All findings logged with model version, confidence, reviewer action | RISK-009 | Incomplete audit trail → post-market surveillance gap | Append-only audit log; all fields required | test_p0_security.py | test_audit_log_completeness | cybersecurity-submission-package.md §5 |
| REQ-B-001 | Rank instruments by risk-weighted priority | RISK-010 | Un-ranked queue → high-risk instruments not prioritized | Multi-factor ranking algorithm | test_p3_ranking.py | test_priority_ranking | software-requirements-specification.md §3 |
| REQ-B-002 | Ranking uses: finding type, severity, history, baseline, recall | RISK-010 | Incomplete ranking factors → wrong priority ordering | Algorithm incorporates all 5 factors | test_p3_ranking.py | test_ranking_factors | software-requirements-specification.md §3 |
| REQ-B-003 | Ranking rationale displayed to reviewer | RISK-011 | Opaque ranking → reviewer cannot assess priority validity | Rationale displayed in UI | test_p3_ranking.py | test_rationale_display | human-factors-validation-plan.md §4 |
| REQ-C-001 | Compare images to manufacturer-approved baselines | RISK-012 | No baseline comparison → defect may appear normal | Baseline comparison algorithm | test_p4_inspection.py | test_baseline_comparison | software-requirements-specification.md §4 |
| REQ-C-003 | Baseline deviations above threshold trigger flag | RISK-012 | Below-threshold deviation undetected → degraded instrument proceeds | Configurable threshold; auto-flag | test_p4_inspection.py | test_baseline_deviation_flag | device-master-record.md §4 |
| REQ-D-001 | Decode Code 128 barcodes | RISK-013 | Unreadable barcode → instrument unidentified → wrong record | Code 128 decoder implemented | test_p4_inspection.py | test_barcode_decode_code128 | software-requirements-specification.md §5 |
| REQ-D-002 | Decode GS1 UDI (AI-01 + AI-21) | RISK-013 | UDI not decoded → FDA tracking compliance gap | GS1 UDI parser implemented | test_p4_inspection.py | test_udi_decode_gs1 | software-requirements-specification.md §5 |
| REQ-D-005 | Flag identification failures for human review | P19-002 | Barcode misread → wrong instrument identified | Explicit failure flag; no silent skip | test_p4_inspection.py | test_id_failure_flagged | risk-management-addendum-p19.md §P19-002 |
| REQ-D-006 | Dual confirmation on identification mismatch | P19-002 | Wrong instrument released under incorrect identity | Dual-confirm workflow required on mismatch | test_p4_inspection.py | test_dual_confirm_on_mismatch | risk-management-addendum-p19.md §P19-002 |
| REQ-E-003 | FDA MedWatch recall data integrated | RISK-014 | Missed recall → recalled instrument used on patient | MedWatch integration connector | test_p6_vendor.py | test_recall_integration | software-requirements-specification.md §6 |
| REQ-E-004 | Recall alerts surfaced within 1 business day | RISK-014 | Delayed recall alert → continued use of recalled instrument | Alert latency SLA enforced | test_p6_vendor.py | test_recall_alert_latency | post-market-surveillance-plan.md |
| REQ-F-002 | Facility data pseudonymized before aggregation | P19-006 | Facility re-identified from benchmark data | Salted hash pseudonymization | test_p5_benchmark.py | test_pseudonymization | risk-management-addendum-p19.md §P19-006 |
| REQ-F-003 | Cohorts < 5 facilities suppressed | P19-006 | Small cohort → facility identifiable by exclusion | k-anonymity (k≥5) suppression | test_p5_benchmark.py | test_minimum_cohort_suppression | risk-management-addendum-p19.md §P19-006 |
| REQ-G-002 | Predictive outputs labeled as estimates | RISK-015 | Prediction treated as determination → wrong action | "Estimate" label required on all outputs | test_p7_predictive.py | test_estimate_labeling | software-requirements-specification.md §8 |
| REQ-G-003 | Human review required before action on predictive alert | RISK-015 | Automated action on prediction → unvalidated instrument action | Advisory-only; human gate required | test_p7_predictive.py | test_human_review_required | submission-strategy.md §5 |
| REQ-H-002 | System SHALL NOT assert causation between quality and patient outcomes | RISK-016 | Causation misattribution → wrong CAPA; true root cause missed | Prohibited language enforcement; output audit | test_p16_patient_safety.py | TestGovernance::test_no_causation_in_correlation_output | risk-management-addendum-p19.md §P19-005 |
| REQ-H-003 | Disclaimer required on all Module H outputs | P19-005 | User misinterprets association as causation | Disclaimer in all outputs: "association for review only" | test_p16_patient_safety.py | TestGovernance::test_disclaimer_present | risk-management-addendum-p19.md §P19-005 |
| REQ-H-005 | PHI NOT stored in Module H outputs | P19-004 | PHI stored → HIPAA violation; privacy breach | PHI strip at route layer; de_identified=True | test_p16_patient_safety.py | TestPHI::test_phi_not_stored | risk-management-addendum-p19.md §P19-004 |
| REQ-I-001 | Support offline inspection session creation | P19-001 | No offline mode → inspection gap in low-connectivity SPD | PWA + IndexedDB offline sessions | test_p17_mobile.py | test_offline_session_creation | risk-management-addendum-p19.md §P19-001 |
| REQ-I-003 | Sessions marked PENDING_SYNC until server confirmed | P19-001 | User assumes sync complete when not → data loss risk | PENDING_SYNC state; badge display | test_p17_mobile.py | test_pending_sync_state | human-factors-validation-plan.md §4 (Task 4) |
| REQ-I-004 | Sync retried with exponential backoff | P19-001 | Single-attempt failure → permanent data loss | Retry with backoff; max 5 attempts | test_p17_mobile.py | test_sync_retry_backoff | risk-management-addendum-p19.md §P19-001 |
| REQ-I-005 | SYNC_FAILED alert on max retry exhaustion | P19-001 | Silent sync failure → inspection record lost | SYNC_FAILED alert generated | test_p17_mobile.py | test_sync_failed_alert | risk-management-addendum-p19.md §P19-001 |
| REQ-J-001 | All API endpoints require authentication | RISK-017 | Unauthenticated access → data exposure | JWT bearer required; dev-token prod-blocked | test_p0_security.py | test_auth_required | cybersecurity-submission-package.md §2 |
| REQ-J-002 | Tenant data isolation — cross-tenant access prevented | RISK-018 | Cross-tenant data leak → PHI/PII exposure | tenant_id filter on all queries; no cross-tenant joins | test_p0_security.py | test_tenant_isolation | cybersecurity-submission-package.md §2.3 |
| REQ-J-003 | All data in transit encrypted TLS 1.2+ | RISK-019 | Unencrypted traffic → data interception | TLS 1.2+ enforced at Nginx | Nginx config inspection | cybersecurity-submission-package.md §2.4 |
| REQ-J-004 | Audit logs append-only; capture all user actions | RISK-020 | Missing audit trail → cannot investigate incidents | Append-only log; no DELETE API | test_p0_security.py | test_audit_log_completeness | cybersecurity-submission-package.md §5 |
| REQ-J-005 | RBAC with technician/supervisor/manager/admin/enterprise roles | RISK-021 | Over-privileged user → unauthorized data modification | tier_guard; require_enterprise_auth | test_p0_security.py | test_rbac_enforcement | cybersecurity-submission-package.md §2.2 |
| REQ-J-006 | Rate limiting enabled in production | P19-008 | Rate limiting disabled → DoS → service unavailable | RATELIMIT_ENABLED=1 required; startup check | test_p0_security.py | test_rate_limiting_active | risk-management-addendum-p19.md §P19-008 |

---

## Traceability Coverage Summary

| Module | Requirements | Risk IDs Covered | Test Files | Evidence Docs |
|--------|-------------|----------------|-----------|--------------|
| A — CV Detection | REQ-A-001 to A-010 | RISK-001 to 009, P19-007 | test_p12_clinical_validation.py, test_p4_inspection.py, test_p0_security.py | clinical-evidence-package.md, risk-management-addendum-p19.md |
| B — AI Ranking | REQ-B-001 to B-003 | RISK-010, RISK-011 | test_p3_ranking.py | software-requirements-specification.md |
| C — Baseline | REQ-C-001, C-003 | RISK-012 | test_p4_inspection.py | software-requirements-specification.md |
| D — Identification | REQ-D-001, D-002, D-005, D-006 | RISK-013, P19-002 | test_p4_inspection.py | risk-management-addendum-p19.md |
| E — Vendor/Recall | REQ-E-003, E-004 | RISK-014 | test_p6_vendor.py | post-market-surveillance-plan.md |
| F — Benchmarking | REQ-F-002, F-003 | P19-006 | test_p5_benchmark.py | risk-management-addendum-p19.md |
| G — Predictive | REQ-G-002, G-003 | RISK-015 | test_p7_predictive.py | software-requirements-specification.md |
| H — Patient Safety | REQ-H-002, H-003, H-005 | RISK-016, P19-004, P19-005 | test_p16_patient_safety.py | risk-management-addendum-p19.md |
| I — Mobile/Offline | REQ-I-001, I-003, I-004, I-005 | P19-001 | test_p17_mobile.py | risk-management-addendum-p19.md |
| J — Security | REQ-J-001 to J-006 | RISK-017 to 021, P19-008 | test_p0_security.py | cybersecurity-submission-package.md |

---

## Traceability Gaps

The following requirements have incomplete test coverage or evidence links:

| REQ-ID | Gap Description | Priority |
|--------|----------------|----------|
| REQ-A-004 | Chemical residue kappa < 0.80 — evidence gap; performance below threshold | HIGH |
| REQ-C-004 | Baseline versioning test not yet confirmed | MEDIUM |
| REQ-E-001, E-002 | Vendor scorecard tests reference needed | MEDIUM |
| REQ-G-004 | Confidence interval display not yet confirmed in test | MEDIUM |
| REQ-I-002 | Sync success confirmation test needed | HIGH |
| REQ-I-006 | PENDING_SYNC badge — UI test only (no automated backend test) | LOW |
| REQ-J-007 | bcrypt test reference not confirmed | MEDIUM |
| REQ-J-008 | JWT secret length check — test or inspection needed | HIGH |
| REQ-J-009 | CORS policy test needed | MEDIUM |
| REQ-J-010 | Audit log retention test needed | LOW |

**Gap remediation**: Coverage gaps shall be addressed in test sprint before submission package finalization.

---

## Revision History

| Version | Date | Description |
|---------|------|-------------|
| 1.0 | 2026-06-21 | Initial master matrix (P19); 40 requirements, 10 modules |

---

*Document Owner: Regulatory Affairs Lead + Software Engineering Lead*
*Review Cycle: Per release | This matrix must be updated with each software release.*
