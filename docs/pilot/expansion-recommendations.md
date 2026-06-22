# Pilot Expansion Recommendations Framework

## Quarterly Review Package

The LumenAI quarterly review package (`GET /api/pilot-analytics/quarterly-review`) generates a 90-day summary with structured expansion recommendations and go/no-go criteria.

## Success Criteria for Expansion

| Criterion | Target | Assessment |
|---|---|---|
| Inspection volume | ≥ 800 total / ≥ 25/week | Volume check via adoption metrics |
| Data completeness | ≥ 95% | Mandatory for data integrity |
| Active sites | ≥ 3 | Multi-site validation required |
| CAPA signal generation | ≥ 1 actionable CAPA from data | Demonstrates operational value |
| Stakeholder satisfaction | ≥ 3.5 / 5.0 | Measured via weekly pulse survey |

A **go recommendation** requires meeting ≥ 4 of 5 criteria. A no-go triggers a 4-week remediation period before re-evaluation.

## Expansion Recommendation Logic

| Criteria Met | Recommendation |
|---|---|
| ≥ 4 of 5 | `expand` — proceed to broader rollout planning |
| 3 of 5 | `conditional_expand` — address gaps before expanding |
| ≤ 2 of 5 | `extend_pilot` — 4-week remediation; re-evaluate |

## Expansion Planning Checklist

When recommendation is `expand`:

1. Identify next 3–5 target sites based on surgical volume and SPD staffing
2. Confirm data governance agreements are in place for new tenants
3. Scale tenant provisioning (`POST /api/admin/tenants`) for new sites
4. Validate that CAPA signals from pilot are represented in post-market surveillance documentation
5. Schedule executive briefing with expansion timeline and ROI projection
6. Confirm site coordinator training capacity for expanded cohort

## What Must Remain True at Scale

- Tenant data isolation must be enforced — no cross-tenant data access
- All AI outputs must include `human_review_required: true`
- Hospital identities must remain anonymised in any cross-site analytics
- Every audit-logged export must be reviewed before external sharing
- LumenAI does not claim FDA clearance; regulatory review continues independently

## API Endpoint

```
GET /api/pilot-analytics/quarterly-review
```

Response includes: `expansion_recommendations`, `success_criteria`, `pilot_summary`, `human_review_required: true`.
