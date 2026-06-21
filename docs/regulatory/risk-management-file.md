# Risk Management File
LumenAI Surgical Instrument Inspection Software | Version 1.0
**ISO 14971:2019 Compliant Risk Management File**
**Subject to regulatory counsel review before submission.**

---

## 1. Risk Management Plan Overview

### 1.1 Scope
This Risk Management File covers all software modules of LumenAI Version 1.0, including:
- Computer Vision Detection (P4)
- AI Inspection Ranking Engine (P3)
- Predictive Failure Analytics (P7)
- Autonomous Inspection Copilot (P9)
- Regulatory Automation / Accreditation (P8)
- Enterprise Benchmarking (P5)
- Vendor Intelligence Exchange (P6)
- Digital Twin of SPD Operations (P10)
- Authentication, Security, and Audit Infrastructure (P0-P2)

### 1.2 Risk Management Team
| Role | Responsibility |
|------|---------------|
| Regulatory Affairs Lead | Risk file ownership, acceptability decisions |
| Clinical Validation Lead | Harm severity input, clinical context |
| Software Engineering Lead | Probability estimates, control implementation |
| Cybersecurity Lead | Security hazard analysis |
| Quality Manager | Review and approval |

### 1.3 Risk Management Activities
Per ISO 14971:2019 Section 4:
- Risk analysis (hazard identification, estimation)
- Risk evaluation (acceptability determination)
- Risk control (measures, verification)
- Residual risk evaluation
- Overall residual risk evaluation
- Risk management review
- Post-production information collection

---

## 2. Risk Acceptability Policy

### 2.1 Severity Scale
| Level | Score | Definition |
|-------|-------|-----------|
| Negligible | 1 | No injury; no clinical impact |
| Minor | 2 | Temporary, reversible harm; no lasting impact |
| Moderate | 3 | Significant harm requiring medical intervention |
| Serious | 4 | Permanent injury or significant morbidity |
| Critical | 5 | Life-threatening or fatal outcome |

### 2.2 Probability Scale
| Level | Score | Definition | Approximate Rate |
|-------|-------|-----------|-----------------|
| Remote | 1 | Unlikely to occur in device lifetime | <1 in 100,000 uses |
| Unlikely | 2 | Infrequent occurrence | 1 in 10,000 – 1 in 100,000 uses |
| Possible | 3 | Occasional occurrence | 1 in 1,000 – 1 in 10,000 uses |
| Likely | 4 | Frequent occurrence | 1 in 100 – 1 in 1,000 uses |
| Almost Certain | 5 | Will occur in normal use | >1 in 100 uses |

### 2.3 Risk Acceptability Matrix
| RPN Range | Classification | Action Required |
|-----------|---------------|----------------|
| 1-6 | Acceptable | Document; no further action required |
| 7-12 | ALARP | Reduce as low as reasonably practicable; document justification |
| >12 | Unacceptable | Must reduce before release; risk controls mandatory |

---

## 3. Hazard Analysis and Risk Control Table

### H-01: False Negative — AI Fails to Detect Contamination

| Field | Value |
|-------|-------|
| Hazard ID | H-01 |
| Hazard Description | AI system fails to flag contaminated instrument |
| Harm | Surgical site infection (SSI); patient harm from inadequately processed instrument |
| Hazardous Situation | Contaminated instrument released for use in surgical procedure |
| Cause | Model sensitivity limitation; image quality degradation; novel contamination type not in training data |
| Initial Severity | 5 (Critical) |
| Initial Probability | 3 (Possible) |
| Initial RPN | 15 (Unacceptable) |
| Risk Controls | (1) Mandatory human technician review of all AI findings before instrument disposition; (2) Low confidence banner (<0.70) triggers mandatory manual inspection; (3) Critical finding categories (blood, bone, tissue) receive enhanced sensitivity weighting in model; (4) Image quality validation at capture time rejects substandard images; (5) Technician training requirement for image acquisition protocol; (6) Dual sign-off (technician + supervisor) for CRITICAL severity findings |
| Residual Severity | 4 (Serious) |
| Residual Probability | 1 (Remote) |
| Residual RPN | 4 (Acceptable) |
| Verification Evidence | P12 sensitivity metrics (critical FN rate 1.8% on mock data); P0/P1 audit log enforcement; P9 escalation workflow tests; image quality rejection unit tests |
| Post-Market Signal | Critical FN rate tracked quarterly via P12 RWE module; threshold >2% triggers model review |

### H-02: False Positive — AI Incorrectly Flags Clean Instrument

