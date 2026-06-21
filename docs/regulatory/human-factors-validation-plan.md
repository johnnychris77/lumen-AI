# Human Factors Validation Plan
**LumenAI SPD Intelligence Platform** | HFE-LUM-001 | Version 1.0-DRAFT
**Per FDA Human Factors Guidance (2016) and ANSI/AAMI HE75:2009**
**Status**: In Review | **Subject to regulatory counsel and human factors expert review before submission.**

---

## 1. Scope

This Human Factors Validation Plan covers all user interactions with LumenAI that could, if performed incorrectly, contribute to patient harm or quality failures. The plan addresses:

- AI finding review and confirmation/override workflow
- Mobile image capture workflow
- Barcode/UDI/QR/KeyDot scanning
- Offline session management and sync status awareness
- Critical finding escalation and acknowledgment
- Report generation and export

This plan does NOT cover system administration functions (user management, tenant configuration) as these do not create direct patient safety risk.

---

## 2. User Groups

### 2.1 Primary User Groups

| User Group | Count (US estimate) | Experience Level | HF Priority |
|------------|--------------------|--------------------|-------------|
| SPD Technicians (Entry-Level) | ~45,000 | 0–2 years; may be in certification training | HIGH |
| SPD Technicians (Senior) | ~60,000 | 2+ years; CRCST certified | HIGH |
| SPD Educators | ~8,000 | 3+ years; education role | MEDIUM |
| SPD Supervisors/Managers | ~12,000 | 5+ years; management role | MEDIUM |
| Infection Prevention Specialists | ~12,000 | CIC certified; clinical background | LOW |

### 2.2 User Characteristics

| Characteristic | Entry-Level Technician | Senior Technician |
|---------------|----------------------|-------------------|
| Technology literacy | Moderate (smartphone users) | Moderate to high |
| Domain expertise | Low to moderate | High |
| Time pressure | High (case carts, turnaround) | High |
| Attention state | Variable; high cognitive load | Variable; task-saturated |
| Fatigue risk | High (12-hour shifts common) | High |
| Supervisory oversight | High | Low to moderate |
| Primary language | Variable; ESL common in SPD | Variable |
| Physical environment | Wet/contaminated; PPE-encumbered | Same |

### 2.3 Environmental Considerations for User Interface

- PPE (gloves): Touchscreen interaction impaired; large targets required
- Noise: Auditory alerts may not be detected; visual alerts essential
- Lighting: Variable (decontamination area often bright; inspection area varies)
- Contaminated surfaces: Device must be wipeable; mobile devices in SPD are commonly ruggedized
- Time pressure: Task completion time is critical; workflows must minimize steps
- Cognitive load: Technicians monitor multiple instrument sets simultaneously

---

## 3. Use Environments

| Environment | Primary Users | Key Risks |
|-------------|--------------|-----------|
| SPD Decontamination Area | Entry-level, senior technicians | Wet surfaces, PPE, noise, contamination |
| SPD Inspection/Assembly | Senior technicians, educators | Lighting variation, magnification use |
| SPD Sterilization | Senior technicians | Time pressure, process criticality |
| Mobile/Point-of-Use (OR, procedural) | Senior technicians, managers | Variable lighting, one-handed operation, connectivity |
| Manager Office/Workstation | Managers, quality directors | Desktop environment; standard conditions |
| Remote/Administrative | IP nurses, quality directors | Standard office; report review |

---

## 4. Critical Tasks (Tasks Where Use Error Could Cause Harm)

### Task 1: Reviewing AI Finding and Confirming or Overriding

**Task Description**: Technician receives AI finding (e.g., "potential blood residue detected — confidence 0.73") and must confirm or override before recording disposition.

**Use Error Scenario A**: Technician accepts AI finding without reviewing the supporting image or confidence score. If finding is false positive, instrument is unnecessarily quarantined. If finding is false negative that the technician doesn't independently catch, contaminated instrument proceeds.

**Use Error Scenario B**: Technician reflexively overrides AI findings due to alert fatigue or overconfidence in own visual inspection, systematically reducing safety value of AI.

| Factor | Detail |
|--------|--------|
| Probability of Use Error | Medium — alert fatigue is documented in healthcare |
| Severity if Error Occurs | S4 (Critical) — contaminated instrument may reach patient |
| Risk Level (Pre-Mitigation) | High |
| Mitigation | Confidence score prominently displayed; low-confidence warning (< 0.60); image evidence always shown; override requires explicit confirmation with reason |

---

### Task 2: Barcode/UDI Scanning — Instrument Identification

