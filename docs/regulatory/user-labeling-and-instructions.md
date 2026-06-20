# User Labeling and Instructions for Use
LumenAI Surgical Instrument Inspection Software | Version 1.0
**DRAFT — For regulatory review prior to final labeling approval.**
**Subject to regulatory counsel review.**

---

## Intended Use Statement (Label Text)

LumenAI is a software-based decision support tool that assists trained Sterile Processing
Department (SPD) professionals in the visual inspection of reusable surgical instruments.
The software provides AI-generated findings to support — not replace — the judgment of
qualified SPD technicians. All findings require human review before instrument disposition.

---

## WARNINGS

WARNING: FOR DECISION SUPPORT ONLY. This software does not replace the visual inspection
judgment of qualified SPD professionals.

WARNING: DO NOT release instruments for patient use based solely on AI-generated findings.
A qualified SPD technician must review and accept all findings.

WARNING: CRITICAL FINDINGS (cracks, corrosion, insulation damage) flagged by the system
require immediate supervisor review before the instrument is returned to service.

WARNING: SYSTEM LIMITATIONS: AI performance degrades with poor image quality (motion blur,
inadequate lighting, occlusion). Inspect image quality before relying on AI findings.

WARNING: NOT VALIDATED FOR: Implantable devices, point-of-care without SPD infrastructure,
autonomous use without trained personnel oversight.

WARNING: PERFORMANCE DATA: At Version 1.0, performance metrics are derived from
mock/simulated data. Live clinical study is pending. Do not rely solely on published
performance figures for clinical decision-making.

---

## Required System Qualifications

- Users must be trained SPD professionals (CRCST or equivalent in-training under supervision)
- Users must complete LumenAI onboarding training before clinical use
- Image capture must follow the LumenAI Image Acquisition Protocol (see Section 5)
- Supervisor (CHL or equivalent) must be designated for escalation workflow
- IT Administrator must complete LumenAI system configuration training before deployment

---

## 1. Device Description

LumenAI is a cloud-based SaaS (Software as a Service) platform accessible via standard web
browser. It provides the following functions:

1. **AI-assisted instrument inspection**: Upload instrument images; receive AI-generated
   findings with confidence scores and severity classification
2. **Inspection tracking**: Record all inspection events with technician identity, timestamp,
   and decision
3. **Instrument lifecycle tracking**: UDI, barcode, and QR code-based instrument identity
   and history
4. **Escalation management**: Automated supervisor notification for critical findings
5. **Audit log**: Immutable record of all inspection activities
6. **Accreditation support**: AAMI/JC/CMS/FDA/ISO self-assessment tools (administrative)
7. **Analytics**: Throughput dashboards; defect trend analysis; benchmarking

---

## 2. Intended Users

| User Role | Required Qualification |
|-----------|----------------------|
| SPD Technician | CRCST certification or equivalent in-training under supervisor oversight |
| SPD Educator | CS educator certification |
| SPD Manager | CHL (Certified Healthcare Leader) or equivalent |
| Infection Prevention Specialist | CIC (Certified in Infection Control) |
| IT Administrator | System administration training; no clinical certification required |

---

## 3. Intended Environment

LumenAI is intended for use in:
- Hospital Sterile Processing Departments
- Ambulatory surgery center SPD areas
- Central sterile services in healthcare systems

LumenAI is NOT intended for:
- Home use
- Point-of-care environments without dedicated SPD infrastructure
- Autonomous operation without qualified personnel oversight
- Intraoperative surgical guidance
- Any environment where AI findings would be acted upon without human review

---

## 4. Contraindications

Do not use LumenAI as the sole basis for instrument disposition decisions.

Do not use LumenAI to inspect implantable devices (not validated for this use).

Do not use LumenAI to quantify microbial bioburden — AI findings indicate visual
contamination only and do not predict sterility assurance.

Do not disable or bypass the mandatory human sign-off workflow under any circumstances.

---

## 5. Image Quality Requirements

The accuracy of AI findings depends critically on image quality. The following standards
must be met before relying on AI findings:

| Parameter | Requirement |
|-----------|------------|
| Minimum resolution | 1920 x 1080 pixels |
| Lighting | Adequate; ring light recommended (5000K color temperature) |
| Capture distance | 20-30 cm from instrument |
| Instrument state | Clean, dry, fully opened/unfolded, standard orientation |
| Motion blur | None acceptable |
| Glare | Minimal; reposition light source if glare covers inspection area |
| Occlusion | Less than 30% of instrument visible surface must be unoccluded |

