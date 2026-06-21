# Risk Management File — Addendum P19
**LumenAI SPD Intelligence Platform** | RMF-ADD-P19 | Version 1.0
**ISO 14971:2019 Addendum** | **Status**: In Review
**This addendum supplements docs/regulatory/risk-management-file.md with new hazards identified during P19 regulatory readiness review.**
**Subject to regulatory counsel and clinical review before submission.**

---

## 1. Addendum Purpose

This addendum documents additional hazards identified during Milestone P19 (Regulatory Submission Package) review, covering:
- Mobile/offline platform risks (P17)
- Patient safety intelligence risks (P16)
- Network pseudonymization risks (P15)
- AI transparency risks
- Infrastructure security risks

These hazards supplement existing entries in docs/regulatory/risk-management-file.md. Upon QMS establishment, these items shall be formally incorporated into the master Risk Management File with review board sign-off.

---

## 2. Risk Acceptability Policy Reference

Refer to docs/regulatory/risk-management-file.md §2 for probability, severity, and risk level scales.

**Summary**:
- Probability: P1 (Rare) → P5 (Almost Certain)
- Severity: S1 (Negligible) → S5 (Catastrophic)
- Risk Level: Low | Medium | High | Unacceptable
- All High/Unacceptable risks require mitigation to Medium or Low before release

---

## 3. New Hazard Table (P19 Additions)

### Hazard P19-001: Offline Inspection Sync Failure

| Field | Detail |
|-------|--------|
| **Hazard** | Mobile offline inspection session fails to synchronize with server |
| **Hazardous Situation** | PENDING_SYNC session never reconciles; inspection data permanently lost |
| **Harm** | Inspection record gap; instrument may be released without documented inspection; potential patient exposure to uninspected instrument |
| **Probability** | P3 (Possible — transient network issues are common in hospital environments) |
| **Severity** | S3 (Moderate — instrument may be used without inspection record; human verification step may catch) |
| **Pre-Mitigation Risk Level** | Medium |
| **Mitigation Controls** | (1) Auto-retry with exponential backoff (max 5 attempts); (2) SYNC_FAILED alert generated on max retry; (3) PENDING_SYNC badge prominently displayed to user; (4) Offline sessions cannot be marked complete until SYNCED; (5) Alert escalated to supervisor after 24 hours |
| **Residual Risk Level** | Low |
| **Verification** | test_p17_mobile.py::test_sync_failed_alert |

---

### Hazard P19-002: Barcode/UDI Misread — Wrong Instrument Identified

| Field | Detail |
|-------|--------|
| **Hazard** | System decodes barcode/UDI incorrectly due to image quality, label damage, or algorithm error |
| **Hazardous Situation** | Wrong instrument record associated with physical instrument; inspection findings attributed to wrong device |
| **Harm** | Contaminated instrument released under incorrect identity; wrong instrument sterilized; patient exposure |
| **Probability** | P2 (Unlikely — barcode algorithms are mature; image quality controls reduce errors) |
| **Severity** | S4 (Critical — contaminated instrument could reach patient) |
| **Pre-Mitigation Risk Level** | High |
| **Mitigation Controls** | (1) Dual confirmation required for any identification mismatch; (2) Identification failures flagged explicitly, never silently skipped; (3) Human reviewer must manually confirm instrument identity when scan result is ambiguous; (4) Low-confidence identification scans require re-scan; (5) Audit log captures all identification events and confirmation actions |
| **Residual Risk Level** | Medium |
| **Verification** | test_p4_inspection.py::test_dual_confirm_on_mismatch; test_p4_inspection.py::test_id_failure_flagged |

---

### Hazard P19-003: Mobile Image Compression Loss — Defect Below Resolution Threshold

| Field | Detail |
|-------|--------|
| **Hazard** | Mobile image is compressed below quality threshold before or during offline storage |
| **Hazardous Situation** | Defect (contamination, crack, pitting) is below pixel resolution after compression; CV model cannot detect |
| **Harm** | Missed finding; contaminated or defective instrument released; potential patient harm |
| **Probability** | P3 (Possible — mobile cameras vary; aggressive compression by OS or browser is common) |
| **Severity** | S3 (Moderate — human visual review may still detect; not all defects are sub-threshold) |
| **Pre-Mitigation Risk Level** | Medium |
| **Mitigation Controls** | (1) Compression quality floor enforced at ≥ 0.85 JPEG quality before storage; (2) Image quality check on upload (blurriness detection); (3) Low-quality images flagged for retake before submission; (4) Re-capture workflow available to user |
| **Residual Risk Level** | Low |
| **Verification** | test_p17_mobile.py::test_image_quality_floor; I (compression parameter inspection) |

---

### Hazard P19-004: External Event Import Containing PHI

