# Quality Management System (QMS) Readiness Gap Analysis
**LumenAI SPD Intelligence Platform** | QMS-GAP-001 | Version 1.0
**Assessment Against 21 CFR Part 820 and ISO 13485:2016**
**Status**: In Review | **Subject to quality consultant review before submission.**

---

## 1. Executive Summary

LumenAI currently operates without a formal Quality Management System meeting 21 CFR Part 820 (US) or ISO 13485:2016 requirements. Engineering practices (git version control, CI/CD, PR-based review, automated testing) provide partial compliance evidence for some QMS elements; however, formal SOPs, approval workflows, training records, and quality oversight structures are absent.

**Overall QMS Readiness**: NOT READY FOR SUBMISSION

Establishing a compliant QMS is estimated to require 12–18 months and dedicated quality resources before FDA submission is achievable. QMS establishment is on the critical path for regulatory submission.

---

## 2. QMS Element Assessment

### 2.1 Design Controls (21 CFR 820.30 / ISO 13485 §7.3)

| Sub-Element | Required | Current State | Gap | Priority |
|-------------|----------|--------------|-----|----------|
| 820.30(b) Design and development planning | Yes | Project milestone plan (P0–P19) exists in git; no formal design plan document | No formal design plan with phase gates and sign-off authority | HIGH |
| 820.30(c) Design input | Yes | SRS (software-requirements-specification.md) exists | SRS lacks formal review/approval signatures; no user needs traceability to SRS | HIGH |
| 820.30(d) Design output | Yes | Code, architecture docs, API specs exist in git | No formal design output approval; outputs not formally released | HIGH |
| 820.30(e) Design review | Yes | PR reviews in GitHub; no formal design review board | No formal design review meetings; no design review records; no sign-off authority | CRITICAL |
| 820.30(f) Design verification | Yes | Automated test suite (pytest); IEC 62304 V&V trace matrix | Test suite exists; no formal verification sign-off; no verification report | HIGH |
| 820.30(g) Design validation | Yes | Clinical validation framework (P12) established | Real-world validation not yet performed; validation report not complete | CRITICAL |
| 820.30(h) Design transfer | Yes | CI/CD pipeline exists | No formal transfer to manufacturing/operations procedure | MEDIUM |
| 820.30(i) Design changes | Yes | AI-ML Change Control Plan; PR-based change control | No formal ECO (Engineering Change Order) process; no change review board | HIGH |
| 820.30(j) DHF | Yes | DHF Index (design-history-file-index.md) created | DHF index exists; documents lack formal approval; DHF structure needs validation | HIGH |

**Recommended Action**: Establish Design Review Board; create formal design review procedure; apply document approval workflow to all DHF items. Estimated effort: 3–6 months.

---

### 2.2 Document Control (21 CFR 820.40 / ISO 13485 §4.2.4)

| Sub-Element | Required | Current State | Gap | Priority |
|-------------|----------|--------------|-----|----------|
| Controlled document register | Yes | Documents exist in git; no numbered document register | No SOP for document approval; no controlled document register; no document numbering system | HIGH |
| Document approval workflow | Yes | PR review exists (technical approval) | No formal document approval by designated authority (RA, QA, Executive) | HIGH |
| Document revision control | Yes | Git version history provides version control | Version numbers not systematically applied to docs; no "effective date" tracking | MEDIUM |
| Document distribution control | Yes | GitHub repository access | No controlled distribution list; no confirmation of receipt/training on new documents | MEDIUM |
| Obsolescence control | Yes | Old versions preserved in git history | No formal obsolescence process; superseded documents not formally withdrawn | LOW |

**Recommended Action**: Implement document management system (or adapt git with formal controls); create Document Control SOP; establish document numbering convention; identify document approval authorities. Estimated effort: 2–3 months.

---

### 2.3 Corrective and Preventive Action (CAPA) (21 CFR 820.100 / ISO 13485 §8.5.2/8.5.3)

| Sub-Element | Required | Current State | Gap | Priority |
|-------------|----------|--------------|-----|----------|
| CAPA procedure | Yes | CAPA data model exists in database (from P12/P13) | No written CAPA SOP; no defined intake process; no root cause analysis procedure | HIGH |
| Root cause analysis methodology | Yes | None established | No documented methodology (5-Why, Fishbone, FTA) | HIGH |
| CAPA effectiveness verification | Yes | None established | No effectiveness check SOP; no criteria for CAPA closure | HIGH |
| Trend analysis | Yes | kappa-monitor provides AI performance trend | No formal trend analysis for complaints, defects, or nonconformances | MEDIUM |
| Preventive action | Yes | None established | No proactive quality signal review process | MEDIUM |

**Recommended Action**: Create CAPA SOP covering intake, investigation, root cause analysis, action planning, verification, closure, and trend review. Estimated effort: 2–3 months.

