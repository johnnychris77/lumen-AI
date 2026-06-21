# Submission Readiness Review
**LumenAI SPD Intelligence Platform** | SRR-LUM-001 | Version 1.0
**FDA 510(k) Pre-Submission Readiness Assessment**
**Date**: 2026-06-21 | **Status**: Internal Assessment
**Subject to regulatory counsel review before FDA engagement.**
**This is an internal readiness assessment. It does not constitute regulatory approval or clearance.**

---

## 1. Executive Summary

This Submission Readiness Review evaluates LumenAI's preparedness for a 510(k) Premarket Notification submission to FDA for the Computer Vision Detection module (Module A). The assessment scores 10 regulatory domains on a 1–5 scale.

**Overall Score: 27/50 — PARTIALLY READY**

LumenAI has made substantial progress in documentation, software architecture, risk management, and regulatory strategy. However, two critical gaps prevent submission:

1. **Clinical evidence**: No real-world validation study has been conducted. Current kappa data is from seeded mock only and is below the ≥ 0.80 primary endpoint.
2. **Quality management system**: No formal QMS exists. Complaint handling, CAPA, document control, and training records are absent.

**Estimated time to submission readiness**: 18–24 months with dedicated regulatory, clinical, and quality resources.

---

## 2. Domain Readiness Scores

| Domain | Score | Status | Rationale |
|--------|-------|--------|-----------|
| Intended Use & Claims | 4/5 | PARTIALLY READY | Well-bounded intended use; clear in/out claims; human review requirements documented. Missing: formal legal sign-off; predicate alignment review by regulatory counsel. |
| Clinical Evidence | 2/5 | NOT READY | Validation framework complete (P12). Seeded mock data only — not real-world. Kappa ~0.79, below ≥ 0.80 threshold. No multi-site study. No sealed test set results on real data. |
| Software Documentation | 4/5 | PARTIALLY READY | SRS, architecture, DMR, DHF index all exist. IEC 62304 V&V trace matrix complete. Missing: formal design review board sign-off; document approval signatures; DHF formally released. |
| Cybersecurity | 3/5 | PARTIALLY READY | Security architecture strong: JWT auth, tenant isolation, rate limiting, TLS, RBAC. Missing: penetration test (not yet completed), SBOM in CI pipeline, Dependabot, DAST, field-level encryption. |
| Risk Management | 3/5 | PARTIALLY READY | ISO 14971 file exists; P19 addendum adds new hazards. Missing: formal risk review board with sign-off; benefit-risk determination by qualified team; all residual risks formally accepted. |
| Human Factors | 1/5 | NOT READY | Human factors validation plan complete. No formative evaluation conducted. No summative validation study. IFU usability not tested. HF is a critical 510(k) gap. |
| Traceability | 3/5 | PARTIALLY READY | Master traceability matrix created (P19). Existing IEC 62304 trace matrix (P12). Coverage gaps in mobile/integration modules; some test references unconfirmed. |
| Quality System Maturity | 1/5 | NOT READY | No formal QMS. No complaint handling SOP (CRITICAL). No CAPA SOP. No document control. No training records. No management review. No internal audit. Complaint handling is a pre-submission legal requirement. |
| Post-Market Surveillance | 3/5 | PARTIALLY READY | PMS plan exists. RWE program designed (P15). kappa-monitor active. Predetermined Change Control Plan exists. Missing: real-world PMS data; MDR reporting procedure; RWE baseline data. |
| Predicate/Pathway | 3/5 | PARTIALLY READY | 510(k) pathway identified. Q-Submission prep documents exist. SaMD classification assessed. Missing: confirmed predicate device; predicate comparison data; Q-Sub meeting with FDA not yet scheduled. |

---

## 3. Scoring Summary

| Domain | Score |
|--------|-------|
| Intended Use & Claims | 4 |
| Clinical Evidence | 2 |
| Software Documentation | 4 |
| Cybersecurity | 3 |
| Risk Management | 3 |
| Human Factors | 1 |
| Traceability | 3 |
| Quality System Maturity | 1 |
| Post-Market Surveillance | 3 |
| Predicate/Pathway | 3 |
| **TOTAL** | **27/50** |

**Target score for submission**: 45/50 minimum (domains 1, 2, 5, 6, 8 must reach ≥ 4/5).

---

## 4. Pre-Submission Critical Path