| Field | Detail |
|-------|--------|
| **Hazard** | External system connector imports event data containing patient health information (PHI) |
| **Hazardous Situation** | PHI fields stored in LumenAI database; LumenAI not configured as HIPAA-covered system for PHI storage |
| **Harm** | HIPAA violation; unauthorized PHI disclosure; regulatory sanctions; patient privacy breach |
| **Probability** | P2 (Unlikely with controls — connectors designed to strip PHI; implementation gaps possible) |
| **Severity** | S4 (Critical — HIPAA violations carry civil and criminal penalties; patient harm from privacy breach) |
| **Pre-Mitigation Risk Level** | High |
| **Mitigation Controls** | (1) PHI fields stripped at integration route layer before any storage; (2) de_identified=True flag enforced on all integration imports; (3) PHI field list maintained in connector configuration (name, DOB, MRN, SSN, address, contact info); (4) Unit test verifies PHI not stored; (5) Integration test with synthetic PHI verifies strip function |
| **Residual Risk Level** | Low |
| **Verification** | test_p16_patient_safety.py::TestPHI::test_phi_not_stored; test_integrations.py::test_phi_strip |

---

### Hazard P19-005: Patient Safety Correlation Misinterpreted as Causation

| Field | Detail |
|-------|--------|
| **Hazard** | Module H output of quality-safety association is interpreted by user as established causal link |
| **Hazardous Situation** | User initiates CAPA or incident report attributing patient harm causation to instrument quality based solely on Module H output |
| **Harm** | Incorrect root cause attribution; wrong CAPA action; resource misallocation; failure to identify true root cause; potential repeat patient harm |
| **Probability** | P3 (Possible — users under time pressure may shortcut review; causation language is intuitive) |
| **Severity** | S3 (Moderate — CAPA misdirection may allow true root cause to persist) |
| **Pre-Mitigation Risk Level** | Medium |
| **Mitigation Controls** | (1) Disclaimer required on every Module H output: "potential association for human review — does not establish causation"; (2) Human review required before any CAPA action; (3) Test verifies causation language is absent from all outputs; (4) User training (IFU) explicitly addresses association vs. causation distinction |
| **Residual Risk Level** | Low |
| **Verification** | test_p16_patient_safety.py::TestGovernance::test_no_causation_in_correlation_output; test_p16_patient_safety.py::TestGovernance::test_disclaimer_present |

---

### Hazard P19-006: National Network Pseudonym Rotation Failure — Facility Re-identification

| Field | Detail |
|-------|--------|
| **Hazard** | Monthly pseudonym salt rotation fails; static salt persists across periods; adversary accumulates sufficient data for re-identification |
| **Hazardous Situation** | Facility identified within anonymized benchmark data; competitive intelligence or reputational harm to facility |
| **Harm** | Privacy breach for participating facility; loss of trust in network; regulatory exposure under applicable privacy regulations |
| **Probability** | P2 (Unlikely — rotation is automated; failure requires silent automation failure) |
| **Severity** | S5 (Catastrophic — facility re-identification from supposedly anonymous data is a serious privacy violation) |
| **Pre-Mitigation Risk Level** | High |
| **Mitigation Controls** | (1) Monthly salt rotation automated via APScheduler job; (2) k-anonymity enforced (k≥5 — minimum 5 facilities per cohort); (3) Rotation failure alerts to administrator; (4) Cohort suppression logic re-evaluated on each query; (5) Audit log of salt rotation events |
| **Residual Risk Level** | Low |
| **Verification** | test_p5_benchmark.py::test_minimum_cohort_suppression; test_p5_benchmark.py::test_pseudonymization; I (APScheduler job inspection) |

---

### Hazard P19-007: AI Confidence Score Not Displayed — Reviewer Acts Without Uncertainty Awareness

| Field | Detail |
|-------|--------|
| **Hazard** | UI bug or configuration error causes confidence score to not be displayed to human reviewer |
| **Hazardous Situation** | Human reviewer confirms AI finding without knowing the model's uncertainty level; may accept low-confidence findings uncritically |
| **Harm** | Missed contamination or incorrect disposition due to unrecognized low-confidence finding |
| **Probability** | P3 (Possible — UI rendering failures are a common software defect class) |
| **Severity** | S3 (Moderate — human visual review may still detect; depends on finding type) |
| **Pre-Mitigation Risk Level** | Medium |
| **Mitigation Controls** | (1) Confidence score is a mandatory display element — UI test verifies presence; (2) Low-confidence findings (< 0.60) trigger additional warning to reviewer; (3) Confidence score stored server-side; absence from display is a UI defect caught by automated tests |
| **Residual Risk Level** | Low |
| **Verification** | test_p4_inspection.py::test_finding_has_confidence_score; UI integration test |

---

### Hazard P19-008: Rate Limiting Disabled in Production — DoS Vulnerability

