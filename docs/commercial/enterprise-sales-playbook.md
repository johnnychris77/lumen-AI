# LumenAI Enterprise Sales Playbook

> **Audience:** Account executives and sales leadership pursuing health system and multi-facility enterprise deals.

---

## 1. Ideal Customer Profile (ICP)

| Attribute | Target |
|-----------|--------|
| Organization | IDN, health system, academic medical center, GPO member |
| Facilities | 3+ (Enterprise), 10+ (Health System) |
| SPD volume | 6,000+ inspections/month aggregate |
| Pain | Manual lumen inspection, audit-readiness gaps, contamination events, multi-site inconsistency |
| Budget owner | COO, CFO, VP Surgical Services, VP Supply Chain, CNO |

---

## 2. Value Proposition by Persona

| Persona | Primary Value |
|---------|---------------|
| COO | Operational consistency across sites, audit readiness |
| CFO | Documented labor savings + quality-event avoidance (ROI) |
| CNO / VP Surgical | Patient-safety quality signals, reduced reprocessing/cancellations |
| VP Supply Chain | Vendor/manufacturer accountability, baseline governance |
| SPD Director | Faster, AI-assisted inspection with audit trail |

---

## 3. Packaging & Tier Selection

Match the prospect to a tier (see `product-packaging.md`):

| Facilities | Recommended Tier |
|-----------|------------------|
| 1 | Starter |
| 2–3 | Professional |
| 3–10 | Enterprise |
| 10+ | Health System |

Use `POST /api/commercial/pricing/estimate` to generate a live, non-binding estimate including multi-facility (10%/20%) and multi-year (10%/15%) discounts.

---

## 4. Enterprise Sales Motion

```
Discovery → Demo → Pilot → Business Case → Procurement → Rollout
```

### 4.1 Discovery
- Map the hierarchy: system → markets → regions → facilities → departments
- Quantify inspection volume, SPD FTEs, contamination/reprocessing pain
- Identify champion and economic buyer

### 4.2 Demo
- Run the executive + pricing flows (see `demo-environment-guide.md`)
- Tailor the ROI calculator to the prospect's volume

### 4.3 Pilot
- Use the pilot framework (`docs/pilot/`) for a 90-day proof-of-value
- Define success criteria up front (adoption, quality, ROI)

### 4.4 Business Case
- Generate ROI model: `POST /api/commercial/roi/calculate`
- Generate executive summary: `GET /api/commercial/business-case/executive-summary`
- Present labor savings, quality-event avoidance, payback months
- Frame all quality data as candidate signals requiring human review

### 4.5 Procurement
- GPO pricing via Premier/Vizient/HPG to shorten cycle
- Multi-year term for discount + churn reduction
- HIPAA BAA, security review, SSO requirements for Health System tier

### 4.6 Rollout
- Hand off to deployment per `docs/enterprise/multi-site-rollout-playbook.md`
- Use wave-based site onboarding
- CSM engages per `customer-success-playbook.md`

---

## 5. ROI & Business Case Methodology

ROI is modeled from validated pilot constants:
- Labor savings: 4.5 min saved/inspection × $35/hr staff cost
- Reprocessing avoidance: 60% capture × $85/event
- Cancellation avoidance: 1% capture × $12,000/case

Always present as a **model requiring customer validation** — never a guarantee.

---

## 6. Expansion Strategy (Land and Expand)

1. **Land:** single facility or department (Starter/Professional) or a focused pilot
2. **Prove:** document adoption, quality wins, and ROI
3. **Expand:** add facilities, upgrade tier; trigger from `high_utilization` signals in `GET /api/commercial/expansion/opportunities`
4. **Standardize:** system-wide rollout under Enterprise/Health System with central governance

---

## 7. Competitive Positioning

| Competitor Category | LumenAI Advantage |
|--------------------|-------------------|
| Manual / spreadsheet audit | AI detection, audit trail, benchmarking |
| Legacy tracking software | CV detection, predictive analytics, copilot |
| General clinical AI platforms | SPD-specific, faster ROI, lower complexity |
| Full CMMS suites | Focused scope, faster deployment, SPD-first |

---

## 8. Objection Handling

| Objection | Response |
|-----------|----------|
| "Is this FDA cleared?" | LumenAI does not claim FDA clearance; it is a decision-support tool with human-in-the-loop review. |
| "Can it replace our techs?" | No — it assists trained staff; all findings require human review. |
| "How do we know the ROI is real?" | We model from validated pilot constants and validate against your own data in a pilot. |
| "Data security across sites?" | Strict tenant isolation; no tenant sees another's raw data; every cross-org action is audit-logged. |

---

## 9. Deal Desk & Discounting

| Authority | Max Discount |
|-----------|--------------|
| AE | 15% |
| VP Sales | 25% |
| CEO/CPO | >25% |
| Strategic (reference/case study) | up to 40% |

The pricing estimate API caps modeled discounts at 40% to match this ceiling.

---

## 10. National Expansion Roadmap (see milestone deliverable)

- **Phase A:** Reference accounts in 2–3 regions
- **Phase B:** GPO agreements (Premier/Vizient/HPG) for procurement velocity
- **Phase C:** Health System tier with SSO/CMMS/dedicated infra
- **Phase D:** Intelligence/network benchmarking as a cross-system differentiator

---

*LumenAI does not claim FDA clearance or regulatory approval. All quality outputs are candidate signals requiring human review.*
