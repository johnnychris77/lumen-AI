# 510(k) Predicate Device Substantial Equivalence Analysis

## 1. Device Description
**Subject Device:** LumenAI Surgical Instrument Inspection Software
**Device Type:** Software as a Medical Device (SaMD)
**Intended Use:** AI-assisted visual inspection of reusable surgical instruments in SPD
**Indications for Use:** Intended to assist SPD professionals in identifying contamination,
structural defects, and tracking failures on reusable surgical instruments prior to sterilization.
Not intended to replace human judgment or serve as the sole basis for instrument release decisions.

## 2. Predicate Device Identification

| Field | Predicate 1 | Predicate 2 |
|-------|-------------|-------------|
| Device Name | Canfield VECTRA Imaging System | Olympus OER-Pro Endoscope Reprocessor |
| 510(k) Number | K201234 (example) | K183456 (example) |
| Device Class | Class II | Class II |
| Product Code | QMF (AI-aided detection) | FRN (reprocessing equipment) |
| Predicate Use | AI-assisted image analysis | Instrument reprocessing quality |

*Note: Actual 510(k) numbers must be confirmed via FDA 510(k) database search at time of submission.*

## 3. Substantial Equivalence Comparison

| Feature | Subject Device | Predicate | Equivalent? |
|---------|---------------|-----------|-------------|
| Intended use | SPD instrument inspection | Image-based quality inspection | Yes |
| Technology | Computer vision AI (CNN) | Camera + image processing | Different — same safety profile |
| Decision support only | Yes — human review required | Yes | Yes |
| No direct patient contact | Yes | Yes | Yes |
| Output: pass/fail recommendation | Yes | Yes | Yes |
| Software-only device | Yes | Yes | Yes |

## 4. Performance Data Requirements
Per FDA guidance on AI/ML-based SaMD:
- Algorithm description and training data summary
- Performance data on independent test set
- Bias and fairness analysis (instrument type, facility type)
- Real-world performance plan (post-market)

## 5. Special Controls (Class II)
- Labeling must state "For decision support only — does not replace clinical judgment"
- Cybersecurity documentation per 2023 FDA guidance
- Post-market performance monitoring plan
- Software version control and change management (IEC 62304)

## 6. Regulatory Pathway Decision Tree
- If kappa ≥ 0.80 AND FN_critical ≤ 2%: Proceed with 510(k) traditional pathway
- If performance below thresholds: De Novo request or additional clinical data
- International: CE Mark (EU MDR Class IIa), Health Canada Class II, TGA Class IIa

## 7. Submission Timeline (Estimated)
| Milestone | Target |
|-----------|--------|
| Multi-site reader study complete | Q3 2026 |
| Sealed test set evaluation | Q4 2026 |
| Pre-submission meeting with FDA (Q-submission) | Q4 2026 |
| 510(k) submission | Q1 2027 |
| FDA review (90-day standard) | Q2 2027 |
| Clearance + market launch | Q3 2027 |
