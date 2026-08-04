# ROI / Operational Estimator — Assumptions

The `/roi` estimator is **illustrative only** — not a forecast, benchmark, or
financial ROI, and it makes **no cost-savings, labor-savings, accuracy, or outcome
guarantees**.

## Inputs
Sites, inspections/month, instruments, SPD staff.

## Fixed illustrative assumptions (in `commercial.tsx`)
- Governed records/month = inspections/month (one record per inspection).
- Review-routed = **18%** of inspections (illustrative assumed review rate).
- Documentation minutes = **1.5 min/record** (illustrative capture→record time).
- Records/technician = inspections ÷ staff.

## Why no dollars
We deliberately do **not** output financial ROI or savings figures — those depend
on each site's costs and would be unsupported claims. Outputs are operational
shape only. Any real figures must come from a pilot in the customer's environment.