**Task Description**: Technician scans instrument barcode/UDI to associate inspection record with instrument identity.

**Use Error Scenario A**: Technician scans adjacent instrument's barcode instead of target instrument. Inspection findings associated with wrong instrument.

**Use Error Scenario B**: Technician proceeds despite scan failure or low-confidence scan result, using wrong or assumed instrument identity.

| Factor | Detail |
|--------|--------|
| Probability of Use Error | Medium — high-density instrument trays; similar instruments adjacent |
| Severity if Error Occurs | S4 (Critical) — inspection record associated with wrong instrument |
| Risk Level (Pre-Mitigation) | High |
| Mitigation | Explicit identification failure flag; dual confirmation on mismatch; instrument image displayed for visual verification after scan |

---

### Task 3: Mobile Image Capture — Quality Adequate for Analysis

**Task Description**: Technician captures instrument image using mobile device camera.

**Use Error Scenario A**: Blurry, poorly lit, or obstructed image submitted. AI cannot detect findings below image quality threshold.

**Use Error Scenario B**: Technician submits image of wrong surface (e.g., instrument handle instead of working end).

| Factor | Detail |
|--------|--------|
| Probability of Use Error | Medium-High — mobile camera use in clinical environments is challenging |
| Severity if Error Occurs | S3 (Moderate) — missed finding; human visual review may still catch |
| Risk Level (Pre-Mitigation) | Medium |
| Mitigation | Image quality check on capture; blur detection; retake prompt for low-quality images; guidance overlay for image capture (frame guides) |

---

### Task 4: Offline Session Management — Sync Status Awareness

**Task Description**: Technician works in offline mode; session is PENDING_SYNC; must be aware that data is not yet confirmed on server.

**Use Error Scenario**: Technician assumes inspection session is complete and synchronized when it is actually PENDING_SYNC. Instrument released based on offline-only record that was never confirmed.

| Factor | Detail |
|--------|--------|
| Probability of Use Error | Medium — PENDING_SYNC concept is novel for most SPD technicians |
| Severity if Error Occurs | S3 (Moderate) — inspection record gap; supervisor may catch |
| Risk Level (Pre-Mitigation) | Medium |
| Mitigation | Prominent PENDING_SYNC badge; session list clearly differentiates synced vs. pending; completion workflow requires SYNCED status; supervisor dashboard shows pending sessions |

---

### Task 5: Escalation — Critical Finding Acknowledgment

**Task Description**: Critical AI finding (e.g., blood residue, high confidence) requires explicit acknowledgment before user proceeds.

**Use Error Scenario A**: Technician dismisses acknowledgment dialog reflexively without reading content (alert fatigue).

**Use Error Scenario B**: Technician acknowledges but does not escalate to supervisor as required by facility protocol.

| Factor | Detail |
|--------|--------|
| Probability of Use Error | Medium — acknowledgment fatigue is a well-documented HF issue |
| Severity if Error Occurs | S4 (Critical) — critical finding may not reach quality decision-maker |
| Risk Level (Pre-Mitigation) | High |
| Mitigation | Critical findings require acknowledgment before proceeding; acknowledgment is logged; escalation recommendation displayed; supervisor dashboard shows unescalated critical findings |

---

## 5. Use Error Risk Assessment Summary

| Task | Pre-Mitigation Risk | Key Mitigation | Post-Mitigation Risk |
|------|--------------------|-----------------|--------------------|
| 1 — AI Finding Review | High | Confidence score display; low-confidence warning | Medium |
| 2 — Barcode/UDI Scan | High | ID failure flag; dual confirmation | Medium |
| 3 — Image Capture | Medium | Quality check; retake prompt | Low |
| 4 — Offline Sync Awareness | Medium | PENDING_SYNC badge; session status | Low |
| 5 — Escalation | High | Acknowledgment gate; supervisor dashboard | Medium |

Residual medium risks (Tasks 1, 2, 5) require further assessment in summative validation study.

---

## 6. Formative Evaluation Plan

### 6.1 Objectives
- Identify use errors and close calls in prototype workflows
- Evaluate learnability for entry-level technicians
- Assess cognitive load of AI finding review workflow
- Validate effectiveness of PENDING_SYNC visual design

### 6.2 Method
- **Protocol**: Think-aloud usability protocol
- **Participants**: 5 users per role group × 5 groups = 25 total
- **Stimulus**: Clickable prototype or staging environment
- **Tasks**: Representative task scenarios for each Critical Task (§4)
- **Data collected**: Task completion, errors, time-on-task, verbal commentary
- **Analysis**: Usability problems logged; severity rated; redesign recommendations

