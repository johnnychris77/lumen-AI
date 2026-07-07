# Intelligent Prioritization Engine

`app/services/prioritization_engine.py` — `compute_priority()`

## What it is

A point-based, auditable ranking of inspection urgency — mirroring the same
rubric style already used by `risk_stratification_service.stratify_risk()`
(v1.6). Every point awarded comes with a plain-English reason, so the
ranking a supervisor sees is never a black box.

## Scoring rubric

| Factor | Points | Real signal used |
|---|---|---|
| Emergency procedure | +4 | `Inspection.procedure_priority == "emergency"` |
| Trauma procedure | +3 | `Inspection.procedure_priority == "trauma"` |
| First case | +2 | `Inspection.procedure_priority == "first_case"` |
| Supervisor escalation | +3 | Latest `DispositionOverride.action == "escalate"` |
| Critical finding | +3 | `readiness["is_critical_finding"]` (v1.6) |
| High-risk anatomy | +2 | Instrument family resolves to a high/critical-risk zone (`instrument_anatomy.py`) |
| Prior repair/removal history | +2 | `readiness["repair_history"]` (v1.6) |
| Repair return awaiting evaluation | +2 | Disposition is Repair/Manufacturer Evaluation |
| Repeat findings | +1 | A prior `InspectionFinding` row exists for the same physical instrument |
| Vendor tray | +1 | `vendor_name` is real and `tray_id` is set |
| Loaner instrument | +1 | `Inspection.is_loaner_instrument` |

## Tiers

| Score | Tier |
|---|---|
| ≥ 8 | Critical |
| 5–7 | High |
| 2–4 | Medium |
| 0–1 | Low |

## Honesty notes

- A factor with no real signal contributes zero points — there is no
  fabricated "default urgency."
- `reasons` always lists exactly which factors fired, so the score is
  explainable to a supervisor questioning why one inspection outranked
  another.
- Repeat-findings detection only fires for instruments with a real tracked
  identity (barcode/UDI) — an `untracked:` instrument can never honestly
  claim a repeat-condition history.
