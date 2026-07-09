# First Pass Yield Intelligence

Codename: Project Guardian · LumenAI Quality v2.9

## Scoped honestly to what the data actually supports

`Inspection` has no reprocess-cycle/attempt-number lineage — there's no way
to know today whether a given inspection was a physical instrument's first
attempt or a re-inspection after rework. Rather than fabricate that
distinction, First Pass Yield here is scoped to what LumenAI can actually
back with real records:

```
Inspection Pass -> OR Quality Event -> Confirmed Finding ->
True First Pass Yield / False Pass Yield
```

- **True First Pass Yield** — the fraction of `PASS`-dispositioned
  inspections with no subsequently-confirmed OR quality event pointing
  back at them.
- **False Pass Yield** — the complement: a `PASS` that a confirmed,
  supervisor-verified OR event later showed had actually missed something.

"Confirmed" requires two things to both be true: the quality event itself
is `confirmed` (`quality_event_service.confirm_event`), and the
`EventCorrelation` linking it to that inspection is
`supervisor_confirmed` (`event_correlation_service.confirm_correlation`) —
an unconfirmed fuzzy correlation never counts as a miss.

## Scopes

`GET /api/quality-guardian/first-pass-yield?scope_type=...&scope_value=...`
computes for one of `department`, `instrument`, `technician`, `facility`.
`GET /api/quality-guardian/first-pass-yield/all-scopes` returns the overall
figure plus a full breakdown across all four scopes, for the Executive
Quality Dashboard's trend view. Every computation persists a
`FirstPassYieldSnapshot` row, so the trend is a real historical series, not
recomputed-on-read-only.
