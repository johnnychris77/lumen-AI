# LumenAI Vendor Governance Power BI Export Evidence Lock v1

## Validation Status
PASSED

## Module
Vendor Governance

## Capability
Power BI-ready Vendor Governance CSV export

## Production Endpoint
GET /api/enterprise/vendor-governance/powerbi-csv?limit=500

## Production URL
https://lumen-ai-53u4.onrender.com/api/enterprise/vendor-governance/powerbi-csv?limit=500

## Export Format
text/csv

## Validated CSV Fields
- vendor_event_id
- vendor_name
- event_type
- event_summary
- risk_level
- site
- device_or_tray
- owner
- status
- capa_id
- is_high_risk
- is_linked_to_capa
- created_at
- updated_at

## Frontend Integration
The Vendor Governance Panel includes a visible frontend button:

Download Vendor Power BI CSV

The button opens:

https://lumen-ai-53u4.onrender.com/api/enterprise/vendor-governance/powerbi-csv?limit=500

## Validation Note
The endpoint should be validated using a GET request. Browser downloads and standard curl GET requests work as expected.

## Evidence Files
- headers.txt
- lumenai-vendor-governance-powerbi.csv
- VALIDATION_SUMMARY.md

## Business Value
The Vendor Governance Power BI export enables vendor quality event data to be used in Power BI, vendor trend dashboards, high-risk vendor event reporting, CAPA linkage reporting, and executive governance scorecards.

## Final Result
LumenAI Vendor Governance Power BI Export Evidence Lock v1 is complete.
