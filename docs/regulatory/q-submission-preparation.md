# Q-Submission (Pre-Submission Meeting) Preparation
LumenAI | Regulatory Affairs | Target: Q4 2026
**Subject to regulatory counsel review before submission to FDA.**

## Purpose
A Q-submission (Pre-Sub) meeting with FDA provides an opportunity to:
1. Confirm the regulatory pathway (510(k) vs. De Novo vs. non-device)
2. Obtain FDA feedback on the proposed clinical evidence package
3. Discuss the AI/ML Predetermined Change Control Plan (PCCP)
4. Clarify cybersecurity submission requirements
5. Reduce submission uncertainty before filing

## Questions for FDA

### Q1: Regulatory Pathway Confirmation
"Does FDA agree that LumenAI's Computer Vision Detection module (Module A), which assists trained
SPD technicians in identifying visual contamination and structural defects in reusable surgical
instruments, is appropriately classified as a Class II device pursuable via 510(k)?"

### Q2: 21st Century Cures CDS Exemption
"Do Modules C–H (Predictive Failure Analytics, Inspection Copilot, Regulatory Automation,
Benchmarking, Vendor Intelligence, Digital Twin) qualify for the CDS non-device exemption
under 21st Century Cures, given that each module displays its basis for recommendation and
requires mandatory human review before action?"

### Q3: Clinical Evidence Adequacy
"Is a multi-reader, multi-case (MRMC) study with [N=500 cases, 35 readers across 5 SPD
professional roles, ground truth by expert consensus] an adequate clinical evidence design
for a 510(k) submission for this intended use?"

### Q4: Performance Acceptance Thresholds
"Are the following performance thresholds appropriate for the primary endpoint:
- Overall Cohen's kappa ≥ 0.80 (AI vs. expert consensus)
- Critical finding (crack, corrosion, insulation) sensitivity ≥ 95%
- Critical finding false negative rate ≤ 2%"

### Q5: AI/ML PCCP
"Does FDA have feedback on the structure of our Predetermined Change Control Plan for
AI/ML model updates? Specifically, the proposed pre-specified performance thresholds,
drift monitoring methodology (PSI/CSI), and 5-step human approval chain?"

### Q6: Cybersecurity
"Is CycloneDX-format SBOM acceptable for the cybersecurity section of the submission?
Are there specific threat modeling formats preferred?"

## Submission Package for Pre-Sub Meeting
Attach to Q-submission request:
1. Cover letter with meeting request and questions
2. Device description (2-3 pages)
3. Intended use statement (from intended-use-and-claims-boundary.md)
4. Proposed regulatory pathway hypothesis
5. Proposed clinical study design summary
6. Draft performance thresholds
7. Software description (IEC 62304 summary)
8. Preliminary risk management summary

## Timeline
| Activity | Target |
|----------|--------|
| Regulatory counsel engaged | Q2 2026 |
| Q-submission package drafted | Q3 2026 |
| Q-submission filed with FDA | Q4 2026 |
| FDA response (typically 90 days) | Q1 2027 |
| 510(k) submission | Q2 2027 |
| FDA decision (90-day review) | Q4 2027 |
| Clearance + launch | Q4 2027 |

## FDA Contact
- Submit via FDA eSTAR system or email to the appropriate review division
- Division of Infection Control Devices or Digital Health Center of Excellence (DHCE)
- Reference product code: QMF (Computer-Aided Detection) or request new product code