The following 10 items represent the critical path to FDA submission readiness, ordered by priority and dependency:

### Priority 1 — Clinical (Longest Lead Time; Start Immediately)

**Item 1: Complete Real-World Clinical Validation Study**
- Timeline: 12–18 months
- Dependencies: Site identification, data use agreements, IRB/QA process, data collection, analysis, report
- Milestone: kappa ≥ 0.80 on real instrument images (multi-site, minimum 3 facilities)
- Owner: Clinical Validation Lead + contracted CRO
- Reference: docs/clinical/clinical-validation-plan.md, docs/regulatory/clinical-evidence-package.md

**Item 2: Identify and Confirm 510(k) Predicate Device**
- Timeline: 3–6 months (concurrent with Item 1)
- Dependencies: Regulatory counsel; FDA predicate database search; substantial equivalence analysis
- Milestone: Confirmed predicate with documented technological characteristics comparison
- Owner: Regulatory Affairs + Regulatory Counsel
- Reference: docs/clinical/510k-predicate-analysis.md, docs/regulatory/510k-predicate-search-log.md

### Priority 2 — Regulatory Engagement (Start Immediately)

**Item 3: Engage Regulatory Consultant and Legal Counsel**
- Timeline: 1–2 months
- Dependencies: Budget approval
- Milestone: Regulatory counsel retained; pathway determination confirmed; Q-Sub strategy approved
- Owner: CEO / Regulatory Affairs
- Note: Should not be delayed — informs all other items

**Item 4: Schedule Pre-Submission (Q-Submission) Meeting with FDA**
- Timeline: 3–6 months to receive FDA response
- Dependencies: Item 3 (regulatory counsel); Q-Sub documents (already exist)
- Milestone: FDA feedback on intended use, study design, and predicate received
- Owner: Regulatory Affairs + Regulatory Counsel
- Reference: docs/regulatory/q-submission-preparation.md

### Priority 3 — Quality System (Start Immediately; Long Lead Time)

**Item 5: Establish Formal Quality Management System**
- Timeline: 12–18 months to full compliance
- Dependencies: Quality Manager hire/contract
- Milestone: 21 CFR Part 820 compliant QMS; complaint handling SOP operational; CAPA active
- Owner: Quality Manager (TBH)
- Reference: docs/regulatory/qms-readiness-gap-analysis.md
- Note: Complaint handling is a legal pre-commercialization requirement, not just pre-submission

**Item 6: Complete SOC 2 Type I Audit**
- Timeline: 6–9 months
- Dependencies: Security controls mature; audit firm engaged
- Milestone: SOC 2 Type I report issued
- Owner: Cybersecurity Lead + External Auditor

### Priority 4 — Human Factors (Start After QMS Foundation)

**Item 7: Complete Human Factors Formative Evaluation**
- Timeline: 8 months (25 participants, 5 role groups)
- Dependencies: Prototype/staging environment; formative study protocol; participant recruitment
- Milestone: Formative evaluation report; design improvements implemented
- Owner: Human Factors Lead (TBH or contracted)
- Reference: docs/regulatory/human-factors-validation-plan.md §6

**Item 8: Complete Human Factors Summative Validation Study**
- Timeline: 8 months (after formative; 30+ participants)
- Dependencies: Item 7 completed; design improvements implemented
- Milestone: Summative report; ≤ 10% critical use error rate demonstrated
- Owner: Human Factors Lead
- Reference: docs/regulatory/human-factors-validation-plan.md §7

### Priority 5 — Cybersecurity (Start Soon)

**Item 9: Complete Penetration Test (CREST/OSCP Firm)**
- Timeline: 3–6 months (procurement + execution + remediation)
- Dependencies: Production-equivalent environment available; pentest firm engaged
- Milestone: Penetration test report; critical and high findings remediated; remediation report
- Owner: Cybersecurity Lead
- Reference: docs/regulatory/external-pentest-scope.md

**Item 10: Generate Machine-Readable SBOM and Integrate Automated Vulnerability Scanning**
- Timeline: 2–3 months
- Dependencies: CI/CD pipeline access; cyclonedx-bom tooling
- Milestone: CycloneDX SBOM generated on each release; pip-audit + npm audit in CI; Dependabot configured
- Owner: Engineering Lead
- Reference: docs/regulatory/cybersecurity-submission-package.md §3

