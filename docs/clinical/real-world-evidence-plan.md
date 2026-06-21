# Real-World Evidence Collection Plan

## 1. Purpose
Collect post-market surveillance data from live hospital deployments to:
- Demonstrate real-world performance (accuracy, sensitivity, specificity)
- Detect performance drift early
- Support 510(k) annual report and post-market surveillance (PMS) obligations

## 2. Data Collection Strategy
### Passive Collection (automated)
- Every AI finding is logged in CVInferenceRecord with tenant_id, facility_id, instrument_name
- Technician accept/override decision logged (override_reason captured)
- Weekly aggregate: finding rates, override rates, confidence distributions

### Active Collection (opt-in)
- Facilities enroll in RWE program via IntelligenceSharingConsent (P6)
- Consenting facilities: technician confirmation outcome (pass/fail) linked to AI finding
- De-identified before cross-site aggregation

## 3. RWE Metrics
| Metric | Calculation | Alert Threshold |
|--------|-------------|-----------------|
| Override rate | overrides / total findings | > 15% (possible FP spike) |
| Escalation rate | escalations / sessions | > 5% (possible sensitivity issue) |
| Cycle time drift | avg inspection time vs. baseline | > 20% increase |
| Finding distribution shift | PSI on finding_category distribution | PSI > 0.2 |

## 4. Minimum Sample for RWE Report
- 3 hospital sites minimum
- 1,000 instrument inspections per site
- 6 months continuous operation
- Inspections covering all 12 finding categories

## 5. Reporting
- Monthly: automated RWE dashboard (P10 Digital Twin integration)
- Quarterly: formal RWE report submitted to CVC
- Annual: FDA annual report if cleared under 510(k)