| Field | Detail |
|-------|--------|
| **Hazard** | RATELIMIT_ENABLED environment variable not set to "1" in production deployment |
| **Hazardous Situation** | API endpoints are unprotected against high-volume request flood; service becomes unavailable |
| **Harm** | Service unavailability; SPD technicians unable to access inspection workflows; instrument quality processes disrupted; potential patient safety impact from workflow disruption |
| **Probability** | P3 (Possible — deployment misconfiguration is a common operational error) |
| **Severity** | S3 (Moderate — service disruption; paper-based fallback should exist) |
| **Pre-Mitigation Risk Level** | Medium |
| **Mitigation Controls** | (1) RATELIMIT_ENABLED startup check — application logs warning and may refuse to start if not set in production mode; (2) Deployment checklist includes rate limiting verification; (3) Infrastructure-level rate limiting (AWS WAF) as secondary control |
| **Residual Risk Level** | Low |
| **Verification** | test_p0_security.py::test_rate_limiting_active; I (startup check code inspection) |

---

## 4. Post-Market Monitoring Indicators

The following indicators shall be monitored continuously after commercial deployment. Triggers initiate escalation per the Post-Market Surveillance Plan (docs/regulatory/post-market-surveillance-plan.md).

| Indicator | Metric | Alert Threshold | Escalation Action |
|-----------|--------|----------------|-------------------|
| AI Performance Degradation | Cohen's kappa (rolling 30-day) | < 0.75 | Mandatory retraining review; notify Regulatory Affairs |
| Population Shift (Input) | Population Stability Index (PSI) | PSI > 0.20 | Model re-validation review |
| Concept Drift (Output) | Characteristic Stability Index (CSI) | CSI > 0.15 | Model re-validation review |
| Human Override Rate | % AI findings overridden by humans | > 30% (30-day) | Potential AI degradation review |
| Recall Signal Escalation | Time from MedWatch publication to in-system alert | > 1 business day | Process review |
| Offline Sync Failure Rate | % SYNC_FAILED / total offline sessions | > 5% | Engineering escalation |
| Integration Error Rate | % import records failing normalization | > 2% | Engineering escalation |
| Authentication Failure Rate | % failed auth attempts | > 10% (1-hour window) | Security escalation |
| Critical Finding Acknowledgment Rate | % critical findings acknowledged before proceed | < 95% | UI/UX review |

### 4.1 kappa-Monitor Endpoint

The `/api/validation/kappa-monitor` endpoint is available to authorized administrators and provides:
- Rolling 30-day Cohen's kappa calculation
- Per-category kappa breakdown
- Alert status (GREEN / YELLOW / RED)
- Trend direction (improving / stable / degrading)

Alert thresholds:
- GREEN: kappa ≥ 0.80
- YELLOW: 0.75 ≤ kappa < 0.80 (warning; increased monitoring)
- RED: kappa < 0.75 (mandatory review; consider deployment pause)

---

## 5. Overall Residual Risk Assessment (Post-Mitigation)

Following addition of mitigations for P19-001 through P19-008:

| Hazard ID | Hazard Summary | Post-Mitigation Risk |
|-----------|---------------|---------------------|
| P19-001 | Offline sync failure | Low |
| P19-002 | Barcode misread / wrong instrument | Medium |
| P19-003 | Image compression loss | Low |
| P19-004 | PHI import | Low |
| P19-005 | Causation misinterpretation | Low |
| P19-006 | Pseudonym rotation failure | Low |
| P19-007 | Confidence score not displayed | Low |
| P19-008 | Rate limiting disabled | Low |

**Remaining medium residual risk (P19-002)**: Barcode misread with dual confirmation required. The residual medium risk is acceptable given: (1) barcode misread is detectable by attentive human reviewer; (2) dual confirmation requirement forces deliberate human review; (3) further risk reduction would require impractical constraints on image capture requirements. This acceptable residual risk shall be documented in the overall benefit-risk determination.

---

## 6. Benefit-Risk Statement

The overall residual risks of LumenAI, when used as intended by trained SPD professionals with all mitigations in place, are outweighed by the expected benefits:

- Systematic documentation of instrument inspections (currently often informal)
- Detection of contamination types that human visual inspection may miss under time pressure
- Consistent tracking of inspection history and quality trends
- Timely integration of FDA recall alerts
- Support for regulatory compliance and accreditation

This benefit-risk assessment is preliminary and must be reviewed by clinical and regulatory counsel before submission. It does not constitute a claim of clinical superiority or regulatory approval.

---

*Document Owner: Regulatory Affairs Lead + Clinical Validation Lead*
*Review Cycle: Per risk event; minimum annual | Next Review: 2027-06-21*
*This addendum is subject to formal risk review board sign-off before submission.*