Images failing these quality criteria will generate a system warning. The technician must
re-capture the image before relying on AI findings for that image.

---

## 6. Step-by-Step Operating Instructions

### 6.1 Login and Session Setup
1. Navigate to your facility's LumenAI URL
2. Enter credentials (username and password)
3. Complete MFA verification (Manager and Admin roles)
4. Verify you are logged in under the correct facility (displayed in header)

### 6.2 Starting an Inspection
1. Select "New Inspection" from the dashboard
2. Scan or manually enter instrument ID (barcode, UDI, QR code, or KeyDot)
3. System displays instrument identity, type, and inspection history
4. Confirm instrument identity before proceeding (visual verification required)
5. Capture image(s) per Image Quality Requirements (Section 5)
6. Upload image(s) to LumenAI system

### 6.3 Reviewing AI Findings
1. System displays AI-generated findings with:
   - Finding type (contamination category or defect type)
   - Confidence score (0.0-1.0)
   - Severity classification (LOW, MEDIUM, HIGH, CRITICAL)
   - Bounding box overlay on image (where applicable)
2. Review each finding carefully:
   - HIGH CONFIDENCE (>=0.90): Finding is reliable; human review still required
   - MEDIUM CONFIDENCE (0.70-0.89): Review carefully; consider re-imaging
   - LOW CONFIDENCE (<0.70): Finding is unreliable; perform full manual inspection;
     LOW CONFIDENCE banner displayed prominently
3. Do not accept findings without reviewing the underlying image

### 6.4 Accepting or Overriding Findings
**Accept**: If you agree with the AI finding, select "Accept" for each finding.

**Override**: If you disagree with the AI finding:
1. Select "Override"
2. Enter override reason (mandatory — field cannot be left blank)
3. For CRITICAL findings: supervisor co-signature is required before override is finalized
4. Override is permanently recorded in audit log and cannot be deleted or modified

### 6.5 Instrument Disposition
After reviewing all findings:
1. Select disposition: PASS (return to service), FAIL (remove from service), or HOLD (re-inspection needed)
2. For CRITICAL findings: supervisor review required before PASS disposition
3. Confirm disposition with your credential (electronic signature)
4. System records disposition decision in immutable audit log

### 6.6 Escalation Workflow
If AI finding is CRITICAL severity:
1. System automatically notifies designated supervisor (in-app notification + configurable alert)
2. Technician and supervisor must both review the finding
3. Instrument is automatically quarantined pending supervisor review
4. Supervisor must log in and co-sign the disposition decision
5. All actions timestamped and recorded in audit log

---

## 7. Interpretation Guidance

### 7.1 Confidence Score Interpretation
| Confidence Score | AI Finding Reliability | Required Action |
|----------------|----------------------|----------------|
| 0.90-1.00 | High reliability | Review and confirm; human sign-off required |
| 0.70-0.89 | Moderate reliability | Review carefully; consider re-imaging if uncertain |
| 0.50-0.69 | Low reliability | LOW CONFIDENCE banner shown; full manual inspection required |
| 0.00-0.49 | Very low reliability | AI finding should be disregarded; full manual inspection required |

### 7.2 Severity Classification
| Severity | Definition | Required Response |
|---------|-----------|------------------|
| CRITICAL | Defect poses direct patient safety risk if instrument used | Immediate quarantine; supervisor review; dual sign-off required |
| HIGH | Significant defect likely requiring instrument removal | Senior technician or supervisor review recommended |
| MEDIUM | Defect present; clinical significance uncertain | Technician review; document decision rationale |
| LOW | Minor finding; may not require action | Technician review; document decision rationale |

### 7.3 When to Perform Full Manual Inspection (Regardless of AI Finding)
- Any finding with confidence <0.70
- Any CRITICAL severity finding
- Instrument type not recognized by system ("Unvalidated instrument" message)
- Image quality warning displayed
- Any suspicion that the image does not accurately represent the instrument

---

## 8. Override Procedure

Overrides are a normal and expected part of LumenAI operation. Technicians are expected
to exercise professional judgment. The override system is designed to capture that
judgment, not to discourage it.