### 6.3 Pass/Fail Criteria (Formative — Iterative)
No pass/fail for formative evaluation — all findings used for design improvement.

### 6.4 Timeline
- **Phase 1 (Paper prototype)**: 2 months after QMS establishment
- **Phase 2 (Staging prototype)**: 4 months after QMS establishment
- **Analysis and redesign**: 2 months
- **Total**: ~8 months

### 6.5 Status
**Not yet initiated.** Gap — required before summative study and before submission.

---

## 7. Summative Validation Study Plan

### 7.1 Objectives
- Demonstrate that the intended user population can use LumenAI safely and effectively
- Meet FDA threshold: critical use error rate ≤ 10% per critical task
- Provide evidence for 510(k) human factors submission section

### 7.2 Method
- **Protocol**: Simulated use study (realistic SPD environment simulation)
- **Participants**: 15 users per critical role × 2 critical roles = 30 minimum (may increase based on formative findings)
- **Stimulus**: Production-equivalent staging environment with representative instrument images
- **Tasks**: Critical Tasks 1–5 (§4) in simulated workflow
- **Ground truth**: Expert panel pre-scored instrument images (known contamination status)
- **Data collected**: Task completion (binary), errors, close calls, time-on-task, user satisfaction

### 7.3 Pass Criteria (Summative — Go/No-Go)
- **Critical use error rate**: ≤ 10% per critical task per role group
- **Task completion rate**: ≥ 90% per critical task
- **No unrecoverable critical errors**: Zero unrecoverable errors that would result in patient harm in real use

### 7.4 Failure Response
If critical use error rate > 10% for any task:
1. Analyze error pattern (root cause)
2. Implement design fix
3. Re-test affected task (additional 5 participants per error pattern)
4. Must achieve ≤ 10% before submission

### 7.5 Timeline
- After formative evaluation and design iteration complete
- Estimated: 6 months of summative study
- Analysis and report: 2 months
- Total: 8 months (concurrent with clinical validation study)

### 7.6 Status
**Not yet initiated.** Gap — critical pre-submission requirement.

---

## 8. Mitigation Strategies Already Implemented

The following human factors mitigations have been implemented in the current codebase:

| Mitigation | Implementation | Evidence |
|------------|---------------|---------|
| Confidence score displayed with every finding | Backend: confidence_score stored and returned; Frontend: displayed per finding | REQ-A-005; test_p4_inspection.py |
| Override requires explicit confirmation | Override action requires explicit user action and logs reason | REQ-A-006 |
| Critical findings require acknowledgment before proceeding | Acknowledgment gate in inspection workflow | UI design; logged in audit |
| PENDING_SYNC badge on unsynced sessions | Session list displays sync status | REQ-I-003 |
| Identification failures flagged, not silently skipped | Failed scan → explicit flag → human resolution required | REQ-D-005 |
| Low-confidence warning (< 0.60) | Threshold-based warning triggered server-side | Risk control P19-007 |
| Dual confirmation on identification mismatch | Mismatch triggers dual-confirm workflow | REQ-D-006 |

---

## 9. Gaps Before Submission

| Gap | Priority | Estimated Effort |
|-----|----------|-----------------|
| Formative evaluation not completed | CRITICAL | 8 months; 25 participants |
| Summative validation not completed | CRITICAL | 8 months; 30+ participants |
| IFU usability not tested | HIGH | Part of formative evaluation |
| Error recovery workflows not evaluated | HIGH | Part of formative evaluation |
| Entry-level technician specific evaluation | HIGH | Subset of formative/summative |
| Mobile image capture workflow not formally tested | HIGH | Part of summative study |

**Overall Human Factors Readiness: NOT READY FOR SUBMISSION**

---

## 10. Regulatory References

- FDA Human Factors Guidance: "Applying Human Factors and Usability Engineering to Medical Devices" (February 2016)
- FDA Draft Guidance: "Human Factors Studies and Related Clinical Study Considerations" (November 2020)
- ANSI/AAMI HE75:2009 — Human factors engineering — Design of medical devices
- IEC 62366-1:2015 — Medical devices — Application of usability engineering
- FDA Guidance: "Use of International Standard IEC 62366-1..." (February 2016)

---

*Document Owner: Human Factors Lead + Product Design Lead*
*Review Cycle: Per study milestone | Next Review: Post-formative evaluation*
*This plan requires human factors specialist review before study execution.*
