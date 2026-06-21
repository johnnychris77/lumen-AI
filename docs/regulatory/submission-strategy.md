# LumenAI Regulatory Submission Strategy
**Version**: 1.0-DRAFT | **Status**: In Review | **Classification**: Regulatory Confidential
**Subject to regulatory counsel review before any FDA engagement.**

---

## 1. Intended Use

LumenAI is a software platform designed to assist trained Sterile Processing Department (SPD) technicians and quality professionals in reviewing and documenting the visual inspection of surgical instruments, including detection of potential contamination (blood, bone, tissue, residue), physical defects (cracks, corrosion, pitting), identification failures (barcode, UDI, QR, KeyDot), and comparison against manufacturer-approved baselines.

**All outputs are intended to support, not replace, the judgment of qualified human professionals.**

---

## 2. Indications for Use

For use by trained SPD technicians, SPD educators, SPD managers, infection prevention specialists, and quality leaders in hospital and ambulatory surgery center sterile processing departments for documentation, quality tracking, workflow management, and instrument inspection support.

- **Not for diagnostic use.**
- **Not for direct patient care decisions.**
- **Not for determination of instrument sterility** (sterility determination requires biological indicators and validated sterilization process controls).

---

## 3. User Population

| User Type | Experience Level | Primary Use |
|-----------|-----------------|-------------|
| SPD Technicians (Entry-Level) | 0–2 years, certified or in certification | Inspection documentation, image capture |
| SPD Technicians (Senior) | 2+ years, CRCST certified | Inspection review, AI finding confirmation |
| SPD Educators | 3+ years, educational role | Training, quality review |
| SPD Supervisors/Managers | 5+ years, supervisory role | Quality oversight, trend review |
| Infection Prevention Nurses | CIC certified | Quality and safety correlation review |
| Quality Directors | Healthcare quality leadership | Executive dashboards, compliance reports |
| Hospital Administrators | Administrative role | Benchmarking, ROI reporting |

Users are trained healthcare professionals operating in professional healthcare environments. This system is not intended for use by patients or untrained laypersons.

---

## 4. Deployment Environment

- **Primary setting**: Hospital SPD departments, ambulatory surgery centers (ASCs), central sterile supply departments
- **Architecture**: Cloud-hosted SaaS (AWS/Kubernetes) with optional mobile/offline mode for point-of-use inspection
- **Contact with patients**: None — not implanted, not life-sustaining, not in direct contact with patients
- **Connectivity requirements**: Minimum 10 Mbps for image upload; offline mode supported with browser-based IndexedDB storage

---

## 5. Human Review Requirements

ALL AI-generated findings require human review and confirmation before any quality action is taken. Specific controls:

1. No system output automatically triggers patient care decisions.
2. The system is advisory only — all findings are labeled as requiring human confirmation.
3. Override of AI findings is always available and logged.
4. Critical findings require explicit acknowledgment before the user may proceed.
5. Module H (Patient Safety Intelligence) outputs always carry disclaimer: "potential association for human review — does not establish causation."

---

## 6. Claim Boundaries

### 6.1 What LumenAI Claims

- Assists in visual inspection documentation
- Flags potential contamination for human review
- Compares instrument images to approved manufacturer baselines
- Tracks inspection history and quality trends
- Generates audit-ready reports
- Supports regulatory compliance documentation (AAMI ST79, TJC, DNV)
- Identifies potential associations between quality signals and safety events (for human review)

### 6.2 What LumenAI Does NOT Claim

- Does not diagnose patient conditions
- Does not determine instrument sterility (sterility requires biological indicators and sterilization process controls)
- Does not replace qualified SPD technician judgment
- Does not claim causation between instrument quality and patient outcomes
- Does not replace AAMI/ANSI sterilization validation processes
- Does not provide clinical diagnosis or treatment recommendations
- Does not assert that any instrument is safe for use — all pass/fail determinations remain with the human reviewer

---

## 7. Regulatory Pathway Analysis

### 7.1 Non-Device Software (21st Century Cures Act Exclusion)

**Assessment**: Under the 21st Century Cures Act (Section 3060), certain software functions are excluded from device regulation:

- Administrative functions (scheduling, billing, workflow) — **Applies to Modules G, H (administrative aspects), and Module F (benchmarking)**
- Electronic health record software — **Not applicable**
- General wellness functions — **Not applicable**
- Functions intended to transfer, store, convert formats, or display clinical laboratory test results — **Not applicable**

**Conclusion**: Modules E (Vendor Intelligence), F (Benchmarking), G (Workflow/Predictive), and H (Administrative reporting aspects) likely qualify as non-device software under the Cures Act exclusion. Module A (CV Detection) and Module B (AI Ranking) likely **do not qualify** — they analyze images of instruments to inform quality decisions, which resembles device functionality regulated under 21 CFR Part 880.

### 7.2 Clinical Decision Support (CDS) Exemption

**Assessment**: Under 21 USC 360j(o), software qualifies for the CDS exemption if it:
1. Is not intended to replace clinical judgment of a healthcare professional
2. Is intended to enable the clinician to independently review the basis of the recommendations
3. Is intended for use by a licensed healthcare professional

