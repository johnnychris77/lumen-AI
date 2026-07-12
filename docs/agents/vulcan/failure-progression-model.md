# Project Vulcan — Failure Progression Model

LumenAI AI Specialist, Section 3.

## Real history, never fabricated trends

`vulcan_progression_service.compute_progression` classifies condition
progression from real `InspectionFinding.severity_index` sequences (0 none /
1 minor / 2 moderate / 3 severe) for one instrument identity, optionally
scoped to one anatomy zone. Fewer than two matching findings always yields
`insufficient_history` — Vulcan does not predict a trend it has no evidence
for.

## Progression states

| State | Condition |
|---|---|
| `rapidly_worsening` | severity non-decreasing, net increase >= 2 |
| `slowly_worsening` | severity non-decreasing, net increase == 1 |
| `improving` | severity strictly decreasing |
| `unresolved` | severity flat at moderate/severe (>= 2), not improving |
| `stable` | severity flat at none/minor |
| `intermittent` | severity oscillates (neither monotonic) |
| `insufficient_history` | fewer than 2 matching findings |

## Example (matches the brief's illustrative progression)

```
Inspection 1: minor surface discoloration   (severity 1)
Inspection 2: surface rust                  (severity 1-2)
Inspection 3: moderate corrosion            (severity 2)
Inspection 4: pitting                       (severity 3)
Inspection 5: remove from service           (severity 3, disposition escalation)
```

This sequence classifies as `rapidly_worsening` (net severity change >= 2
across the window), which — combined with the reliability score's
progression penalty — drives the recommended disposition toward repair or
removal review.

## API

```
GET /api/vulcan/progression?instrument_identity=...&zone=...
```
