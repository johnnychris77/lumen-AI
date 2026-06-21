# Clinical Safety Review
Version: 1.0 | ISO 14971 Risk Management

## 1. Intended Use

LumenAI is a Software as a Medical Device (SaMD) Decision Support system.
It assists SPD technicians in identifying instrument contamination, structural defects,
and tracking/identification failures. It does NOT make autonomous clinical decisions —
all findings require technician review and sign-off.

**Intended users:** SPD Technicians (CRCST certified), SPD Educators, SPD Managers,
Infection Prevention Specialists

**Use environment:** Hospital Sterile Processing Department (SPD) / Central Sterile
Supply Department (CSSD); controlled environment with standardized lighting

**Contraindications:** LumenAI is not intended for:
- Autonomous instrument pass/fail without human review
- Diagnosis or treatment of patient conditions
- Real-time intraoperative instrument assessment
- Assessment of single-use devices (classification may differ)

---

## 2. Risk Classification

- **FDA:** Class II (moderate risk), 510(k) pathway
  (21 CFR Part 880 — General Hospital and Personal Use Devices)
- **EU MDR:** Class IIa (Annex VIII, Rule 11 — SaMD)
- **Risk level:** MEDIUM (supports, does not replace, human decision)
- **Software Safety Class (IEC 62304):** Class B (serious injury possible if software fails)

**Rationale for Class II / Class B:**
LumenAI provides decision support that influences (but does not control) whether a
contaminated or defective instrument is returned to clinical service. A false negative
could result in an undetected contaminated instrument being used in a subsequent
surgical procedure, with potential for surgical site infection (SSI) or device failure.
However, mandatory technician review before instrument release provides a critical
human safety barrier.

---

## 3. Hazard Analysis (ISO 14971 Table)

**Risk Priority Number (RPN) = Probability (1-5) × Severity (1-5)**

| Hazard ID | Hazard | Harm | Probability | Severity | RPN | Mitigation |
|-----------|--------|------|-------------|----------|-----|------------|
| H-01 | False Negative on contamination | Patient SSI | Low (2) | Critical (5) | 10 | Mandatory human review; sensitivity threshold ≥95%; UI "AI-assisted, not definitive" |
| H-02 | False Positive causes unnecessary discard | Instrument shortage affecting surgical schedule | Medium (3) | Minor (2) | 6 | FP rate monitoring; technician override workflow with audit log |
| H-03 | AI confidence misinterpreted as certainty | Technician skips visual check | Low (2) | Moderate (3) | 6 | UI shows "AI-assisted, not definitive" on all findings; confidence score displayed |
| H-04 | Model drift reduces accuracy post-deployment | Degraded detection; missed findings | Low (2) | Moderate (3) | 6 | Quarterly drift monitoring (PSI/CSI); automated alert if PSI > 0.2 |
| H-05 | Data breach exposes audit evidence | HIPAA violation; reputational harm | Low (2) | Moderate (3) | 6 | Encryption at rest+transit; RBAC; immutable audit logs; SOC 2 Type II |
| H-06 | Incorrect UDI/barcode read | Wrong instrument tracked; traceability failure | Low (2) | Minor (2) | 4 | Dual-read with confidence score; technician confirm before commit |

**Risk matrix key:**
- Probability: 1=Negligible, 2=Remote, 3=Occasional, 4=Probable, 5=Frequent
- Severity: 1=Negligible, 2=Minor, 3=Moderate, 4=Major, 5=Critical
- RPN ≥ 15: Unacceptable; RPN 8–14: ALARP review required; RPN < 8: Acceptable

All identified hazards have RPN < 15 after mitigation. No unacceptable residual risks.

---

## 4. Escalation Workflow

1. AI flags finding with severity ≥ HIGH (confidence ≥ 0.85 on critical category)
2. P9 Copilot generates escalation event with finding details
3. Supervisor notified (in-app alert + optional email/Slack integration)
4. Technician must explicitly **accept** or **override** AI finding:
   - **Accept:** Finding logged; instrument quarantined for reprocessing or discard per IFU
   - **Override:** Reason text required; for CRITICAL findings, supervisor co-sign required
5. If override: reason captured in audit log (immutable; cannot be edited or deleted)
6. All escalations visible in P8 Regulatory Dashboard for supervisor review
7. Critical finding escalations reviewed at monthly CVC meeting (aggregate data)

**Override reasons (standardized list, free text also accepted):**
- Visual inspection confirms no defect
- Image quality insufficient for AI determination
- Instrument confirmed cleaned and re-inspected
- IFU criteria do not require rejection for this finding type
- Other (free text required)

---

## 5. Override Workflow

- Any AI finding can be overridden by the technician
- **Override requirements:**
  - Role: ≥ SPD Technician (CRCST)
  - Reason text: required (minimum 20 characters)
  - Supervisor co-sign: required for CRITICAL findings (crack, corrosion, insulation)
- **All overrides are permanent audit log entries** (no edit/delete capability)
- Override rate monitored as a KPI:
  - Override rate > 20% per category: triggers model review
  - Override rate > 40% overall: triggers CVC escalation and potential revalidation

---

## 6. Safety Controls

| Control | Implementation | Monitoring |
|---------|---------------|-----------|
| Minimum confidence threshold | 0.70 — findings below show "low confidence" banner | P12 validation engine |
| Critical finding FN rate alert | If > 2%, auto-notification to CVC | P12 quarterly report |
| Model version pinning | Deployed models immutable; hash-verified at startup | CI/CD pipeline |
| Human review gate | No instrument released without technician sign-off | Workflow enforcement |
| Offline mode | If AI unavailable, app shows manual checklist only | Health check / liveness probe |
| Audit log integrity | Immutable ledger with event hashing (P1) | Tamper detection |

---

## 7. Residual Risks

| Risk | Residual Level | Acceptability |
|------|---------------|--------------|
| FN rate on non-critical findings (blood, bone, tissue) | ≤ 5% | ALARP — acceptable with mandatory human review |
| FP rate across all categories | ≤ 15% | Acceptable (workflow disruption only) |
| Model performance degradation between validations | Monitored via PSI/CSI | ALARP |
| **FN rate on critical findings (crack, corrosion, insulation)** | **≤ 2%** | **Unacceptable if exceeded — immediate action required** |

---

## 8. Post-Market Surveillance

### 8.1 Routine Monitoring
- **Quarterly performance reports** generated by P12 validation engine
  (includes FP/FN rates, drift metrics, override rates)
- **Monthly:** CVC review of escalation log and critical finding overrides
- **Annual:** Full re-validation against updated ground truth dataset

### 8.2 Adverse Event Reporting
- **FDA Medical Device Report (MDR):** Required within 30 days of becoming aware
  of device malfunction that could cause or contribute to serious injury
  (21 CFR Part 803)
- **EU IVDR/MDR:** Report to competent authority within applicable timelines
- **Internal:** Document in corrective action system; CVC notified within 24 hours

### 8.3 Trend Analysis
- P7 Predictive Analytics monitors instrument failure correlation with CV findings
- P12 PSI/CSI drift detection provides early warning of model degradation
- Annual correlation analysis: LumenAI finding rates vs. site SSI rates
  (where data available under data sharing agreements)

### 8.4 Revalidation Decision Tree
```
Performance metric drops > 5%?
├── Yes → Initiate drift investigation
│         ├── Root cause: data shift → update training data → mini-validation
│         ├── Root cause: model issue → model remediation → full re-validation
│         └── Root cause: environmental (camera, lighting) → site recalibration
└── No → Continue quarterly monitoring
```