---

### 2.4 Complaint Handling (21 CFR 820.198 / ISO 13485 §8.2.2)

| Sub-Element | Required | Current State | Gap | Priority |
|-------------|----------|--------------|-----|----------|
| Complaint intake process | Yes | Not implemented | No complaint intake mechanism; no complaint definition or classification criteria | CRITICAL |
| MDR/Vigilance evaluation | Yes | Not implemented | No process to evaluate whether complaint meets MDR reporting threshold (21 CFR Part 803) | CRITICAL |
| Complaint investigation procedure | Yes | Not implemented | No investigation SOP; no defined timeframes | CRITICAL |
| MDR reporting (21 CFR Part 803) | Yes | Not implemented | No MDR reporting capability or procedure | CRITICAL |
| Complaint file maintenance | Yes | Not implemented | No complaint record system | HIGH |

**Recommended Action**: This is the highest-priority QMS gap. Establish complaint handling SOP; define MDR evaluation criteria; create complaint intake form/system; train relevant staff; engage regulatory counsel on MDR threshold interpretation. Estimated effort: 3–4 months (for procedure); ongoing staff training.

---

### 2.5 Change Management (21 CFR 820.70(b) / ISO 13485 §7.3.9)

| Sub-Element | Required | Current State | Gap | Priority |
|-------------|----------|--------------|-----|----------|
| Change control procedure | Yes | PR-based change control; AI-ML Change Control Plan; PCCP | No formal ECO process; no change review board with sign-off authority | HIGH |
| Impact assessment | Yes | Code review assesses technical impact | No formal regulatory impact assessment for changes; no risk re-evaluation trigger | HIGH |
| Validation of changes | Yes | CI/CD automated tests run on all changes | No formal validation sign-off for significant changes | HIGH |
| Record of changes | Yes | Git commit history | Git history is informal; no formal change record with regulatory impact statement | MEDIUM |

**Recommended Action**: Create Engineering Change Order (ECO) procedure; establish Change Review Board; create regulatory impact assessment template. Estimated effort: 2–3 months.

---

### 2.6 Training Records (21 CFR 820.25 / ISO 13485 §6.2)

| Sub-Element | Required | Current State | Gap | Priority |
|-------------|----------|--------------|-----|----------|
| Training requirements by role | Yes | Not defined | No documented training requirements per role (engineering, QA, regulatory, clinical) | HIGH |
| Training records | Yes | Not implemented | No training record system; no evidence of regulatory training completion | HIGH |
| Competency assessment | Yes | Not implemented | No competency verification process | MEDIUM |
| Training on controlled documents | Yes | Not implemented | No process to ensure staff trained on new/revised SOPs | HIGH |

**Recommended Action**: Define training requirements by role; implement training record system (spreadsheet or EQMS); create onboarding training plan. Estimated effort: 2–3 months.

---

### 2.7 Supplier Controls (21 CFR 820.50 / ISO 13485 §7.4)

| Sub-Element | Required | Current State | Gap | Priority |
|-------------|----------|--------------|-----|----------|
| Supplier qualification procedure | Yes | Vendor intelligence module tracks suppliers; no formal qualification | No supplier qualification SOP; no Approved Vendor List (AVL) | MEDIUM |
| Critical supplier identification | Yes | Not defined | Cloud infrastructure (AWS), key software components (FastAPI, PostgreSQL) not evaluated | MEDIUM |
| Supplier audit / assessment | Yes | Not implemented | No supplier audit process | MEDIUM |
| Supplier agreements (QAA) | Yes | Standard vendor terms only | No Quality Agreement with critical suppliers | LOW |

**Recommended Action**: Define critical suppliers; create supplier qualification SOP; establish AVL; review standard contracts for quality requirements. Estimated effort: 3 months.

---

### 2.8 Management Review (21 CFR 820.20 / ISO 13485 §5.6)

| Sub-Element | Required | Current State | Gap | Priority |
|-------------|----------|--------------|-----|----------|
| Management review procedure | Yes | Not implemented | No management review SOP; no defined inputs/outputs | MEDIUM |
| Management review records | Yes | Not implemented | No minutes or records of quality management reviews | MEDIUM |
| Quality objectives | Yes | Not formally defined | No documented quality objectives or KPIs | MEDIUM |
| Management commitment evidence | Yes | Not documented | No documented management commitment to quality system | MEDIUM |

**Recommended Action**: Schedule initial management review; create management review procedure; define quality objectives and KPIs. Estimated effort: 1–2 months to establish process.

---

### 2.9 Internal Audit (21 CFR 820.22 / ISO 13485 §8.2.4)

