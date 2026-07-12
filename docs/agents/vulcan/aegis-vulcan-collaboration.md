# Project Vulcan — Integration With Aegis

LumenAI AI Specialist, Section 12.

## Aegis does not pre-exist in this codebase

A `grep -rn "aegis" app/` before writing any Vulcan code returned zero
matches. Rather than fabricate a full "process variation" platform to match
the brief's illustrative example (an "evening shift" pattern this codebase
has no shift data to support), `vulcan_aegis_integration_service.py` builds
a real, honestly minimal process-variation signal from the one relevant
real field this codebase actually has: `Inspection.technician` concentration
among the findings behind a Vulcan assessment.

## Signal

`compute_process_variation_signal` looks at the technicians attributed to
the relevant inspections. With fewer than two technician-attributed
inspections, it reports no signal (insufficient sample). Otherwise it
reports the most-concentrated technician's share; a concentration >= 60%
is flagged as a possible process-variation contributor — always described
in terms of what was actually measured, never dressed up as the brief's
"evening shift" example.

## Vulcan and Aegis never overwrite each other

- Vulcan's own reasoning lives in `reasoning_narrative`.
- Aegis's conclusion lives in a separate field, `aegis_conclusion_json`.
- `combine_conclusions` only ever *appends* a combined-conclusion sentence
  into `combined_conclusion` — it never mutates or replaces either side's
  own field.

This satisfies "no agent may overwrite the other's conclusion" and keeps
both agents' evidence separately traceable in the persisted assessment row.

## Example (Section 12 illustrative pattern, adapted to real data)

> Vulcan identifies recurring corrosion in orthopedic drill-bit flutes.
> Aegis's real signal shows one technician performed a concentrated share
> of the relevant inspections. Combined conclusion: instrument failures may
> involve both repeated process exposure and progressive material
> degradation — human review required to confirm either contributor.