**Module A Analysis**: The basis of the AI recommendation (raw computer vision model weights and intermediate feature maps) is not readily and independently reviewable by the end user without specialized ML expertise. While confidence scores are displayed, the underlying reasoning is not transparent in a manner that allows independent verification by an SPD technician.

**Conclusion**: Partial applicability. Administrative and workflow modules (E, F, G, H) may qualify. The CV detection module (Module A) likely does **not** qualify for the CDS exemption due to opacity of model reasoning. Regulatory counsel review required.

### 7.3 Enforcement Discretion

**Assessment**: FDA has exercised enforcement discretion for certain Software as a Medical Device (SaMD) categories during development and early commercialization phases. This may apply to limited early access deployments.

**Conclusion**: Possible for limited early commercial deployment under a controlled research use agreement. **Not a long-term strategy and not a substitute for clearance.** This pathway requires active engagement with FDA and does not confer legal marketing authorization.

### 7.4 510(k) Premarket Notification Pathway

**Assessment**: The 510(k) pathway requires demonstration of substantial equivalence to a legally marketed predicate device. Relevant predicate categories include:

- Computer-aided detection (CADe) devices for other imaging modalities (e.g., radiology, pathology)
- Quality control imaging systems cleared under 21 CFR 892.2050 or similar
- See docs/clinical/510k-predicate-analysis.md for predicate search results

**Requirements**:
- Substantial equivalence to predicate: same intended use AND same technological characteristics (or different characteristics without raising new safety/effectiveness questions)
- Clinical study data meeting primary endpoint: Cohen's kappa ≥ 0.80 vs. expert human panel
- Estimated review timeline: 12–18 months from submission acceptance
- Requires Special 510(k) review if change to cleared device; Traditional 510(k) for novel device with predicate

**Conclusion**: Viable pathway for Module A (CV Detection) if a suitable predicate device is identified. Predicate search is ongoing (see 510k-predicate-search-log.md).

### 7.5 De Novo Classification Request

**Assessment**: If no suitable predicate is identified for Module A, the De Novo pathway creates a new device classification (Class I or Class II) with special controls. This pathway:
- Establishes LumenAI as a predicate for future devices
- Typically requires more extensive clinical data than 510(k)
- Estimated timeline: 24–36 months
- Can result in Class II classification with special controls (algorithm performance benchmarks, human factors requirements, post-market monitoring)

**Conclusion**: Fallback pathway if 510(k) predicate search is unsuccessful. Should be explored in parallel with 510(k) predicate research.

---

## 8. Recommended Regulatory Strategy

| Module | Recommended Pathway | Rationale | Timeline |
|--------|--------------------|-----------|----|
| Module A — CV Detection | 510(k) | Likely SaMD; predicate search underway | 18–24 months post-study |
| Module B — AI Ranking | 510(k) bundled with A | Accessory to CV detection | Same as A |
| Module C — Baseline Intelligence | 510(k) bundled | Supports CV inspection | Same as A |
| Module D — Identification | 510(k) bundled or CDS | Barcode/UDI decoding; likely CDS-eligible | 12–18 months |
| Module E — Vendor Intelligence | Non-Device / CDS | Administrative/quality tracking | Current |
| Module F — Benchmarking | Non-Device | Anonymized network analytics | Current |
| Module G — Predictive Analytics | Non-Device / CDS | Labeled as estimates; human review required | Current |
| Module H — Patient Safety Intelligence | Non-Device / CDS | Association only; causation disclaimed | Current |
| Module I — Mobile Platform | Follows primary modules | Platform, not decision-making | Follows A |
| Module J — Security Infrastructure | Non-Device | Administrative | Current |

### 8.1 Immediate Next Steps

1. **Pre-Submission (Q-Submission) Meeting**: Schedule Q-Sub meeting with FDA Center for Devices and Radiological Health (CDRH) to discuss intended use, proposed predicate, and clinical study design. See docs/regulatory/q-submission-preparation.md.
2. **Regulatory Counsel Engagement**: Retain FDA regulatory counsel to confirm pathway determination and predicate analysis.
3. **Clinical Validation Study**: Design and initiate real-world multi-site clinical validation study (see clinical-evidence-package.md for gap analysis).
4. **Human Factors Program**: Initiate formative human factors evaluation (see human-factors-validation-plan.md).
5. **QMS Establishment**: Establish formal Quality Management System meeting 21 CFR Part 820 / ISO 13485 (see qms-readiness-gap-analysis.md).

---

## 9. Regulatory Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| No suitable 510(k) predicate found | Medium | High | Begin De Novo analysis in parallel |
| Clinical study fails kappa ≥ 0.80 | Medium | High | Algorithm improvement plan; threshold analysis |
| FDA reclassifies as Class III | Low | Very High | Engage pre-submission early; CDS exemption argument |
| Human factors critical use errors exceed threshold | Medium | High | Iterative design improvement before summative study |
| QMS not established before submission | High | High | Immediate QMS program initiation |

---

*Document Owner: Regulatory Affairs Lead | Review Cycle: Quarterly | Next Review: 2026-09-21*
*This document is a planning artifact. It does not constitute FDA guidance, legal advice, or regulatory clearance.*
