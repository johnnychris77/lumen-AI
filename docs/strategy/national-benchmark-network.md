# LumenAI National Benchmark Network

> **Audience:** Product, security, and governance leadership. Defines the anonymized benchmark network's participation, governance, and data-sharing controls. Builds on the existing `/api/network` and global-intelligence infrastructure.

---

## 1. Purpose

Provide participating facilities with anonymized peer benchmarking (contamination rates, quality indicators, vendor/instrument patterns) while guaranteeing that no participant can be re-identified and no tenant's raw data is ever exposed.

---

## 2. Anonymized Benchmarking

- Benchmarks are computed from **aggregated, anonymized** participant data only
- Each participant is assigned a **rotating pseudonym**, never a stable identity (`NetworkParticipant.pseudonym`)
- Coarse attributes only: `facility_type` (hospital/health_system/asc), `region` (NE/SE/MW/W), `bed_count_range` (banded, never exact)
- Existing endpoints: `/api/network/benchmarks`, `/api/network/benchmarks/my-percentile`

### k-Anonymity Enforcement
- Network aggregates are **suppressed below a minimum participant threshold** (k-anonymity)
- The P18 market-intelligence summary (`/api/growth/market-intelligence/summary`) enforces a floor of **5 active participants** before exposing any participant-mix breakdown; below it, detail is replaced with a suppression message
- Global intelligence signals require **≥ 5 facilities to contribute** and are only marked publishable at **≥ 10 facilities** (`k_anonymity_verified`)

---

## 3. Participation Model

```
opt-in → contributor/observer/full_member → (opt-out)
```

| Tier | Capability |
|------|-----------|
| observer | View aggregate benchmarks |
| contributor | Contributes anonymized data + views benchmarks |
| full_member | Contributor + advanced cross-network intelligence (Intelligence/Health System tier) |

Managed via `/api/network/opt-in`, `/api/network/opt-in/status`, `/api/network/opt-out`. Participation is **opt-in only** and reversible at any time.

---

## 4. Governance

| Principle | Enforcement |
|-----------|-------------|
| Opt-in only | No facility is in the network without explicit opt-in |
| Reversibility | Opt-out deactivates participation immediately |
| Anonymization | Rotating pseudonyms; coarse attributes; no exact identifiers |
| k-anonymity | Aggregates suppressed below participant/facility floors |
| Tenant isolation | No tenant can query another tenant's raw data — ever |
| Auditability | Every contribution and intelligence-sharing action is audit-logged |
| Human review | All cross-network signals carry `human_review_required: true` |
| No causation | Signals are "potential association" / "investigation candidate" only |

---

## 5. Data-Sharing Controls

**What the network shares:**
- Anonymized aggregate benchmarks (percentiles, rates) when k-anonymity is met
- Anonymized instrument/vendor risk patterns (aggregated)
- Anonymized recall early-warning signals (candidate, human-reviewed)

**What the network never shares:**
- Any participant's raw inspection data
- Any participant's stable identity
- Aggregates below the k-anonymity floor
- Cross-tenant joins of identifiable data

---

## 6. Governance Roles

| Role | Responsibility |
|------|----------------|
| Network Steward | Approves publishable signals after human review |
| Privacy/Security Officer | Validates anonymization and k-anonymity controls |
| Participant Admin | Manages their facility's opt-in/out and tier |
| Executive Sponsor | Owns network growth strategy |

---

## 7. Growth & Trust Flywheel

1. Anchor accounts opt in and seed the network past the k-anonymity floor
2. Benchmarks become meaningful → more value for participants
3. Reference customers (consent-gated) attract new participants
4. Larger network → richer anonymized intelligence → stronger differentiation

Tracked via `/api/growth/market-intelligence/summary` and `/api/growth/kpis` (target: 25 active participants Year 1).

---

## 8. Security Validation Summary (P18 Phase 7)

| Area | Finding |
|------|---------|
| Tenant isolation | Enforced; growth endpoints expose only anonymized aggregates or consented metadata |
| Anonymization | Pseudonyms + coarse attributes + k-anonymity floors |
| Data-sharing governance | Opt-in, reversible, audit-logged; suppression below floors |
| Consent | Reference customers consent-gated and code-enforced |
| Commercialization readiness | Pricing/packaging/ROI (P17) + partnership/reference tracking (P18) in place |
| Claims discipline | No FDA/regulatory/causation language; human review required throughout |

---

*LumenAI does not claim FDA clearance or regulatory approval. All quality outputs are candidate signals requiring human review.*
