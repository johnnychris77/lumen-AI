# Intended Use and Claims Boundary
LumenAI | Version 1.0 | CONFIDENTIAL — Regulatory Strategy Document
**For review by qualified regulatory counsel before use in any submission.**

## 1. Device Name
LumenAI Surgical Instrument Inspection Software

## 2. Intended Use Statement
LumenAI is a software-based decision support tool intended to assist trained Sterile Processing Department (SPD) professionals in the visual inspection of reusable surgical instruments. The software analyzes digital images of instruments and provides AI-generated findings (contamination indicators, structural assessments, and tracking/identification results) to support — not replace — the judgment of qualified SPD technicians.

**All AI-generated findings require review and acceptance by a qualified SPD professional before any instrument disposition decision is made.**

## 3. Intended Users
| User Type | Required Qualification | Role in Workflow |
|-----------|----------------------|-----------------|
| SPD Technician | CRCST certification (or equivalent in-training under supervision) | Primary inspection operator |
| SPD Educator | CS educator certification | Protocol oversight, quality review |
| SPD Manager | CHL or equivalent | Dashboard, escalation review |
| Infection Prevention Specialist | CIC certification | Outbreak investigation, trend review |
| Hospital IT Administrator | None (system administration only) | System configuration, user management |

## 4. Intended Environment
- Hospital Sterile Processing Departments (inpatient, outpatient surgery centers)
- Ambulatory surgery centers with dedicated SPD function
- Central sterile services in healthcare systems
- **Not intended for:** home use, point-of-care without SPD infrastructure, autonomous robot-only environments without human review

## 5. Supported Workflows
1. **Instrument visual inspection** — AI-assisted contamination detection (blood, bone, tissue, residue, corrosion, crack, pitting, insulation damage)
2. **Instrument tracking** — Barcode, UDI, QR, KeyDot identification and traceability
3. **Baseline comparison** — Instrument condition scoring against manufacturer, vendor, and hospital baselines
4. **Inspection ranking** — Prioritization of instruments for urgent re-inspection
5. **Predictive maintenance** — Risk scoring for instrument failure (decision support only)
6. **Regulatory readiness** — JC/AAMI/FDA/CMS/ISO accreditation self-assessment (administrative function)
7. **Vendor/manufacturer intelligence** — Aggregated defect trend analysis (quality management function)
8. **SPD workflow visibility** — Digital twin throughput monitoring (operational function)

## 6. Excluded Workflows (Contraindicated)
- **Autonomous instrument release** — LumenAI must never be the sole basis for releasing an instrument for patient use without human technician sign-off
- **Patient diagnosis or treatment** — LumenAI does not interface with patient clinical data and makes no diagnostic claims
- **Autonomous sterilization control** — LumenAI does not control sterilizers or reprocessing equipment
- **Real-time surgical guidance** — Not intended for intraoperative use
- **Implant assessment** — Not validated for implantable device inspection
- **Microbiology / bioburden quantification** — AI findings indicate visual contamination only; do not quantify microbial load

## 7. Clinical vs. Non-Clinical Claims

### Approved Clinical Claims
| Claim | Evidence Basis | Qualification |
|-------|---------------|---------------|
| "Assists SPD technicians in identifying visual contamination" | P12 validation study (mock; live study pending) | Decision support only |
| "Identifies structural defects including cracks and corrosion in instrument images" | P4 CV module; P12 validation | Advisory finding; human review required |
| "Supports technician compliance with AAMI ST79 inspection protocols" | P8 accreditation module; standards catalogue | Workflow guidance |
| "Provides audit trail for inspection activities" | P0/P1 security; audit log | Administrative/quality claim |

### Prohibited Claims (Do Not Use in Marketing)
- No AI system achieves 100% sensitivity — do not claim "Detects all contamination"
- Do not state or imply that LumenAI "Replaces visual inspection by SPD technicians"
- Do not reference FDA clearance until clearance is obtained
- Do not claim "Prevents surgical site infections" — causal link not established
- Do not claim "Guarantees instrument sterility" — sterility is a process attribute, not a software output
- Do not describe LumenAI as a tool for "Medical diagnosis" — not a diagnostic device

### Non-Clinical Operational Claims (Permitted)
- "Reduces inspection time per instrument" (operational efficiency)
- "Provides dashboard visibility into SPD throughput" (operational)
- "Supports AAMI/JC accreditation preparation" (quality management)
- "Tracks instrument lifecycle and maintenance history" (asset management)

## 8. Human-in-the-Loop Decision Model

```
[Image Capture] --> [AI Analysis] --> [AI Finding + Confidence Score]
                                               |
                                   [SPD Technician Review]
                                         /           \
                                   [Accept]       [Override + Reason]
                                       |                   |
                               [Instrument Decision]  [Audit Log Entry]
                                       |
                               [Supervisor Co-sign if CRITICAL]
```

No instrument disposition may occur based solely on AI output. Human review is mandatory at every decision point.

## 9. Limitations
1. Performance validated on mock/synthetic data; multi-site clinical study pending
2. Image quality-dependent — poor lighting, occlusion, or motion blur degrades accuracy
3. Not validated for novel instrument types not present in training data
4. AI confidence scores are probabilistic, not definitive
5. Predictive failure analytics are decision support; maintenance decisions require engineering judgment
6. Regulatory accreditation scores are self-assessment aids; do not replace formal accreditation surveys

## 10. Marketing Language Guardrails
All marketing, sales, and customer-facing materials must:
- Include: "For decision support only. Does not replace the judgment of qualified SPD professionals."
- Avoid: Absolute performance claims without confidence intervals and study design disclosure
- Avoid: FDA clearance references until clearance is obtained
- Route to: Regulatory Affairs review before publication of any new clinical claim
