# Anonymization Specification — National SPD Intelligence Network

## Purpose

This document defines the technical implementation of anonymization controls applied to all data shared across the National SPD Intelligence Network. All engineers implementing network data pipelines must adhere to these specifications.

---

## 1. Pseudonym Rotation

### Algorithm
```
pseudonym = SHA-256(facility_id + monthly_salt)[:12]
```

### Implementation
- **Input**: raw `facility_id` (tenant identifier) and `monthly_salt`
- **Salt format**: `YYYY-MM` (e.g., `2025-06`)
- **Salt rotation**: on the 1st of each calendar month at 00:00 UTC
- **Output**: first 12 hex characters of SHA-256 digest
- **Storage**: pseudonyms stored in `network_participants.pseudonym`; raw `tenant_id` never stored in cross-tenant tables

### Salt Management
- Monthly salt generated from: `HMAC-SHA256(master_key, "YYYY-MM")`
- Master key stored in LumenAI KMS (AWS KMS or equivalent)
- Salt never logged, never exposed in API responses, never stored in application DB

### Python Reference Implementation
```python
import hashlib

def anonymize_facility_id(facility_id: str, month_salt: str) -> str:
    digest = hashlib.sha256(f"{facility_id}{month_salt}".encode()).hexdigest()
    return digest[:12]
```

---

## 2. Minimum Cohort Size (K-Anonymity, k ≥ 5)

### Rule
Never publish an aggregate value if fewer than 5 distinct facilities contributed to that cohort.

### Applied To
- Industry benchmark distributions (all cohorts: `all`, `hospital`, `region`, etc.)
- Instrument registry network stats (`contributing_facilities` field)
- Any sliced/filtered view of aggregate metrics

### Enforcement
```python
MIN_FACILITIES = 5

def publish_metric(value, n_facilities):
    if n_facilities < MIN_FACILITIES:
        return None  # suppress entirely — do not return the value
    return value
```

### API Behavior
- Suppressed fields return `null` (not 0, not omitted)
- `suppressed: true` flag included in response when suppression occurs
- Error messages must not reveal the actual N (e.g., "suppressed due to insufficient data")

---

## 3. Differential Privacy — Laplace Mechanism

### Parameters
- **Sensitivity (Δf)**: 0.01 (maximum change in aggregate rate from one facility's data)
- **Privacy budget (ε)**: 0.1 (strong privacy guarantee)
- **Scale (b)**: Δf / ε = 0.1

### Algorithm
```python
import math
import random

def add_laplace_noise(value: float, sensitivity: float = 0.01, epsilon: float = 0.1) -> float:
    scale = sensitivity / epsilon
    u = random.uniform(-0.4999, 0.4999)
    noise = -scale * math.copysign(1, u) * math.log(1 - 2 * abs(u))
    return max(0.0, min(1.0, value + noise))
```

### Application Points
- Applied **after** k-anonymity check
- Applied to: P25, P50, P75, P90, mean values in all benchmark distributions
- Applied to: network_defect_rate, network_pass_rate in instrument registry
- **Not** applied to: count fields (n_facilities, network_inspection_count) — these are already bounded

### Privacy Budget Management
- ε = 0.1 per query per metric per month
- Composition: multiple queries to same data do not amplify — noise is pre-applied at aggregation time
- Budget reset: monthly (aligned with salt rotation)

---

## 4. Suppression Rules

### Cell Suppression (Count < 3)
Any individual cell (metric × cohort × time period) where the contributing facility count is less than 3 is entirely suppressed:

| Condition | Action |
|-----------|--------|
| N < 3 contributing facilities | Suppress cell; return `null` |
| N = 3–4 contributing facilities | Apply k-anonymity suppression (k ≥ 5) |
| N ≥ 5 contributing facilities | Apply Laplace noise; publish |

### Recall Signal Suppression
Signal is not surfaced if:
- N < 3 facilities reporting the pattern, OR
- signal_strength ≤ 0.3

### Regional Cohort Suppression
Regional breakdowns (e.g., "northeast") suppressed if fewer than 5 facilities in that region are active participants.

### Linked-Table Suppression
Cross-table joins that could enable re-identification are prohibited at the query layer. Network queries only access pre-aggregated views, never raw tenant tables.

---

## 5. Audit Trail for Anonymization

Every anonymization decision is logged:
- Timestamp of aggregation run
- Metric name and cohort
- N facilities contributing (not which facilities)
- Whether suppression was applied
- Noise seed reference (not the seed itself)

Audit logs are immutable and retained for 7 years per compliance requirements.