| Sub-Element | Required | Current State | Gap | Priority |
|-------------|----------|--------------|-----|----------|
| Internal audit procedure | Yes | Not implemented | No internal audit SOP; no audit schedule | MEDIUM |
| Qualified auditors | Yes | None designated | No trained internal auditors | MEDIUM |
| Audit schedule | Yes | Not implemented | No annual audit schedule | MEDIUM |
| Audit reports and corrective actions | Yes | Not implemented | No audit report format; no CAPA linkage | MEDIUM |

**Recommended Action**: Train at least one internal auditor; create internal audit SOP; schedule first internal audit (likely 6 months after QMS establishment). Estimated effort: 3 months.

---

### 2.10 Statistical Methods (21 CFR 820.250 / ISO 13485 §8.2.6)

| Sub-Element | Required | Current State | Gap | Priority |
|-------------|----------|--------------|-----|----------|
| Statistical methods for validation | Yes | Wilson CI, Cohen's kappa implemented in validation framework | Implemented in code; not documented in formal sampling plan | LOW |
| Sampling plan | Yes | Defined in clinical validation plan for study N | No formal sampling plan document separate from study protocol | LOW |
| Control charts / SPC | Situational | kappa-monitor provides trend monitoring | Not in SPC format; no formal control limits documentation | LOW |

**Recommended Action**: Document sampling plan rationale; formalize kappa-monitor alert thresholds as statistical control criteria. Estimated effort: 1 month.

---

## 3. QMS Gap Summary Table

| QMS Element | Regulation | Gap Severity | Estimated Effort | Owner |
|-------------|-----------|-------------|------------------|-------|
| Design Controls (820.30) | 21 CFR Part 820 | HIGH | 3–6 months | Engineering Lead + RA |
| Document Control (820.40) | 21 CFR Part 820 | HIGH | 2–3 months | Quality Manager |
| CAPA (820.100) | 21 CFR Part 820 | HIGH | 2–3 months | Quality Manager |
| Complaint Handling (820.198) | 21 CFR Part 820 | CRITICAL | 3–4 months | RA + Legal |
| Change Management (820.70(b)) | 21 CFR Part 820 | HIGH | 2–3 months | Engineering Lead |
| Training Records (820.25) | 21 CFR Part 820 | HIGH | 2–3 months | HR + Quality |
| Supplier Controls (820.50) | 21 CFR Part 820 | MEDIUM | 3 months | Supply Chain + Quality |
| Management Review (820.20) | 21 CFR Part 820 | MEDIUM | 1–2 months | Executive Team |
| Internal Audit (820.22) | 21 CFR Part 820 | MEDIUM | 3 months | Quality Manager |
| Statistical Methods (820.250) | 21 CFR Part 820 | LOW | 1 month | Clinical Lead |

---

## 4. Recommended QMS Implementation Roadmap

### Phase 1 (Months 1–3): Foundation
- Hire or contract Quality Manager with medical device QMS experience
- Implement document control system (EQMS or controlled SharePoint/Confluence)
- Create Document Control SOP
- Create CAPA SOP
- Create Complaint Handling SOP (highest regulatory priority)
- Define training requirements by role

### Phase 2 (Months 4–6): Core Processes
- Establish Change Review Board; create ECO procedure
- Implement training record system
- Conduct initial management review
- Begin supplier qualification for critical suppliers
- Apply document approval workflow to all existing regulatory documents

### Phase 3 (Months 7–9): Audit Readiness
- Train internal auditor
- Conduct first internal audit
- Schedule Design Review Board for retroactive design review of existing DHF
- Gap remediation from audit findings

### Phase 4 (Months 10–12): Submission Preparation
- Mock FDA inspection / regulatory readiness audit
- External QMS gap audit by regulatory consultant
- SOC 2 Type I audit (if proceeding to enterprise customers before clearance)
- FDA submission package QMS evidence compilation

**Estimated total QMS establishment timeline: 12–18 months with dedicated quality resources.**

---

## 5. QMS Readiness Score

| Area | Score (1–5) | Notes |
|------|------------|-------|
| Design Controls | 2 | Documents exist; no formal process |
| Document Control | 1 | Git history only; no formal control |
| CAPA | 2 | Data model exists; no SOP |
| Complaint Handling | 1 | Not implemented |
| Change Management | 2 | PR process; no formal ECO |
| Training Records | 1 | Not implemented |
| Supplier Controls | 2 | Partial |
| Management Review | 1 | Not implemented |
| Internal Audit | 1 | Not implemented |
| Statistical Methods | 3 | Implemented in code |
| **Overall** | **1.6/5** | **NOT READY** |

---

*Document Owner: Quality Manager (TBH) + Regulatory Affairs Lead*
*Review Cycle: Quarterly during QMS implementation*
*This gap analysis is the starting point for QMS establishment, not evidence of compliance.*
