# Executive Scorecard Guide

## Overview

The LumenAI Executive Scorecard provides a consolidated RAG (Red/Amber/Green) status view of pilot KPIs for SPD managers and executive stakeholders. It is generated on demand and is always audit-logged.

## KPI Definitions

| KPI | Target | Green | Amber | Red |
|---|---|---|---|---|
| Weekly inspection volume | 25/week | ≥ 25 | ≥ 20 | < 20 |
| Data completeness | 95% | ≥ 95% | ≥ 76% | < 76% |
| Review rate | 80% | ≥ 80% | ≥ 64% | < 64% |
| Total inspections (90d) | 200 | ≥ 200 | ≥ 160 | < 160 |
| Contamination detection rate | — | tracked | tracked | tracked |
| Estimated pilot ROI | — | estimated | estimated | estimated |

> Thresholds: Green = at/above target; Amber = ≥ 80% of target; Red = < 80% of target.

## Overall Status Logic

| Condition | Overall Status |
|---|---|
| 0 red KPIs, ≤ 1 amber | Green |
| ≤ 1 red KPI | Amber |
| > 1 red KPI | Red |

## Informational KPIs

Contamination detection rate and estimated ROI do not have targets and are displayed as `tracked` or `estimated` status respectively. These are contextual indicators, not pass/fail criteria.

## Access and Audit

- **Required role:** `spd_manager` or `admin`
- Every scorecard access is logged to the audit trail with `action_type: executive_scorecard_accessed`
- The scorecard period is configurable via `?days=` (default 90, max 365)

## API Endpoint

```
GET /api/pilot-analytics/executive-scorecard?days=90
```

## Disclaimer

Scorecard values are quality indicators derived from inspection data. ROI estimates require validation against site financial data before external reporting. Human review is required for all decisions informed by this scorecard.
