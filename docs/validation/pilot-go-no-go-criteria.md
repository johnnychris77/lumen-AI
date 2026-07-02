# Pilot Go / No-Go Criteria (Phase 18)

Readiness gate for expanding the pilot. Source:
`app.services.ml.pilot_validation.go_no_go`. API: `/api/pilot-validation/go-no-go`.
Advisory — a human owns the final decision.

## GO — all must hold
- No unresolved critical safety issue.
- Safety-critical false-negative rate within threshold for blood / tissue /
  organic residue (and the other critical findings).
- Supervisor agreement above threshold.
- Documented limitations.

## NO-GO — any triggers a block
- Repeated missed critical findings (safety FNR over threshold).
- High overall false-negative rate.
- Poor image quality without mitigation.
- Unreliable zone assignment.

## Default thresholds

| Gate | Default |
|---|---|
| Max safety false-negative rate | 0.05 |
| Min supervisor agreement rate | 0.80 |
| Min reviewed inspections | 30 |

Insufficient data (fewer than the minimum reviews) is **NO-GO**, not an
optimistic pass — the gate refuses to certify readiness without evidence.

## Output

`decision` (GO / NO-GO), `blocking_issues` (human-readable), the `thresholds`
used, and the `measured` values — so the decision is transparent and auditable.
