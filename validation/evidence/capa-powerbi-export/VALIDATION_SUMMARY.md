# LumenAI CAPA Power BI Export Evidence Lock v1

## Validation Status
PASSED

## Module
CAPA Workflow

## Capability
Power BI-ready CAPA CSV export

## Production Endpoint
GET /api/capa/powerbi-csv?limit=500

## Production URL
https://lumen-ai-53u4.onrender.com/api/capa/powerbi-csv?limit=500

## Export Format
text/csv

## Validated CSV Fields
- capa_id
- title
- source
- risk_level
- status
- owner
- due_date
- created_at
- updated_at
- days_to_due
- is_overdue
- is_high_risk
- is_open
- corrective_action
- preventive_action
- description

## Frontend Integration
The CAPA Workflow Panel includes a visible frontend button:

Download Power BI CSV

The button opens:

https://lumen-ai-53u4.onrender.com/api/capa/powerbi-csv?limit=500

## Validation Note
A HEAD request using curl -I returns HTTP 405 because the endpoint supports GET. Browser downloads and standard curl GET requests work as expected.

## Evidence Files
- headers.txt
- lumenai-capa-powerbi.csv
- VALIDATION_SUMMARY.md

## Business Value
The CAPA Power BI export enables CAPA data to be used in Power BI, executive dashboards, governance scorecards, overdue tracking, high-risk CAPA monitoring, and quality leadership reporting.

## Final Result
LumenAI CAPA Power BI Export Evidence Lock v1 is complete.