Override process:
1. Select "Override" on any AI finding you disagree with
2. Enter your override reason (select from list or enter free text; mandatory)
3. CRITICAL finding overrides require supervisor co-signature
4. Override is permanently logged with your user ID, timestamp, and reason
5. Overrides cannot be deleted or modified after submission
6. Audit reports include override rates for quality monitoring

High override rates may indicate AI model drift, image quality issues, or training
needs. Supervisors should review override patterns monthly.

---

## 9. Audit Trail

LumenAI maintains an immutable audit log of all inspection events, including:
- User login and logout events
- Inspection initiation
- Image uploads
- AI findings generated (with confidence scores)
- Technician acceptance or override decisions
- Override reasons
- Supervisor co-signatures
- Instrument disposition decisions
- System configuration changes
- User account changes

Audit records:
- Cannot be deleted or modified by any user (including administrators)
- Are retained for a minimum of 7 years
- Can be exported as PDF for regulatory inspection, legal review, or accreditation surveys
- Are encrypted and backed up daily

---

## 10. Fallback Procedure (System Unavailable)

If LumenAI is unavailable:
1. Notify IT administrator immediately
2. Revert to facility's manual inspection protocol (AAMI ST79 or facility SOP)
3. Document all inspections performed manually during outage in paper or alternative system
4. Record outage start and end time
5. Do not delay critical surgical cases due to LumenAI unavailability — manual inspection is the baseline
6. Report outage to LumenAI support at support@lumenai.com

---

## 11. Training Requirements

All users must complete LumenAI training before clinical use:

| User Role | Required Training Modules |
|-----------|--------------------------|
| SPD Technician | System orientation; inspection workflow; image capture; override procedure; escalation |
| SPD Educator | All technician modules + quality review; override pattern analysis |
| SPD Manager | All educator modules + dashboard; user management; escalation management |
| Infection Prevention Specialist | Read-only access training; trend analysis tools |
| IT Administrator | System configuration; user management; audit export; security settings |

Training completion is recorded in LumenAI system and required before clinical access is granted. Training records are retained for 7 years.

---

## 12. Maintenance Requirements

| Activity | Frequency | Responsible |
|---------|----------|------------|
| Image capture equipment calibration | Per manufacturer specification | IT Administrator / Biomedical Engineering |
| LumenAI software updates | Per release schedule (applied automatically or with IT approval) | IT Administrator |
| User account review | Quarterly (or upon staff change) | SPD Manager / IT Administrator |
| Training currency verification | Annual | SPD Manager |
| Audit log review | Monthly | SPD Manager |
| Backup verification | Automated daily (LumenAI system) | LumenAI Operations |

---

## 13. Unsupported Use Cases

The following uses are explicitly not supported and should not be attempted:

- Microbiology or bioburden quantification
- Patient diagnosis or clinical decision-making
- Autonomous sterilization cycle control
- Intraoperative surgical guidance
- Implant assessment or clearance
- Any use without qualified SPD professional review of AI findings
- Inspection of instruments in facilities without trained SPD staff

---

## 14. Technical Support

| Contact Type | Contact |
|-------------|---------|
| System errors and technical issues | support@lumenai.com |
| Clinical safety concerns | Contact your facility's Infection Prevention Officer |
| Cybersecurity incidents or suspected breach | security@lumenai.com |
| Regulatory questions | regulatory@lumenai.com |
| Emergency (patient safety concern) | Contact facility Risk Management immediately; then support@lumenai.com |

---

## 15. Symbols and Abbreviations

| Symbol/Abbreviation | Meaning |
|--------------------|---------|
| AAMI | Association for the Advancement of Medical Instrumentation |
| CHL | Certified Healthcare Leader |
| CIC | Certified in Infection Control |
| CRCST | Certified Registered Central Service Technician |
| FN | False Negative |
| FP | False Positive |
| IFU | Instructions for Use |
| JC | The Joint Commission |
| SPD | Sterile Processing Department |
| SSI | Surgical Site Infection |
| UDI | Unique Device Identifier |
| WARNING | Important safety information; failure to follow may result in harm |

---

*LumenAI Version 1.0 | Instructions for Use | DRAFT*
*For regulatory review by qualified regulatory counsel before final labeling approval.*
*LumenAI does not claim FDA clearance. Regulatory submission is in preparation.*