---

## 5. Milestone Timeline to Submission Readiness

```
2026 Q3 (Now)
  ├── Engage regulatory counsel and legal (Item 3) ──────────────► Month 1–2
  ├── Begin QMS foundation: Document control, CAPA, Complaint SOP ► Month 1–3
  ├── Initiate clinical site identification (Item 1) ────────────► Month 1–3
  ├── Initiate predicate device search (Item 2) ─────────────────► Month 1–3
  └── File Q-Submission request (Item 4) ───────────────────────► Month 2–3

2026 Q4 – 2027 Q1
  ├── FDA Q-Sub response received ────────────────────────────────► Month 4–6
  ├── Penetration test executed (Item 9) ────────────────────────► Month 3–6
  ├── SBOM + automated scanning implemented (Item 10) ───────────► Month 2–4
  ├── QMS Phase 1 complete ───────────────────────────────────────► Month 6
  └── Clinical validation sites enrolled ──────────────────────────► Month 6

2027 Q2 – 2027 Q4
  ├── Clinical study data collection ────────────────────────────► Month 6–15
  ├── Human factors formative evaluation ───────────────────────► Month 6–14
  ├── QMS Phase 2 + Phase 3 complete ───────────────────────────► Month 9–12
  └── SOC 2 Type I complete ───────────────────────────────────────► Month 9

2028 Q1 – Q2
  ├── Clinical study analysis + report ──────────────────────────► Month 15–18
  ├── Sealed test set validation ───────────────────────────────── Month 16–18
  ├── Human factors summative validation ──────────────────────── Month 14–22
  ├── Pre-submission documents finalized ──────────────────────── Month 18–22
  └── 510(k) submission ─────────────────────────────────────────► Month 22–24
```

**Estimated submission date**: Q2–Q3 2028 (assuming resources in place by Q3 2026)
**Estimated clearance date**: Q4 2028 – Q1 2029 (assuming 90-day FDA review; may be longer)

---

## 6. Resource Requirements Estimate

| Role | Engagement Type | Estimated Duration |
|------|---------------|-------------------|
| Regulatory Counsel (FDA specialist) | External firm | 18–24 months |
| Quality Manager | Full-time hire or contractor | 18–24 months |
| Clinical Research Organization (CRO) | Contract; multi-site study | 12–15 months |
| Human Factors Specialist | Contract firm | 12–18 months |
| Penetration Test Firm (CREST/OSCP) | One-time engagement + re-test | 3–6 months |
| SOC 2 Audit Firm | External audit | 6–9 months |
| Internal Regulatory Affairs Lead | Full-time hire | 18–24 months |

---

## 7. What LumenAI Can Do Now (Pre-Clearance)

While pursuing regulatory clearance, LumenAI may engage in the following commercial activities (regulatory counsel confirmation required):
- Administrative modules (E, F, G, H) under non-device / CDS exemption pathway
- Quality documentation and reporting functions
- Pilot programs with research use agreements at qualified facilities
- SPD education and training tools

**What must NOT occur before clearance**:
- Marketing Module A (CV Detection) as a cleared medical device
- Claiming FDA clearance or approval
- Claiming regulatory approval or CE marking without proper registration
- Deploying Module A in commercial clinical use without enforcement discretion engagement or clearance

---

## 8. Risk to Submission Timeline

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Clinical study kappa < 0.80 | Medium | High — retraining required; 6–12 month delay | Algorithm improvement plan; Q-Sub to confirm FDA threshold |
| No suitable 510(k) predicate | Medium | High — De Novo path adds 12–18 months | Begin De Novo analysis in parallel |
| Human factors critical use error rate > 10% | Medium | High — design iteration required; 6–12 month delay | Early formative; iterative design |
| FDA requests additional clinical data in review | Medium | Medium — additional data collection; 6–12 month delay | Q-Sub engagement to align expectations |
| QMS not operational at time of submission | High | Very High — submission may be rejected | Immediate QMS program initiation |
| Key personnel turnover (RA Lead, Clinical Lead) | Medium | High | Knowledge documentation; redundant coverage |

---

*Document Owner: Regulatory Affairs Lead | Review Cycle: Quarterly*
*This internal assessment is a planning artifact. It does not constitute regulatory advice or a commitment by FDA.*
*All regulatory determinations require review by qualified regulatory counsel.*
