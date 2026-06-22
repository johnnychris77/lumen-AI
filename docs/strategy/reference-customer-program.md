# LumenAI Reference Customer Program

> **Audience:** Marketing, customer success, and sales leadership. Defines how pilots become public references, with strict consent governance.

---

## 1. Purpose

Convert satisfied customers into credible, consent-governed references (case studies, ROI proof, testimonials) that accelerate national expansion — without ever exposing a customer's identity or data without explicit permission.

---

## 2. Conversion Funnel

```
pilot → converting → enterprise → reference
```

Tracked via `/api/growth/reference-customers` and reported by `GET /api/growth/conversion-funnel`.

| Stage | Definition |
|-------|------------|
| pilot | Active pilot (see `docs/pilot/`) |
| converting | Pilot succeeded; contracting for enterprise |
| enterprise | Live enterprise customer |
| reference | Consented, citable reference customer |

**Pilot→Enterprise conversion target: ≥ 50%.**

---

## 3. Consent Governance (Critical)

A customer is **never externally citable without explicit consent.**

- New reference records default to `public_reference_consent = false`
- Internal listings **redact** the customer name (`Reference #<id>`) and tenant ID until consent is granted
- Consent is recorded via `POST /api/growth/reference-customers/{id}/consent?consent=true` and is **audit-logged**
- Only consented references appear in `GET /api/growth/reference-customers?public_only=true`
- Consent can be revoked (`consent=false`), which re-redacts the customer

> This consent gate is enforced in code, not just policy — see `_reference_dict(redact=...)` in `app/routes/growth.py`.

---

## 4. Case Study Framework

| Element | Source |
|---------|--------|
| Challenge | Customer SPD pain (manual inspection, audit gaps) |
| Solution | LumenAI deployment scope and tier |
| Adoption | Inspection volume, active users (P17 health score) |
| Quality outcomes | Contamination-trend improvement (candidate signal, human-reviewed) |
| ROI | Modeled savings (`/api/commercial/roi/calculate`) — framed as a model, not a guarantee |
| Quote | Consented testimonial |

Case studies must use quality-improvement language only — **no clinical outcome or causation claims, no FDA/regulatory claims.**

---

## 5. ROI Framework for References

- Use the P17 ROI calculator and executive business case for consistency
- Always present ROI as **modeled and customer-validated**, never guaranteed
- Cite labor savings + reprocessing/cancellation avoidance with stated assumptions

---

## 6. Testimonial Framework

| Status | Meaning |
|--------|---------|
| none | No testimonial |
| requested | Asked, awaiting response |
| draft | Drafted, pending customer approval |
| approved | Customer-approved, citable (requires public consent) |

Testimonials require both `testimonial_status = approved` **and** `public_reference_consent = true` before external use.

---

## 7. Pilot-to-Enterprise Conversion Strategy

1. Define success criteria at pilot start (`docs/pilot/pilot-success-metrics.md`)
2. Track adoption + health score throughout (`/api/commercial/customer-success/health-score`)
3. At pilot exit, generate the executive business case (`/api/commercial/business-case/executive-summary`)
4. Present expansion path (Starter→Professional→Enterprise)
5. On conversion, advance the reference record to `enterprise`, then pursue consent for `reference`

---

## 8. Tracking

| Endpoint | Purpose |
|----------|---------|
| `POST /api/growth/reference-customers` | Create a reference record |
| `POST /api/growth/reference-customers/{id}/consent` | Record/revoke public consent (audit-logged) |
| `POST /api/growth/reference-customers/{id}/roi` | Snapshot modeled ROI (savings + payback) onto the record (audit-logged) |
| `GET /api/growth/reference-customers/{id}/case-study-checklist` | Completeness checklist (consent, ROI, testimonial, quote, published) |
| `GET /api/growth/reference-customers?public_only=` | List (redacted internal or consented public) |
| `GET /api/growth/reference-customers?ready_to_convert=true` | Pilot-stage accounts whose P17 health score is `healthy` — conversion-ready signal |
| `GET /api/growth/conversion-funnel` | Funnel counts + conversion rate |

**Pilot-to-enterprise automation:** `ready_to_convert=true` wires the P17 customer-success health score into the reference lifecycle, surfacing pilots that are conversion-ready so CSMs don't track them manually. All such signals carry `human_review_required: true`.

**ROI linkage:** ROI snapshots captured via `/roi` are stored on the reference record (`modeled_annual_savings_usd`, `roi_payback_months`, `roi_captured_at`) so a case study cites a single, auditable, modeled-and-customer-validated savings figure — never a guarantee.

---

*LumenAI does not claim FDA clearance or regulatory approval. All quality outputs are candidate signals requiring human review.*