| Field | Value |
|-------|-------|
| Hazard ID | H-02 |
| Hazard Description | AI system incorrectly flags a clean instrument as contaminated |
| Harm | Unnecessary instrument removal from service; workflow disruption; potential surgical case delay |
| Hazardous Situation | Unneeded instrument quarantine leading to surgical case cancellation or delay |
| Cause | Model specificity limitation; image artifact mimicking contamination; lighting anomaly |
| Initial Severity | 2 (Minor) |
| Initial Probability | 3 (Possible) |
| Initial RPN | 6 (Acceptable) |
| Risk Controls | (1) Human technician override capability with documented reason; (2) Override audit log captures all FP corrections for model feedback; (3) Confidence score displayed to technician to contextualize finding |
| Residual Severity | 2 (Minor) |
| Residual Probability | 2 (Unlikely) |
| Residual RPN | 4 (Acceptable) |
| Verification Evidence | P12 specificity metrics; P0 override logging tests; P4 CV module precision scores |
| Post-Market Signal | Override rate tracked monthly; spike >15% triggers model review |

### H-03: Unauthorized Data Access / Privacy Breach

| Field | Value |
|-------|-------|
| Hazard ID | H-03 |
| Hazard Description | Unauthorized access to inspection records, images, or PHI-adjacent data |
| Harm | Patient privacy violation; HIPAA breach; reputational harm; regulatory sanction |
| Hazardous Situation | Attacker or unauthorized insider accesses inspection image database or audit logs |
| Cause | Authentication bypass; SQL injection; misconfigured multi-tenant isolation; compromised credentials |
| Initial Severity | 4 (Serious) |
| Initial Probability | 2 (Unlikely) |
| Initial RPN | 8 (ALARP) |
| Risk Controls | (1) JWT + RBAC authentication enforced on all endpoints (P1); (2) Row-level tenant isolation on all database queries (P2); (3) AES-256 encryption at rest; TLS 1.3 in transit (P11); (4) Rate limiting on all auth endpoints (P1); (5) Penetration testing prior to go-live; (6) Immutable audit log with tamper detection (P0); (7) MFA required for admin and manager roles |
| Residual Severity | 3 (Moderate) |
| Residual Probability | 1 (Remote) |
| Residual RPN | 3 (Acceptable) |
| Verification Evidence | P1 auth test suite; P2 tenant isolation tests; P11 security scan; docs/clinical/cybersecurity-threat-model.md; docs/regulatory/cybersecurity-readiness.md |
| Post-Market Signal | Security incident reports; failed auth spike alerts; SOC monitoring |

### H-04: AI Model Drift — Performance Degradation Over Time

| Field | Value |
|-------|-------|
| Hazard ID | H-04 |
| Hazard Description | AI model performance degrades due to distribution shift in instrument population or imaging conditions |
| Harm | Increased false negatives leading to patient harm (see H-01); or increased false positives causing workflow disruption |
| Hazardous Situation | Model deployed without drift detection; degraded performance undetected for extended period |
| Cause | New instrument types introduced at hospital; camera hardware change; lighting protocol change; seasonal variation |
| Initial Severity | 4 (Serious) |
| Initial Probability | 2 (Unlikely) |
| Initial RPN | 8 (ALARP) |
| Risk Controls | (1) PSI >0.2 (finding distribution) triggers automated alert; (2) CSI >0.15 (baseline scores) triggers alert; (3) Quarterly performance review against RWE benchmarks (P12); (4) Locked model — no online learning without formal revalidation; (5) Change control process (docs/regulatory/ai-ml-change-control-plan.md); (6) Annual model revalidation requirement |
| Residual Severity | 3 (Moderate) |
| Residual Probability | 1 (Remote) |
| Residual RPN | 3 (Acceptable) |
| Verification Evidence | P12 RWE module; drift detection implementation; AI/ML change control plan |
| Post-Market Signal | Quarterly PSI/CSI monitoring reports; performance dashboard |

### H-05: System Downtime During Critical Inspection Workflow

