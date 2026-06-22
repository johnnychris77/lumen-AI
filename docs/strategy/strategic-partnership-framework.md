# LumenAI Strategic Partnership Framework

> **Audience:** Partnerships and business development leadership. Defines partner types, tiers, rules of engagement, and tracking.

---

## 1. Partner Types

| Type | Description | Primary Value Exchange |
|------|-------------|------------------------|
| **Manufacturer** | Device/instrument OEMs | Publish manufacturer baselines; receive anonymized defect/recall intelligence on their own products |
| **Vendor** | Reprocessing/repair/distribution vendors | Vendor scorecards; baseline subscription revenue |
| **Industry Organization** | AAMI, IAHCSMM/HSPA, professional bodies | Credibility, standards alignment, education channels |
| **GPO** | Premier, Vizient, HealthTrust | Procurement velocity, contracted pricing, member reach |

These map to the `partner_type` enum in `/api/growth/partnerships`: `manufacturer`, `vendor`, `industry_org`, `gpo`.

---

## 2. Partnership Lifecycle

```
prospect → engaged → active → (inactive)
```

Tracked via `POST /api/growth/partnerships` and `PATCH /api/growth/partnerships/{id}?status=`. Every status change is audit-logged.

| Stage | Definition |
|-------|------------|
| prospect | Identified, not yet in discussion |
| engaged | Active discussions / pilot of partnership |
| active | Signed/operational partnership |
| inactive | Paused or ended |

---

## 3. Partnership Tiers

| Tier | Benefits | Typical Partner |
|------|----------|-----------------|
| Standard | Baseline publishing, scorecards | Most vendors |
| Premium | Priority baseline review, co-marketing, defect trend access | Strategic manufacturers |
| Strategic | Joint roadmap, network leadership, co-developed evidence | AMCs, major OEMs, GPOs |

---

## 4. Manufacturer Partnerships

- Manufacturers publish reference baselines; **hospital approval is always required** before a vendor/manufacturer baseline becomes active (no auto-trust)
- Manufacturers receive intelligence **only about their own products**, as anonymized aggregates (see `/api/manufacturer-intelligence`)
- Manufacturers never receive raw hospital data or competitor data
- Recall/defect early-warning signals are candidate indicators requiring human review

---

## 5. GPO Partnerships

- Negotiate contracted pricing aligned to `docs/commercial/pricing-strategy.md` (GPO pricing lever)
- GPO membership accelerates procurement and de-risks budget approval
- Co-market reference outcomes (consent-gated) to GPO membership

---

## 6. Industry Organization Partnerships

- Align product language with AAMI ST79 and related standards (reference only — no compliance guarantees)
- Contribute to education and best-practice content
- Pursue speaking/contributed-content channels for credibility

---

## 7. Rules of Engagement (Channel Conflict)

- Direct enterprise sales and GPO/partner-sourced deals are registered to avoid conflict
- Manufacturer intelligence is firewalled per-manufacturer (no competitor visibility)
- Partners never gain access to tenant raw data — only anonymized, consented, or own-product aggregates
- All partner-facing data exchange is audit-logged

---

## 8. Data-Sharing Guardrails for Partners

| Partner sees | Partner never sees |
|--------------|--------------------|
| Their own products' anonymized aggregates | Any hospital's raw inspection data |
| Consented reference customer outcomes | Non-consented customer identities |
| Network-level anonymized benchmarks (k-anonymity met) | Competitor product data |

---

## 9. Tracking

| Endpoint | Purpose |
|----------|---------|
| `POST /api/growth/partnerships` | Register a partner (optional `next_review_date` for SLA tracking) |
| `GET /api/growth/partnerships` | List/filter partners, counts by type; `overdue_review=true` surfaces partnerships past their review date; response includes `escalations` count |
| `PATCH /api/growth/partnerships/{id}?status=` | Advance lifecycle stage (stamps `status_changed_at`) |
| `POST /api/growth/partnerships/{id}/notes` | Append a timestamped engagement note / touchpoint (audit-logged) |
| `GET /api/growth/partnerships/{id}/notes` | List engagement notes |
| `GET /api/growth/kpis` | Active-partnership KPI |

**SLA & escalation:** Each partnership carries an optional `next_review_date` (flagged `review_overdue` when past due) and a `status_changed_at` timestamp. A partnership stalled in `engaged` longer than **90 days** raises an `escalation` flag for CSM follow-up.

---

*LumenAI does not claim FDA clearance or regulatory approval. All intelligence outputs are candidate signals requiring human review.*
