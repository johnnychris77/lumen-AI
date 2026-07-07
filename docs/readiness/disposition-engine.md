# Instrument Disposition Engine (v1.6)

## What it does
`app/services/disposition_engine.py::recommend_disposition()` maps a
readiness classification onto one of seven standardized, action-oriented
outcomes — every disposition carries a required, non-generic explanation
grounded in the actual finding, coverage, and repair-history data.

## Allowed outcomes
- **Proceed to Packaging** — no actionable findings, supervisor-confirmed.
- **Reclean** — residual contamination detected.
- **Repeat Inspection** — coverage was too incomplete (< 50%) to trust any
  disposition; requested regardless of what else was found.
- **Supervisor Review Required** — nothing scored/reviewed yet, or an
  unrecognized readiness status (a safe fallback, never a silent pass).
- **Repair Evaluation** — a repairable structural finding (crack, corrosion,
  insulation damage) without a prior repair-history pattern.
- **Manufacturer Evaluation** — a repairable condition finding recurring on
  an instrument with prior remove-from-service history — routed to
  manufacturer-attributable evaluation instead of a one-off repair.
- **Remove From Service** — an escalated, non-repairable finding.

## Why coverage is checked first
An instrument with insufficient anatomy coverage can't honestly support *any*
of the other six dispositions — the AI hasn't actually seen enough of the
instrument to say. Repeat Inspection is checked before every other rule.

## Every disposition requires an explanation
`recommend_disposition()` always returns both `disposition` and
`explanation` — there is no code path that returns a disposition without a
grounded rationale, including the defensive fallback for an unrecognized
status.
