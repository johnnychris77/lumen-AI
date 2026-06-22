# LumenAI Customer Success Playbook

> **Audience:** Customer Success Managers (CSMs) and account teams responsible for adoption, retention, and expansion across LumenAI accounts.

---

## 1. Mission

Drive measurable customer value (labor savings, quality improvement, audit readiness) so accounts adopt deeply, renew reliably, and expand to additional facilities and tiers.

---

## 2. Customer Lifecycle

```
Onboarding → Adoption → Value Realization → Expansion → Renewal
```

| Stage | Goal | Primary Signal |
|-------|------|----------------|
| Onboarding | Live and inspecting within 30 days | Onboarding completion % |
| Adoption | Daily active use by SPD staff | Inspections/active user |
| Value Realization | Documented ROI & quality wins | Modeled savings, contamination trend |
| Expansion | Add facilities / upgrade tier | High utilization signal |
| Renewal | Multi-year commitment | Health score sustained ≥ 80 |

---

## 3. Health Scoring

LumenAI computes a composite **Customer Health Score (0–100)** via
`GET /api/commercial/customer-success/health-score`.

| Dimension | Weight | Source |
|-----------|--------|--------|
| Adoption | 30% | Inspections per active user (derived) |
| Onboarding | 20% | CSM-supplied completion % |
| Training | 20% | CSM-supplied completion % |
| Utilization | 30% | Inspections vs full-utilization target (derived) |

**Status bands:**

| Composite Score | Status | CSM Action |
|-----------------|--------|------------|
| ≥ 80 | Healthy | Pursue expansion / reference |
| 60–79 | Watch | Proactive check-in, adoption plan |
| < 60 | At Risk | Escalate, recovery plan, exec sponsor |

> The health score is an operational triage indicator, **not a clinical measure**. Every output carries `human_review_required: true`.

---

## 4. Onboarding Tracking

CSMs track multi-site onboarding via the enterprise workflow rollup:
`GET /api/commercial/customer-success/onboarding-status?system_id=<id>`

Returns total workflows, completion %, and breakdowns by status and type (site / user / vendor / baseline). See the **Site Onboarding Guide** (`docs/enterprise/site-onboarding-guide.md`) for the 8-step site workflow.

**30-day onboarding targets:**
- [ ] Tenant provisioned, admin logged in
- [ ] ≥ 80% of required users invited and active
- [ ] Baseline coverage ≥ 80% of active tray types
- [ ] Training completion ≥ 95%
- [ ] First 50 inspections submitted

---

## 5. Training Tracking

Training completion feeds the health score (`training_pct`). Required modules (from the site onboarding guide):

| Module | Audience |
|--------|----------|
| Inspection Basics | All inspection staff |
| Quality Review Workflow | SPD Managers, Quality Officers |
| Alert Response Protocol | SPD Managers, Quality Officers |
| Executive Dashboard Overview | Facility leadership |
| Admin & User Management | IT Administrators |

CSMs supply current completion % when querying the health score until an LMS integration persists it automatically.

---

## 6. Adoption & Utilization

- **Adoption:** inspections per active user — measures whether trained users actually use the product.
- **Utilization:** inspections vs the full-utilization target (200 inspections / 30 days per facility) — measures capacity consumption and upsell readiness.

Monitor weekly. A healthy account shows steady or rising inspection trend (`inspection_trend: "up"` or `"flat"`).

---

## 7. Expansion & Renewal Risk

`GET /api/commercial/expansion/opportunities` surfaces two candidate signal sets:

| Signal | Meaning | Recommended Action |
|--------|---------|--------------------|
| `high_utilization` (≥ 80%) | Account near capacity | Upsell capacity / upgrade tier |
| `declining_activity` (≤ −25% MoM) | Renewal risk | CSM outreach, adoption review |

> All signals are **candidate indicators for human review** by the account team — never auto-act on them.

**Expansion plays:**
- Starter → Professional: peer benchmarking + predictive analytics value
- Professional → Enterprise: multi-site hierarchy, autonomous copilot, API
- Enterprise → Health System: SSO, CMMS, dedicated infra, network benchmarking

---

## 8. Quarterly Business Reviews (QBRs)

Cadence by tier (from product packaging):

| Tier | Review Cadence |
|------|----------------|
| Starter | Annual |
| Professional | Semi-annual |
| Enterprise | Quarterly |
| Health System | Monthly |

QBR content: adoption trend, health score, modeled ROI
(`POST /api/commercial/roi/calculate`), quality improvement, open issues, expansion roadmap.

---

## 9. At-Risk Recovery Plan

When health score < 60:
1. Diagnose lowest dimension (adoption / onboarding / training / utilization)
2. Build a 30-day recovery plan with the customer champion
3. Engage executive sponsor for Enterprise/Health System accounts
4. Re-measure health score weekly until ≥ 70
5. Document outcome in the account record

---

*LumenAI does not claim FDA clearance or regulatory approval. All quality and health signals are candidate indicators requiring human review.*
