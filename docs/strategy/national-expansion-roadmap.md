# LumenAI National Expansion Roadmap

> **Status:** Internal strategy. Builds on the P16 multi-site rollout model and P17 commercial framework. All quality signals require human review; LumenAI makes no FDA clearance or regulatory claims.

---

## 1. Vision

Scale LumenAI from validated pilots and early enterprise deployments into a nationally recognized SPD (Sterile Processing Department) intelligence platform, anchored by a trusted anonymized benchmark network.

---

## 2. Expansion Models

### 2.1 Regional Expansion Model
- Establish 1–2 **anchor health systems** per region (Northeast, Southeast, Midwest, West)
- Use anchor references to drive regional density (shorter sales cycles, peer benchmarking value)
- Regional CSM pods aligned to the enterprise hierarchy (system → market → region)
- Target: 3 active regions in Year 1, 4 regions by end of Year 2

### 2.2 Enterprise Deployment Model
- Land via Enterprise/Health System tier (see `docs/commercial/product-packaging.md`)
- Deploy with the wave-based rollout (`docs/enterprise/multi-site-rollout-playbook.md`)
- Standardize on the 8-step site onboarding workflow and facility readiness scoring
- Expand within a system facility-by-facility using P17 utilization/expansion signals

### 2.3 Academic Medical Center (AMC) Strategy
- AMCs are reference-grade design partners (high complexity, teaching influence)
- Value levers: full predictive suite, autonomous copilot, RWE program participation
- Engage clinical/quality faculty for evidence collaboration (no clinical claims; quality-improvement framing only)
- Offer benchmark-network leadership roles to AMCs to seed credibility

### 2.4 Ambulatory Surgery Center (ASC) Strategy
- ASCs are higher-volume, lower-complexity, faster to deploy
- Package: Starter/Professional with ASC-appropriate baseline libraries
- Sell through ASC management organizations and GPOs for scale
- Emphasize fast time-to-value and audit readiness

---

## 3. Phased Roadmap

| Phase | Horizon | Focus | Exit Criteria |
|-------|---------|-------|---------------|
| A — Anchor | Q1–Q2 | 2–3 reference accounts across regions | ≥ 3 public reference customers |
| B — Density | Q3–Q4 | Regional clustering + GPO agreements | ≥ 2 GPO frameworks, 10 active facilities |
| C — Network | Year 2 H1 | Benchmark network ≥ k-anonymity floor | ≥ 25 active network participants |
| D — Scale | Year 2 H2 | Health System tier + AMC leadership | National multi-region footprint |

---

## 4. Tracking & Tooling

P18 introduces growth tooling under `/api/growth`:
- **Reference-customer program:** conversion funnel (`/conversion-funnel`), consent-gated public references
- **Strategic partnerships:** `/partnerships` (manufacturers, vendors, industry orgs, GPOs)
- **Market intelligence:** `/market-intelligence/summary` (anonymized, k-anonymity enforced)
- **Growth KPIs:** `/kpis`

Existing intelligence infrastructure is reused, not rebuilt: `/api/network` (benchmark opt-in/out), `/api/enterprise/benchmarks` (executive dashboards), `/api/manufacturer-intelligence` (manufacturer dashboards).

---

## 5. Growth KPIs

| KPI | Year 1 Target |
|-----|---------------|
| Active benchmark participants | 25 |
| Active strategic partnerships | 10 |
| Reference customers | 15 |
| Pilot → Enterprise conversion | ≥ 50% |
| Active regions | 3 |

---

## 6. Risks & Mitigation

| Risk | Mitigation |
|------|-----------|
| Benchmark network below k-anonymity floor | Suppress aggregates until ≥ 5 participants; seed via anchor accounts |
| Reference customer overexposure / consent gaps | Consent-gated reference model; names redacted without explicit consent |
| Over-claiming clinical/regulatory outcomes | Enforced disclaimers; no FDA/causation language anywhere |
| Tenant data leakage across systems | Strict tenant isolation; only anonymized aggregates exposed; audit logging |
| Sales cycle length at health systems | GPO agreements + reference proof to compress cycles |
| Partner channel conflict | Clear partnership tiers and rules of engagement (see partnership framework) |

---

*LumenAI does not claim FDA clearance or regulatory approval. All quality outputs are candidate signals requiring human review.*
