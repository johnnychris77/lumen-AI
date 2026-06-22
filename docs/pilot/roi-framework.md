# LumenAI Pilot ROI Framework

> **Disclaimer:** All figures in this document are estimates based on published industry benchmarks (AORN, AAMI, IAHCSMM). They must be validated against actual site financial and operational data before use in financial reporting. LumenAI makes no warranty regarding financial outcomes.

## Overview

The ROI framework estimates the economic value delivered by the LumenAI pilot across three value categories: labor savings, reprocessing avoidance, and surgical cancellation avoidance. HAI risk reduction is flagged as an indicative signal but is not monetised.

## Value Categories

### 1. Labor Savings
- **Basis:** Estimated 4.5 minutes of manual paper documentation saved per inspection
- **Rate:** $35/hour (average SPD technician hourly rate, per IAHCSMM 2023 salary survey)
- **Formula:** `(total_inspections × 4.5 min / 60) × $35`

### 2. Reprocessing Avoidance
- **Basis:** Contamination events caught before surgical use
- **Conservative assumption:** 60% of detected contamination events would have required reprocessing if missed
- **Cost per event:** $85 (AAMI ST79 / internal benchmark)
- **Formula:** `int(contamination_events × 0.60) × $85`

### 3. Surgical Cancellation Avoidance
- **Basis:** Very conservative estimate (0.5% of contamination events avoided a cancellation)
- **Cost per cancellation:** $12,000 (published range: $8,000–$20,000 per AORN)
- **Formula:** `max(1, int(contamination_events × 0.005)) × $12,000` (only if contamination > 0)

### 4. HAI Risk Reduction (Indicative, Not Monetised)
- Undetected instrument contamination is a potential contributing factor in surgical site infections
- Rate reference: ~2% of SSIs may have instrument hygiene as a contributing factor (AORN literature)
- This figure is an **indicative estimate only** and requires clinical validation

## API Endpoint

```
GET /api/pilot-analytics/roi?days=90
```

Returns: inputs, value estimates per category, total estimated value, annualised projection, disclaimers.

## Important Limitations

- Estimates are pilot-period projections based on inspection volume, not measured outcomes
- Reprocessing and cancellation savings are probabilistic, not observed
- Site-specific labour rates, reprocessing costs, and case complexity vary significantly
- All ROI claims must be reviewed by finance and clinical operations leadership before external reporting
- LumenAI does not claim FDA clearance for diagnostic or financial outcome prediction
