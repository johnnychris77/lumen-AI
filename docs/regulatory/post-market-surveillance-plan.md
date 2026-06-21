# Post-Market Surveillance Plan
LumenAI | Version 1.0 | Post-Clearance Operationalization
**Subject to regulatory counsel review.**

## 1. Regulatory Basis
- FDA 21 CFR Part 820 (Quality System Regulation)
- FDA 21 CFR Part 803 (Medical Device Reporting — MDR)
- EU MDR Article 83–86 (if EU deployment planned)
- ISO 13485 Section 8.2.1 (Post-Market Surveillance)

## 2. Surveillance System Architecture
LumenAI's post-market surveillance is operationalized via existing platform capabilities:

| Signal | Source | Cadence | Alert Threshold |
|--------|--------|---------|----------------|
| Override rate | CVInferenceRecord + audit log | Weekly (RWE scheduler) | > 15% |
| Escalation rate | EscalationEvent table | Weekly | > 5% |
| Kappa monitoring | `/api/validation/kappa-monitor` | Monthly | < 0.80 |
| PSI drift | RWEMetricSnapshot.psi_score | Weekly | > 0.20 |
| Critical FN rate | Validation report | Monthly | > 2% |
| System uptime | /health + /ready probes | Continuous | < 99.9% |
| Error rate | Structured JSON logs | Continuous | > 0.1% |

## 3. Complaint Handling
- In-app: "Report an Issue" button → logged as SupportTicket (implementation pending)
- Email: support@lumenai.com → routed to Regulatory Affairs within 24h
- Clinical safety complaints: Immediate escalation to Medical Affairs
- Potential MDR events: Regulatory Affairs assessment within 5 business days

## 4. MDR Reportable Events (21 CFR Part 803)
LumenAI must file an MDR if the device:
- May have caused or contributed to serious injury or death
- Has malfunctioned in a way that would likely cause/contribute to serious injury if it recurred

**LumenAI-specific examples**:
- AI system recommended "pass" for an instrument that was later found infected (SSI link)
- System failure during active inspection that resulted in uninspected instrument release
- Cross-tenant data breach affecting patient safety

**Filing timeline**: 30 calendar days from awareness (5 days if death or serious injury)

## 5. Annual Post-Market Report
Required 12 months after clearance and annually thereafter. Content:
1. Units distributed and active facilities
2. Summary of complaints received
3. Summary of MDR reports filed
4. Current performance metrics (kappa, FN rate, override rate) vs. cleared baseline
5. Any software updates made under PCCP (Type 1 and Type 2)
6. Drift monitoring summary (PSI, CSI trends)
7. Changes to risk management file
8. Planned changes in next 12 months

## 6. Performance Trending Dashboard
Implemented via P12 RWE module + P10 Digital Twin:
- `GET /api/validation/rwe/metrics` → weekly override/escalation/PSI trends
- `GET /api/validation/kappa-monitor` → current kappa status
- `GET /api/validation/report` → full confusion matrix and FN rates
- `GET /api/digital-twin/dashboard` → throughput and workflow KPIs

## 7. Revalidation Triggers
Any of the following triggers a formal revalidation assessment:
- Kappa falls below 0.75 (retraining threshold in PCCP)
- Critical FN rate exceeds 2%
- PSI > 0.20 for 3 consecutive weeks
- ≥ 3 MDR-reportable events in 12 months
- Major update to underlying CV model (Type 3 PCCP change)

## 8. Key Roles
| Role | Responsibility |
|------|---------------|
| Regulatory Affairs Lead | PCCP monitoring, MDR assessment, annual report |
| Clinical Validation Committee | Kappa/FN review, revalidation decisions |
| Data Science Lead | Drift monitoring, retraining recommendation |
| VP Engineering | Deployment authorization |
| CISO | Cybersecurity incident assessment |
