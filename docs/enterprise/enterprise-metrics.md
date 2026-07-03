# Enterprise Metrics

The ongoing metrics tracked across every customer, beyond the one-time
30/60/90-day checkpoints.

## Metric definitions and sources

| Metric | Definition | Source |
|---|---|---|
| **Deployment Success** | Did the site reach Day 30 go-live on the planned timeline? | `docs/customer/implementation-timeline.md` tracking |
| **Adoption Rate** | Fraction of expected inspections actually captured through LumenAI vs. expected volume for the site's size | `/api/pilot-analytics/inspection-efficiency` volume vs. segment benchmark (`docs/commercial/roi-model.md`) |
| **User Engagement** | Active users / provisioned users; frequency of dashboard access | Auth/session activity, tenant user counts (`app/models/tenant_membership.py`) |
| **Supervisor Agreement** | Fraction of AI recommendations a supervisor agrees with outright | `/api/knowledge-graph/learning-confidence`'s `knowledge_confidence`, or `/api/model-performance/ai-summary` |
| **AI Confidence** | Mean confidence score across scored inspections | `/api/cios/dashboard`'s `ai_confidence` |
| **Clinical Readiness** | Fraction of inspections in `READY_FOR_PACKAGING` state | `/api/pre-sterilization-command-center/clinical-inspection-readiness`, surfaced in `/api/cios/dashboard`'s `readiness_rate` |
| **Inspection Coverage** | Fraction of imaged inspections with complete/acceptable zone coverage | `/api/cios/dashboard`'s `coverage_rate` |
| **Customer Health Score** | Composite of adoption, engagement, agreement, and support-ticket signals | `docs/customer-success/customer-health-framework.md`, `app/models/customer_health_snapshot.py` |
| **ROI Achievement** | Realized value vs. the projected ROI at time of sale | `docs/enterprise/roi-framework.md`, tracked at each 90-day and quarterly review |
| **Support Metrics** | Ticket volume, time-to-first-response, time-to-resolution, by edition SLA | Support system integration (edition-level SLA commitments in `docs/enterprise/commercial-packaging.md`) |

## Reporting cadence

| Audience | Cadence | Vehicle |
|---|---|---|
| SPD Champion | Daily/weekly | Live dashboards (`/pre-sterilization-command-center`, `/pilot-validation`) |
| Executive Sponsor | Monthly | `/cios-dashboard`, quarterly review package |
| LumenAI Customer Success | Weekly (first 90 days), monthly thereafter | Internal customer health tracking |
| LumenAI Executive Leadership | Quarterly | Portfolio-level roll-up across all customers |

## Portfolio-level (cross-customer) metrics

Beyond a single customer's metrics, LumenAI leadership tracks the same
metrics aggregated across the customer portfolio to spot systemic issues
(e.g., a consistently low adoption rate across all Community Edition
customers might indicate an onboarding-flow problem, not a customer-
specific one) — see `docs/customer-success/customer-health-framework.md`
for the portfolio-level health-scoring methodology.

## Honesty constraint

Every metric here is computed from real tenant data via the API endpoints
cited — none is a manually-maintained spreadsheet figure disconnected
from the live system. If a number reported to a customer or in an
internal review doesn't match what the live dashboard shows, that's a
bug in the reporting process, not an acceptable discrepancy.
