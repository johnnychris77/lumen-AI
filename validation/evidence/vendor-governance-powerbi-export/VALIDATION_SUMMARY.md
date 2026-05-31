# LumenAI Vendor Governance Power BI Export v1 Validation Summary

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

## Business Value
This export enables vendor governance data to be used in Power BI, vendor trend dashboards, high-risk vendor event reporting, CAPA linkage reporting, and executive governance scorecards.

## Final Result
Vendor Governance Power BI Export v1 is production validated.