| Field | Value |
|-------|-------|
| Hazard ID | H-05 |
| Hazard Description | LumenAI system unavailable when SPD needs to inspect instruments for urgent surgical case |
| Harm | Surgical case delay; patient harm if case is urgent; financial harm to hospital |
| Hazardous Situation | System failure during high-demand period (e.g., overnight emergency surgery preparation) |
| Cause | Server crash; database corruption; network failure; dependency service outage; deployment error |
| Initial Severity | 3 (Moderate) |
| Initial Probability | 2 (Unlikely) |
| Initial RPN | 6 (Acceptable) |
| Risk Controls | (1) Kubernetes deployment with auto-restart and pod health checks (P11); (2) 99.5% uptime SLA with monitoring (P11); (3) Fallback to paper-based manual inspection protocol documented in IFU; (4) Database backup and recovery procedures (15-min RTO target); (5) Maintenance windows during lowest-demand periods; (6) Incident response plan (P11 reliability.md) |
| Residual Severity | 2 (Minor) |
| Residual Probability | 1 (Remote) |
| Residual RPN | 2 (Acceptable) |
| Verification Evidence | P11 reliability tests; Kubernetes deployment manifests; uptime monitoring configuration |
| Post-Market Signal | SLA compliance reports; incident log review |

### H-06: Incorrect Instrument Identification

| Field | Value |
|-------|-------|
| Hazard ID | H-06 |
| Hazard Description | AI misidentifies instrument type or UDI, causing incorrect baseline comparison |
| Harm | Wrong instrument cleared or flagged; incorrect maintenance history applied |
| Hazardous Situation | Instrument with matching visual features but different risk profile receives incorrect disposition |
| Cause | OCR/barcode read error; damaged label; visually similar instrument types; tracking module error |
| Initial Severity | 3 (Moderate) |
| Initial Probability | 2 (Unlikely) |
| Initial RPN | 6 (Acceptable) |
| Risk Controls | (1) Human technician confirms instrument identity before accepting AI tracking result; (2) Low confidence on tracking triggers manual ID verification; (3) UDI cross-validation against hospital inventory database; (4) Audit log records all identification decisions |
| Residual Severity | 2 (Minor) |
| Residual Probability | 1 (Remote) |
| Residual RPN | 2 (Acceptable) |
| Verification Evidence | P4 tracking module tests; P3 ranking engine tests; technician confirmation workflow |
| Post-Market Signal | Identification error reports in audit log; user feedback |

### H-07: Data Integrity — Audit Log Tampering or Loss

| Field | Value |
|-------|-------|
| Hazard ID | H-07 |
| Hazard Description | Audit log records are deleted, modified, or lost |
| Harm | Loss of regulatory compliance evidence; inability to investigate adverse events; HIPAA violation |
| Hazardous Situation | Malicious actor or software error corrupts or deletes audit records |
| Cause | Insufficient access controls on audit table; backup failure; deliberate insider tampering |
| Initial Severity | 3 (Moderate) |
| Initial Probability | 2 (Unlikely) |
| Initial RPN | 6 (Acceptable) |
| Risk Controls | (1) Immutable audit log — delete operations blocked at application layer (P0); (2) Append-only database table with no UPDATE/DELETE permissions for application user; (3) 7-year retention policy enforced; (4) Automated daily backup with integrity hash verification; (5) S3 write-once storage for long-term archive; (6) Tamper detection alert if hash mismatch |
| Residual Severity | 2 (Minor) |
| Residual Probability | 1 (Remote) |
| Residual RPN | 2 (Acceptable) |
| Verification Evidence | P0 audit log tests; database migration immutability constraints; backup procedure docs |
| Post-Market Signal | Backup integrity reports; periodic audit log hash verification |

### H-08: User Interface Confusion — Misinterpretation of AI Finding

| Field | Value |
|-------|-------|
| Hazard ID | H-08 |
| Hazard Description | SPD technician misinterprets AI finding confidence or severity level |
| Harm | Incorrect instrument disposition (release of defective instrument or unnecessary rejection) |
| Hazardous Situation | Technician acts on AI finding without adequate understanding of confidence level or severity |
| Cause | Unclear UI labeling; inadequate training; cognitive overload during busy shift; poor confidence display |
| Initial Severity | 4 (Serious) |
| Initial Probability | 2 (Unlikely) |
| Initial RPN | 8 (ALARP) |
| Risk Controls | (1) Color-coded severity indicators with explicit text labels (P9 UI); (2) LOW CONFIDENCE banner prominently displayed for findings <0.70; (3) Mandatory training completion before clinical use; (4) CRITICAL findings cannot be dismissed without supervisor co-sign; (5) Usability study planned prior to go-live (P12 reader study protocol); (6) IFU includes interpretation guidance |
| Residual Severity | 3 (Moderate) |
| Residual Probability | 1 (Remote) |
| Residual RPN | 3 (Acceptable) |
| Verification Evidence | P9 copilot UI tests; P12 reader study (pending live execution); IFU labeling |
| Post-Market Signal | Override pattern analysis; user error reports; training completion rates |

### H-09: Vendor Intelligence Data Quality — Incorrect Recall Information

