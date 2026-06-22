# LumenAI Accreditation Readiness Framework

> **Audience:** Quality, accreditation, and SPD leadership. Defines how LumenAI supports survey readiness across Joint Commission, DNV, CMS, HFAP, and state survey — **as a decision-support tool, not a guarantee of accreditation.** LumenAI makes no FDA clearance or regulatory-approval claims.

---

## 1. Purpose

Help sterile processing departments continuously prepare for accreditation and regulatory surveys by tracking evidence, scoring readiness, and generating survey-ready documentation — while keeping every output human-reviewed and tenant-isolated.

---

## 2. Supported Accreditors

| Accreditor | `accreditor` code | Scope |
|------------|-------------------|-------|
| The Joint Commission | `joint_commission` | Hospital accreditation, IC standards |
| DNV Healthcare | `dnv` | NIAHO / ISO 9001-based accreditation |
| CMS | `cms` | Conditions of Participation, deemed status |
| HFAP / ACHC | `hfap` | Accreditation Commission programs |
| State Survey | `state` | State-specific licensure / survey readiness |

Programs are tracked via `POST /api/accreditation/programs` with lifecycle `preparing → scheduled → surveyed → accredited` (`PATCH /programs/{id}?status=`).

---

## 3. Readiness Engine (Phase 2)

Three complementary scores are computed from a facility's tracked evidence items (`/api/accreditation/readiness`):

| Score | Definition |
|-------|------------|
| **Evidence completeness** | `(complete + 0.5 × in_progress) / total × 100` |
| **Risk score** | `0.6 × (incomplete share) + critical penalty` (open critical items weighted heavily; 0–100, higher = more risk) |
| **Readiness score** | `0.7 × completeness + 0.3 × (100 − risk)`; capped below "ready" while any critical item is open |

Readiness status bands: **ready ≥ 85**, **approaching ≥ 65**, **not_ready < 65**.

- Snapshots are persisted for reproducibility and trend history (`POST /readiness/snapshot`, `GET /readiness/trend`).
- Every readiness output carries `human_review_required: true` and a disclaimer that final determination rests with the accrediting body.

---

## 4. Evidence Model

Evidence items (`/api/accreditation/evidence-items`) carry:
- `standard_ref` (e.g. "AAMI ST79", "Joint Commission IC.02.02.01" — reference only, no compliance guarantee)
- `category`, `title`, `status` (`missing | in_progress | complete`)
- `is_critical` — critical gaps heavily penalize the risk score and cap readiness status

---

## 5. Governance & Security

| Principle | Enforcement |
|-----------|-------------|
| Tenant isolation | Evidence and readiness are scoped per tenant/facility; no cross-tenant reads |
| Auditability | Every program/evidence/readiness/package mutation is audit-logged with `compliance_flag` |
| Human review | All scores and packages require human review before survey use |
| Claims discipline | No guarantee of accreditation; no FDA/regulatory/causation claims |
| Standards references | Standards cited for alignment only — not as certified compliance |

---

## 6. Industry Leadership Roadmap (Accreditation)

| Horizon | Milestone |
|---------|-----------|
| Q1–Q2 | Evidence libraries per accreditor; readiness scoring live at anchor sites |
| Q3–Q4 | Survey binder generation standard in enterprise rollouts |
| Year 2 | Certified-site program + benchmark publications establish category leadership |

---

*LumenAI does not claim FDA clearance or regulatory approval. All readiness and quality outputs are decision-support indicators requiring human review.*
