# LumenAI Benchmark Publication Program

> **Audience:** Product, governance, and marketing leadership. Defines how LumenAI publishes anonymized industry benchmarks to establish ecosystem leadership — under strict k-anonymity and claims discipline. No FDA/regulatory/causation claims.

---

## 1. Purpose

Publish credible, anonymized industry intelligence (annual benchmark reports, contamination-trend reports, industry intelligence reports) that position LumenAI as the category authority — **without ever exposing a participant's identity or raw data.**

---

## 2. Publication Types

| Publication | Cadence | Content |
|-------------|---------|---------|
| **Annual Benchmark Report** | Annual | Network-wide anonymized percentiles, participant mix, methodology |
| **Industry Intelligence Report** | Quarterly | Emerging anonymized patterns (vendor/instrument), candidate signals |
| **Contamination Trend Report** | Quarterly | Anonymized contamination-indicator trends (candidate signals, human-reviewed) |

The annual report is served by `GET /api/accreditation/benchmark-publications/annual-report`, built from the existing benchmark network (`/api/network`) aggregates.

---

## 3. Methodology

- Built from **aggregated, anonymized** participant data only — never raw tenant data
- Participants identified by **rotating pseudonyms**; coarse attributes only (`facility_type`, `region`, banded bed count)
- **Laplace noise** applied to published aggregates
- **k-anonymity floor of 5 active participants** — any report (or per-region cut) below the floor is suppressed
- Every quality/contamination figure is a **candidate signal requiring human review** — never causation

---

## 4. Governance

| Principle | Enforcement |
|-----------|-------------|
| Opt-in only | Only opted-in network participants contribute |
| k-anonymity | Reports suppressed below the participant floor |
| Anonymization | Pseudonyms + coarse attributes + noise |
| Human review | Network steward approves publishable signals |
| No causation | "Potential association" / "investigation candidate" only |
| No regulatory claims | No FDA clearance or regulatory-approval language |

---

## 5. Methodology Validation (Phase 8)

| Area | Finding |
|------|---------|
| Benchmark methodology | Aggregation + noise + k-anonymity floor documented and enforced in code |
| Data governance | Opt-in, reversible, audit-logged; no raw cross-tenant exposure |
| Security | Tenant isolation enforced; publications expose only anonymized aggregates |
| Claims discipline | Candidate signals + human review; no FDA/regulatory/causation claims |

---

## 6. Endpoints

| Endpoint | Purpose |
|----------|---------|
| `GET /api/accreditation/benchmark-publications/annual-report` | Anonymized annual industry benchmark (k-anonymity enforced) |
| `POST /api/accreditation/benchmark-publications/publish` | Archive a dated, immutable edition (rejected below the k-anonymity floor) |
| `GET /api/accreditation/benchmark-publications` | List archived editions (reproducible publication history) |
| `GET /api/growth/benchmark-trends` | Anonymized network metric trend history (k-anonymity enforced) |
| `GET /api/growth/market-intelligence/by-region` | Per-region participant mix (per-region k-anonymity) |

---

*LumenAI does not claim FDA clearance or regulatory approval. All published benchmarks are anonymized aggregates; quality indicators are candidate signals requiring human review.*
