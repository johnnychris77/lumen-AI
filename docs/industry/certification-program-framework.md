# LumenAI Certification Program Framework

> **Audience:** Industry, partnerships, and quality leadership. Defines LumenAI's ecosystem-leadership certification programs and the advisory board that governs them. Certifications recognize use of LumenAI quality practices — they are **not** accreditation, regulatory approval, or FDA clearance.

---

## 1. Purpose

Recognize facilities that operate to a high standard of SPD quality and inspection intelligence, creating a credible, governed mark of excellence that drives adoption and ecosystem leadership.

---

## 2. Certification Types

| `certification_type` | Recognizes | Levels |
|----------------------|-----------|--------|
| `certified_site` | Facilities meeting LumenAI quality-practice criteria | standard / advanced |
| `baseline_excellence` | Rigorous, well-governed instrument baseline management | standard / advanced |
| `inspection_intelligence` | Mature use of inspection analytics + human-reviewed signals | standard / advanced / leader |

Managed via `POST /api/accreditation/certifications`, `GET /certifications`, and `POST /certifications/{id}/award`.

---

## 3. Certification Lifecycle

```
applicant → in_review → certified → (expired)
```

- Awards set an expiry window (`POST /certifications/{id}/award?valid_days=`) — certifications are time-bound and must be renewed
- All status changes are audit-logged
- Certification criteria must be human-reviewed; no automated pass/fail without review

---

## 4. Certification Criteria (illustrative)

| Type | Representative criteria |
|------|--------------------------|
| Certified Site | Active inspection program, evidence completeness ≥ threshold, no open critical readiness gaps |
| Baseline Excellence | Governed baseline approval workflow, manufacturer baselines hospital-approved, change control |
| Inspection Intelligence | Consistent use of analytics with documented human review of all candidate signals |

> Criteria are quality-practice indicators — **not** clinical-outcome or regulatory-compliance certifications.

---

## 5. Advisory Board (Phase 6)

**Governance model:** An independent advisory board governs certification criteria, benchmark methodology, and claims discipline.

| Element | Definition |
|---------|------------|
| **Membership** | SPD/quality leaders, accreditation experts, an industry-org representative, a privacy/security officer, a clinical quality advisor (advisory only) |
| **Term** | Staggered multi-year terms to preserve continuity and independence |
| **Mandate** | Approve certification criteria and benchmark methodology; uphold anonymization, k-anonymity, and no-causation/no-regulatory-claim discipline |
| **Review process** | Periodic review of criteria + published methodology; sign-off on material changes; conflict-of-interest disclosure required |
| **Independence** | Board can require changes to published claims; commercial teams cannot override governance decisions |

---

## 6. Governance & Claims Discipline

| Principle | Enforcement |
|-----------|-------------|
| Not accreditation | Certifications are LumenAI program marks, not accreditation or regulatory approval |
| Human review | Certification decisions require human review |
| Auditability | Certification lifecycle changes are audit-logged |
| Tenant isolation | Certification records are tenant/facility scoped |
| No clinical/regulatory claims | No FDA clearance, regulatory approval, or causation language |

---

## 7. Industry Leadership Roadmap

| Horizon | Milestone |
|---------|-----------|
| Q1–Q2 | Launch Certified Site + advisory board charter |
| Q3–Q4 | Baseline Excellence + first annual benchmark publication |
| Year 2 | Inspection Intelligence "leader" tier; certified-site network as a reference engine |

---

*LumenAI certifications recognize quality practices and are not accreditation, regulatory approval, or FDA clearance. All quality outputs are candidate signals requiring human review.*