| Field | Value |
|-------|-------|
| Hazard ID | H-09 |
| Hazard Description | Vendor/manufacturer intelligence module displays incorrect or outdated recall information |
| Harm | Continued use of recalled instrument; patient harm |
| Hazardous Situation | Recalled instrument not flagged because recall data feed is delayed or corrupt |
| Cause | External data feed failure; sync error; recall database latency; data parsing error |
| Initial Severity | 4 (Serious) |
| Initial Probability | 2 (Unlikely) |
| Initial RPN | 8 (ALARP) |
| Risk Controls | (1) Recall data freshness indicator displayed to user; (2) Stale data (>24 hours) triggers alert; (3) Hospital maintains primary recall management process independent of LumenAI; (4) LumenAI frames recall display as supplementary reference, not primary alert system; (5) Data feed integrity checks at ingestion |
| Residual Severity | 3 (Moderate) |
| Residual Probability | 1 (Remote) |
| Residual RPN | 3 (Acceptable) |
| Verification Evidence | P6 vendor intelligence tests; data freshness unit tests; IFU contraindication language |
| Post-Market Signal | Data feed latency monitoring; user reports of stale data |

### H-10: Training Data Bias — Underperformance on Instrument Subgroups

| Field | Value |
|-------|-------|
| Hazard ID | H-10 |
| Hazard Description | AI model systematically underperforms on specific instrument types, manufacturer brands, or facility contexts due to training data bias |
| Harm | Disproportionate false negative rate for underrepresented instrument types; patient harm |
| Hazardous Situation | Hospital uses instrument types not well-represented in training data; degraded AI performance goes undetected |
| Cause | Non-representative training dataset; overrepresentation of certain instrument brands; limited geographic diversity in training data |
| Initial Severity | 4 (Serious) |
| Initial Probability | 2 (Unlikely) |
| Initial RPN | 8 (ALARP) |
| Risk Controls | (1) Subgroup performance analysis by instrument category in P12 validation; (2) Instrument type not in training data flagged as "Unvalidated — manual inspection required"; (3) Multi-site live study to expand training data diversity (Q3 2026); (4) Bias audit as part of annual model review; (5) Hospitals report novel instrument types for inclusion in next training cycle |
| Residual Severity | 3 (Moderate) |
| Residual Probability | 1 (Remote) |
| Residual RPN | 3 (Acceptable) |
| Verification Evidence | P12 subgroup analysis; training data manifest; validation dataset specification |
| Post-Market Signal | Per-category performance tracking in RWE module; novel instrument type reports |

### H-11: Configuration Error — Incorrect Threshold Settings

| Field | Value |
|-------|-------|
| Hazard ID | H-11 |
| Hazard Description | Administrator misconfigures confidence thresholds or severity routing rules |
| Harm | System-wide performance degradation; critical findings not escalated; false sense of security |
| Hazardous Situation | Hospital IT admin sets confidence threshold too high (suppressing valid alerts) or too low (alert fatigue) |
| Cause | Complex configuration UI; insufficient admin training; no validation of configuration changes |
| Initial Severity | 4 (Serious) |
| Initial Probability | 2 (Unlikely) |
| Initial RPN | 8 (ALARP) |
| Risk Controls | (1) Default configurations locked at validated settings; (2) Configuration changes require manager or admin role; (3) Change audit logged; (4) Out-of-range threshold values rejected with validation error; (5) Critical threshold changes require confirmation with impact warning; (6) Configuration review included in annual quality audit |
| Residual Severity | 3 (Moderate) |
| Residual Probability | 1 (Remote) |
| Residual RPN | 3 (Acceptable) |
| Verification Evidence | P1 RBAC tests; configuration validation unit tests; audit log coverage |
| Post-Market Signal | Configuration change audit review; performance anomaly detection |

### H-12: System Unavailable During Critical Inspection Workflow (Extended Outage)

| Field | Value |
|-------|-------|
| Hazard ID | H-12 |
| Hazard Description | Extended system downtime (>4 hours) prevents LumenAI use for instrument inspection across a facility |
| Harm | Reliance on manual-only inspection during high-volume period; potential inspection quality reduction; surgical case cancellations |
| Hazardous Situation | Extended outage during high-volume surgical day without established fallback procedure |
| Cause | Cloud provider outage; database corruption requiring restore; major software defect; cyber attack |
| Initial Severity | 3 (Moderate) |
| Initial Probability | 1 (Remote) |
| Initial RPN | 3 (Acceptable) |
| Risk Controls | (1) Business continuity plan mandates documented manual inspection fallback (P11); (2) K8s pod redundancy reduces single-point failure risk; (3) 15-minute RTO target for database restore; (4) Incident communication to affected facilities within 30 minutes of declared outage; (5) Quarterly disaster recovery drill; (6) IFU documents manual inspection fallback procedure |
| Residual Severity | 2 (Minor) |
| Residual Probability | 1 (Remote) |
| Residual RPN | 2 (Acceptable) |
| Verification Evidence | P11 reliability documentation; K8s deployment configuration; DR drill records |
| Post-Market Signal | Incident duration reports; DR drill results |

