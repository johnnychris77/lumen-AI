# SaMD Classification Assessment
LumenAI | Version 1.0
**Preliminary assessment only. Final determination requires qualified regulatory counsel.**

## 1. Background: FDA SaMD Framework
FDA applies a risk-based classification to Software as a Medical Device (SaMD) using:
- **IMDRF SaMD Framework**: Significance of information provided x Healthcare situation
- **FDA 21st Century Cures Act CDS Exemption**: Non-device CDS if it displays the basis for recommendations and a clinician can independently review
- **FDA Software Policy (2022 draft guidance)**: Device vs. non-device CDS distinction

## 2. Module-by-Module Assessment

### Module A: Computer Vision Detection (P4)
| Attribute | Assessment |
|-----------|-----------|
| Function | Analyzes images of surgical instruments to identify contamination and defects |
| Information significance | Identifies conditions relevant to infection prevention |
| Healthcare situation | Serious condition (SSI prevention) |
| Preliminary IMDRF risk | Category III (significant x serious) |
| Human review required | Yes — mandatory technician sign-off |
| Probable FDA pathway | 510(k) (Class II, with predicate) |
| CDS exemption eligible | Uncertain — depends on final intended use framing |

### Module B: AI Inspection Ranking Engine (P3)
| Attribute | Assessment |
|-----------|-----------|
| Function | Prioritizes instruments for re-inspection based on risk score |
| Information significance | Drives workflow prioritization, not direct clinical decision |
| Healthcare situation | Supports quality management process |
| Preliminary IMDRF risk | Category II (significant x non-critical) |
| Human review required | Yes |
| Probable FDA pathway | Non-device CDS or 510(k) depending on claims |

### Module C: Predictive Failure Analytics (P7)
| Attribute | Assessment |
|-----------|-----------|
| Function | Forecasts probability of instrument failure based on inspection history |
| Information significance | Maintenance decision support |
| Healthcare situation | Indirectly affects patient safety |
| Preliminary IMDRF risk | Category II |
| Human review required | Yes — maintenance decision by engineer/manager |
| Probable FDA pathway | Non-device CDS or enforcement discretion |

### Module D: Autonomous Inspection Copilot (P9)
| Attribute | Assessment |
|-----------|-----------|
| Function | Guides SPD technicians through step-by-step inspection protocol |
| Information significance | Protocol adherence tool |
| Healthcare situation | Quality management / infection prevention support |
| Preliminary IMDRF risk | Category II |
| Human review required | Yes — technician executes each step |
| Probable FDA pathway | Non-device (workflow guidance software) or 510(k) |

### Module E: Regulatory Automation / Accreditation (P8)
| Attribute | Assessment |
|-----------|-----------|
| Function | Self-assessment scores for JC/AAMI/CMS/FDA/ISO readiness |
| Information significance | Administrative and quality management |
| Healthcare situation | Organizational compliance (not direct patient care) |
| Preliminary IMDRF risk | Category I |
| Human review required | N/A — administrative tool |
| Probable FDA pathway | Non-device — administrative software |

### Module F: Enterprise Benchmarking (P5)
| Attribute | Assessment |
|-----------|-----------|
| Function | Compares hospital performance to peer baselines |
| Information significance | Operational analytics |
| Healthcare situation | Quality improvement |
| Preliminary IMDRF risk | Category I |
| Human review required | N/A |
| Probable FDA pathway | Non-device — quality analytics software |

### Module G: Vendor Intelligence Exchange (P6)
| Attribute | Assessment |
|-----------|-----------|
| Function | Aggregates cross-hospital instrument defect trends, recall tracking |
| Information significance | Supply chain quality signal |
| Healthcare situation | Supports procurement and quality decisions |
| Preliminary IMDRF risk | Category I-II |
| Human review required | Yes |
| Probable FDA pathway | Non-device or 510(k) (recall integration only) |

### Module H: Digital Twin of SPD Operations (P10)
| Attribute | Assessment |
|-----------|-----------|
| Function | Models SPD workflow throughput, bottlenecks, what-if simulation |
| Information significance | Operational planning |
| Healthcare situation | Administrative / operational |
| Preliminary IMDRF risk | Category I |
| Human review required | N/A |
| Probable FDA pathway | Non-device — operational software |

## 3. Overall Regulatory Strategy
**Subject to regulatory counsel review.**

### Recommended Approach
1. **Lead module for 510(k)**: Computer Vision Detection (Module A) — highest risk, clearest medical device function
2. **Bundle**: AI Ranking Engine (Module B) as part of the same 510(k) submission as an integrated system
3. **Non-device claim**: Modules E, F, H — explicitly frame as administrative/operational software in labeling
4. **CDS analysis for**: Modules C, D, G — evaluate 21st Century Cures exemption eligibility (displays basis for recommendation; clinician can independently review)

### De Novo Consideration
If no suitable 510(k) predicate is identified for the CV Detection module, De Novo is the fallback. This would establish a new product code and could benefit future competitors — weigh strategic implications with regulatory counsel.

### PMA Not Anticipated
PMA (Class III) is not anticipated unless LumenAI introduces claims related to:
- Direct patient diagnosis
- Autonomous treatment decisions
- Life-sustaining device control

## 4. Non-Device Safe Harbor Analysis (21st Century Cures)
CDS is excluded from device definition if ALL four conditions are met:
1. Not intended for serious/immediately life-threatening situations — SPD is a quality process, not acute care (met)
2. Displays basis for recommendation — AI confidence scores and evidence factors displayed (met)
3. Clinician can independently review — Mandatory technician sign-off enforced (met)
4. Intended for HCP use only — Confirmed (SPD professionals only; not patient-facing) (met with qualification)

**Preliminary conclusion**: Modules C, D, E, F, G, H likely qualify for non-device CDS exemption. Module A (CV Detection) and Module B (Ranking) require further analysis — the contamination detection function may be viewed as providing information beyond what a clinician can independently verify without the AI. This determination requires regulatory counsel review.

## 5. Potential Predicate Devices for 510(k)
The following cleared devices may serve as predicates (subject to substantial equivalence analysis by regulatory counsel):

| Device | 510(k) Number | Relevance |
|--------|--------------|-----------|
| Computer-aided detection software for imaging | Various K-numbers | AI-assisted image analysis precedent |
| Quality management software in sterile processing | Various | SPD workflow precedent |
| Surgical instrument tracking systems | Various | UDI/tracking function precedent |

Note: Specific predicate identification and substantial equivalence analysis must be performed by qualified regulatory counsel with access to FDA 510(k) database.

## 6. Regulatory Timeline Estimate
**Subject to regulatory counsel review and FDA interaction outcomes.**

| Milestone | Estimated Timeframe |
|-----------|-------------------|
| Regulatory counsel engagement | Q1 2026 |
| Pre-submission (Q-Sub) meeting with FDA | Q2 2026 |
| Live reader study completion | Q3 2026 |
| Sealed test set evaluation | Q4 2026 |
| 510(k) submission preparation | Q1 2027 |
| 510(k) submission (if pathway confirmed) | Q2 2027 |
| FDA review (target 90-day review clock) | Q2-Q3 2027 |

These are planning estimates only. Actual timelines depend on FDA workload, Q-Sub outcomes, and study results.
