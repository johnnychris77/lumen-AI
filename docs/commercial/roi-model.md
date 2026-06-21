# LumenAI ROI Model
Version 1.0 | Commercial — CONFIDENTIAL

## Overview
This model quantifies the financial return from LumenAI deployment.
Values are illustrative ranges based on industry benchmarks and pilot data.
Customer-specific ROI should be calculated using the CFO executive dashboard.

## Input Variables (Customize Per Customer)
| Variable | Community Hospital | Regional Medical Center | Academic Medical Center |
|----------|-------------------|------------------------|------------------------|
| SPD FTEs | 8 | 20 | 45 |
| SPD FTE loaded cost/hr | $28 | $32 | $38 |
| Inspections/month | 1,500 | 5,000 | 15,000 |
| Minutes/inspection (pre-LumenAI) | 4.5 | 4.5 | 4.5 |
| Instrument replacement/year | $45,000 | $120,000 | $350,000 |
| SSI rate (baseline) | 0.8% | 0.8% | 0.8% |
| Cost per SSI | $25,000 | $25,000 | $25,000 |
| Annual audit prep hours | 80 | 200 | 500 |
| Audit staff rate/hr | $45 | $55 | $65 |

## Value Driver 1: Labor Savings (Inspection Efficiency)
**Assumption**: LumenAI reduces average inspection time by 20%
(AI pre-triage prioritizes high-risk instruments; clean instruments processed faster)

| Segment | Monthly inspections | Time saved/inspection | FTE rate | Monthly savings | Annual savings |
|---------|--------------------|-----------------------|----------|-----------------|----------------|
| Community | 1,500 | 0.9 min | $28/hr | $630 | $7,560 |
| Regional | 5,000 | 0.9 min | $32/hr | $2,400 | $28,800 |
| Academic | 15,000 | 0.9 min | $38/hr | $8,550 | $102,600 |

## Value Driver 2: Instrument Replacement Savings
**Assumption**: AI detects 15% more instruments requiring repair before they
progress to costly emergency replacement (catching cracks, corrosion early)

| Segment | Instrument spend/yr | Savings (15% catch rate) |
|---------|--------------------|-----------------------|
| Community | $45,000 | $6,750 |
| Regional | $120,000 | $18,000 |
| Academic | $350,000 | $52,500 |

## Value Driver 3: Contamination Event Reduction
**Assumption**: 10% reduction in instruments released with undetected contamination,
conservative 5% reduction in instrument-attributable SSI events

| Segment | Annual SSIs (attributable) | Reduction (5%) | Cost per SSI | Annual savings |
|---------|--------------------------|----------------|-------------|----------------|
| Community | 4 events | 0.2 events | $25,000 | $5,000 |
| Regional | 12 events | 0.6 events | $25,000 | $15,000 |
| Academic | 35 events | 1.75 events | $25,000 | $43,750 |

## Value Driver 4: Audit Preparation Savings
**Assumption**: LumenAI generates audit packages in minutes vs. hours of manual preparation

| Segment | Annual prep hours | Reduction (60%) | Rate | Annual savings |
|---------|------------------|-----------------|------|----------------|
| Community | 80 hrs | 48 hrs | $45/hr | $2,160 |
| Regional | 200 hrs | 120 hrs | $55/hr | $6,600 |
| Academic | 500 hrs | 300 hrs | $65/hr | $19,500 |

## 3-Year ROI Summary

### Community Hospital (Starter)
| Year | Cost (LumenAI) | Benefits | Net | ROI Multiple |
|------|---------------|----------|-----|-------------|
| 1 | $30,000 | $21,470 | -$8,530 | 0.72x |
| 2 | $30,000 | $25,764 | -$4,236 | 0.86x |
| 3 | $30,000 | $30,000 | $0 | 1.00x |
| **3-Year** | **$90,000** | **$77,234** | **-$12,766** | **0.86x** |

*Note: Community hospital ROI improves significantly with contamination event avoidance.
The avoided SSI value ($25,000/event) is not included in base labor calculation above.*

### Regional Medical Center (Professional)
| Year | Cost (LumenAI) | Benefits | Net | ROI Multiple |
|------|---------------|----------|-----|-------------|
| 1 | $78,000 | $68,400 | -$9,600 | 0.88x |
| 2 | $78,000 | $82,080 | +$4,080 | 1.05x |
| 3 | $78,000 | $90,288 | +$12,288 | 1.16x |
| **3-Year** | **$234,000** | **$240,768** | **+$6,768** | **1.03x** |

### Academic Medical Center (Enterprise)
| Year | Cost (LumenAI) | Benefits | Net | ROI Multiple |
|------|---------------|----------|-----|-------------|
| 1 | $180,000 | $217,850 | +$37,850 | 1.21x |
| 2 | $180,000 | $261,420 | +$81,420 | 1.45x |
| 3 | $180,000 | $287,562 | +$107,562 | 1.60x |
| **3-Year** | **$540,000** | **$766,832** | **+$226,832** | **1.42x** |

## Intangible Value (Not Quantified Above)
- Accreditation readiness and reduced survey deficiencies
- CAPA reduction and compliance posture improvement
- Reduced clinician trust risk from instrument failures
- Benchmark data for negotiating vendor contracts
- Clinical evidence contribution (RWE program)
- Staff retention through reduced manual inspection burden

## Using the CFO Executive Dashboard
The `/api/executive/dashboard/cfo` endpoint returns live ROI metrics for the
current tenant, including labor_savings_usd, instrument_replacement_savings_usd,
audit_prep_savings_usd, repair_avoidance_savings_usd, total_roi_usd, and roi_multiple.
Use these figures in customer-facing ROI reports and QBR presentations.