---

## 4. Overall Residual Risk Evaluation

### 4.1 Residual Risk Summary
| Hazard | Residual RPN | Acceptability |
|--------|-------------|--------------|
| H-01: False Negative — Contamination Missed | 4 | Acceptable |
| H-02: False Positive — Clean Instrument Flagged | 4 | Acceptable |
| H-03: Unauthorized Data Access | 3 | Acceptable |
| H-04: AI Model Drift | 3 | Acceptable |
| H-05: System Downtime (Moderate) | 2 | Acceptable |
| H-06: Incorrect Instrument Identification | 2 | Acceptable |
| H-07: Audit Log Tampering | 2 | Acceptable |
| H-08: UI Misinterpretation | 3 | Acceptable |
| H-09: Incorrect Recall Information | 3 | Acceptable |
| H-10: Training Data Bias | 3 | Acceptable |
| H-11: Configuration Error | 3 | Acceptable |
| H-12: Extended System Outage | 2 | Acceptable |

All residual risks are within the Acceptable range (RPN 1-6). No hazards remain in the Unacceptable or ALARP categories after implementation of risk controls.

### 4.2 Benefit-Risk Determination
The primary benefits of LumenAI are:
- Systematic, AI-assisted contamination detection supporting AAMI ST79 compliance
- Consistent protocol adherence across all SPD technician skill levels
- Complete audit trail for regulatory compliance and adverse event investigation
- Predictive maintenance reducing unexpected instrument failure risk

These benefits, when weighed against the residual risks (all Acceptable), support a positive benefit-risk determination for LumenAI Version 1.0, subject to:
1. Completion of mandatory human-in-the-loop controls
2. Completion of the live reader study prior to broad commercial deployment
3. Ongoing post-market surveillance as defined in Section 5

**Overall Residual Risk Evaluation: ACCEPTABLE — Subject to confirmation after live clinical study.**

---

## 5. Post-Market Surveillance Signals

| Signal | Source | Frequency | Threshold for Action |
|--------|--------|-----------|---------------------|
| Critical FN rate | P12 RWE module | Quarterly | >2% triggers model review |
| Override rate | Audit log analysis | Monthly | >15% spike triggers investigation |
| PSI (finding distribution drift) | Drift detection | Continuous/Monthly | PSI >0.2 triggers alert |
| CSI (baseline score drift) | Drift detection | Continuous/Monthly | CSI >0.15 triggers alert |
| Security incidents | SOC/Incident log | Continuous | Any critical incident = immediate escalation |
| System uptime | Monitoring | Continuous | <99.5% triggers SLA review |
| Configuration change anomalies | Audit log | Monthly | Unexpected changes trigger review |
| User error reports | Support tickets | Ongoing | Pattern analysis quarterly |
| Adverse events | Customer reports | Ongoing | Any SSI linked to AI use = immediate investigation |
| Novel instrument types | Hospital reports | Quarterly | Novel types flagged for retraining cycle |

---

## 6. Risk Management Summary Statement

This Risk Management File has been prepared in accordance with ISO 14971:2019 for LumenAI Version 1.0. Twelve hazards were identified, analyzed, and mitigated. After implementation of risk controls, all residual risks are within the Acceptable range.

The highest initial risk was H-01 (False Negative — Contamination Missed, RPN 15 = Unacceptable), reduced to RPN 4 (Acceptable) through mandatory human-in-the-loop controls, image quality validation, and dual sign-off for critical findings. This risk control strategy is fundamental to LumenAI's safety architecture.

**This Risk Management File requires review and approval by the Risk Management Team and qualified regulatory counsel before submission to any regulatory authority.**

| Role | Name | Signature | Date |
|------|------|-----------|------|
| Regulatory Affairs Lead | [TBD] | [Pending] | [Pending] |
| Clinical Validation Lead | [TBD] | [Pending] | [Pending] |
| Software Engineering Lead | [TBD] | [Pending] | [Pending] |
| Quality Manager | [TBD] | [Pending] | [Pending] |
