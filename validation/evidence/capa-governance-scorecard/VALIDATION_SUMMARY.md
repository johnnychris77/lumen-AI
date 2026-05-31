# LumenAI CAPA Governance Scorecard Evidence Lock v1

## Validation Status
PASSED

## Module
CAPA Governance Scorecard

## Capability
Executive CAPA governance performance scorecard

## Production Endpoint
GET /api/capa/governance-scorecard?days_until_due=7

## Production URL
https://lumen-ai-53u4.onrender.com/api/capa/governance-scorecard?days_until_due=7

## Validated Backend Output
The CAPA Governance Scorecard endpoint returns a production JSON response with:
- status
- module
- version
- governance_status
- scorecard
- signals
- message

## Validated Scorecard Fields
- total_capas
- open_capas
- closed_capas
- high_risk_capas
- overdue_capas
- due_soon_capas
- high_risk_overdue_capas
- requires_escalation
- closure_rate_percent
- powerbi_export_ready

## Frontend Integration
The main LumenAI dashboard includes the CAPA Governance Scorecard frontend component.

Validated frontend section:
- CAPA Governance Scorecard · Executive View
- CAPA Governance Performance
- Governance Status
- Total CAPAs
- Open CAPAs
- Closed CAPAs
- High Risk
- Overdue
- Due Soon
- Requires Escalation
- Closure Rate
- Power BI Export
- Governance Interpretation

## Business Value
The CAPA Governance Scorecard gives leadership an executive view of CAPA performance, overdue risk, high-risk CAPAs, escalation needs, closure rate, and Power BI export readiness.

## Evidence Files
- headers.txt
- governance-scorecard.json
- VALIDATION_SUMMARY.md

## Final Result
LumenAI CAPA Governance Scorecard Evidence Lock v1 is complete.
