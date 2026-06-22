# LumenAI Survey Evidence Framework

> **Audience:** Quality and SPD leadership preparing for accreditation surveys. Defines how LumenAI assembles survey-ready evidence. All packages are human-reviewed; LumenAI makes no accreditation guarantee and no FDA/regulatory claims.

---

## 1. Purpose

Turn a facility's continuously tracked evidence into survey-ready documentation on demand — survey binders, compliance reports, and audit evidence packages — with a readiness summary attached and full audit trail.

---

## 2. Package Types

| `package_type` | Purpose | Typical use |
|----------------|---------|-------------|
| `binder` | Full evidence binder for a survey | On-site survey readiness |
| `compliance_report` | Summary of standard-by-standard status | Leadership / mock survey |
| `audit_evidence` | Evidence package for internal/external audit | Internal QA, vendor audit |

Generated via `POST /api/accreditation/survey-evidence/generate`; listed via `GET /api/accreditation/survey-evidence`.

---

## 3. What a Package Contains

- Every tracked evidence item for the facility + accreditor (`standard_ref`, `category`, `title`, `status`, `is_critical`)
- A point-in-time readiness summary (completeness, risk, readiness score + status, open critical count)
- Generation metadata (`generated_by`, `generated_at`) for audit
- A standing disclaimer: decision-support only; final determination rests with the accrediting body

---

## 4. Workflow

```
track evidence items → score readiness → resolve open critical gaps → generate package → human review → present at survey
```

1. Maintain evidence items as living records (`missing → in_progress → complete`)
2. Monitor readiness (`GET /readiness`) and resolve open critical items first
3. Snapshot readiness for the record (`POST /readiness/snapshot`)
4. Generate the appropriate package type
5. **Human review is required** before any package is used in a survey

---

## 5. Governance & Security

| Principle | Enforcement |
|-----------|-------------|
| Tenant isolation | Packages built only from the requesting tenant's own evidence |
| No cross-tenant data | Packages never include other tenants' or aggregate raw data |
| Auditability | Package generation is audit-logged (`evidence_package_generated`) |
| Human review | Every package carries `human_review_required` framing |
| Claims discipline | No accreditation guarantee; no FDA/regulatory/causation claims |

---

## 6. Endpoints

| Endpoint | Purpose |
|----------|---------|
| `POST /api/accreditation/evidence-items` | Track an evidence item |
| `PATCH /api/accreditation/evidence-items/{id}?status=` | Update evidence status |
| `GET /api/accreditation/evidence-items?tenant_id=` | List evidence |
| `POST /api/accreditation/survey-evidence/generate` | Generate a package |
| `GET /api/accreditation/survey-evidence?tenant_id=` | List generated packages |
| `GET /api/accreditation/survey-evidence/{id}/export` | Render a printable HTML binder (print to PDF in-browser) |

The HTML export renders the full evidence table + readiness summary as a printable document — surveyors get a document, not raw JSON — without adding a server-side PDF dependency.

---

*LumenAI does not claim FDA clearance or regulatory approval. All evidence packages are decision-support artifacts requiring human review.*
