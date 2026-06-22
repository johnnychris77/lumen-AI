# Global Quality Registry

**Version:** 1.0 | **Classification:** Data Governance | **Status:** Active

**Important:** Registry data represents anonymized aggregations. No facility, patient, or individual instrument is identifiable from published registry entries. All registry outputs are decision-support signals — not regulatory findings, clinical determinations, or quality certifications.

---

## Overview

The Global Quality Registry (GQR) is a privacy-preserving, aggregated repository of surgical instrument quality metrics drawn from participating facilities. It enables network-level benchmarking, trend identification, and early warning detection while guaranteeing that no individual facility's data can be isolated from the aggregate.

---

## Registry Entry Types

| Type | Description | Key Metrics |
|------|-------------|-------------|
| `contamination` | Contamination event rates by instrument category | rate, severity_distribution |
| `defect` | Defect incidence by type and severity | rate, severity_distribution |
| `baseline` | Baseline quality variance from network median | rate (variance %), severity_distribution |
| `reliability` | Mean cycles between quality failures | rate (MCBF), severity_distribution |

---

## Privacy Architecture

### K-Anonymity Floor
- Minimum **5 contributing facilities** required before a registry entry is published
- If fewer than 5 facilities contribute data to a given category/period combination, the entry is suppressed entirely
- `k_anonymity_verified: true` is set only when the floor has been confirmed
- Contributing facility count is published alongside the rate; facility identities are never published

### Anonymization Guarantees
- Facility names, tenant IDs, and geographic identifiers below region level are stripped
- Instrument serial numbers and internal IDs are excluded from all registry entries
- Patient data is never collected into instrument quality records — no PHI flows into the registry
- Rates and distributions are computed as network aggregates, with Laplace noise applied to small-count cells

### Data Residency
- Registry aggregations are computed within each regulatory jurisdiction
- Cross-border registry sharing requires explicit data transfer approval per the International Deployment Framework
- Raw contributing data never leaves its originating jurisdiction

---

## Contribution Model

Facilities contribute to the registry through the normal course of inspection, sterilization, and CAPA operations. Contribution is:
- **Automatic** for facilities enrolled in the Global Surgical Intelligence Network (GSIN)
- **Voluntary** for facilities using Lumen AI outside GSIN
- **Always anonymized** — no facility opts in to identified publication

Contribution eligibility:
- Facility must have completed DPA (Data Processing Agreement) signing
- Minimum 30-day operation period before first contribution
- At least 50 instrument lifecycle events in the contribution period

---

## Registry API

### Read (Researcher / Governance / Hospital)
```
GET /api/infrastructure/quality-registry
?registry_type=contamination|defect|baseline|reliability
&instrument_category=<optional>
&period=<YYYY-MM optional>
```

All responses include:
- `anonymized: true`
- `k_anonymity_verified: true|false`
- `contributing_facilities`: integer count (not list)
- `human_review_required: true`
- `disclaimer`: standard quality-support language

### Access Control
| Consumer | Access Tier |
|----------|-------------|
| Hospital | Own data + anonymized network aggregate |
| Manufacturer | Anonymized aggregate by instrument category |
| Researcher | Anonymized aggregate, all categories |
| Governance | Full aggregate + k-anonymity audit trail |

---

## Quality Signal Lifecycle

```
Raw facility event
       │
       ▼
Anonymization layer (strip identifiers)
       │
       ▼
Aggregation engine (group by type/period/category)
       │
       ▼
K-anonymity check (≥5 facilities?)
       │ Yes                    │ No
       ▼                        ▼
Published to registry     Suppressed (held until floor met)
       │
       ▼
Available via API with anonymized: true
```

---

## Governance

- Registry publication decisions are logged as audit events
- Any suppressed entries are retained for 12 months in case the k-anonymity floor is later met
- Registry entries are versioned; corrections create new versions rather than overwriting
- External researchers accessing registry data must have an active `IndustryAPICredential` with `registry` scope
- All access is logged; aggregate access patterns are reviewed quarterly

---

## Limitations and Disclaimers

- Registry rates reflect data submitted to Lumen AI; they are not population-level epidemiological estimates
- Network medians are influenced by the composition of participating facilities — academic medical centers and community hospitals may have different baseline rates
- The registry does not constitute a regulatory database or replace mandatory adverse event reporting obligations
- "Potential association" language used in all registry comparative outputs — causation is never implied
