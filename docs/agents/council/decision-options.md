# Project Council — Decision Options and Tradeoff Analysis

Section 7 of the sprint brief.

## Generation (`council_decision_options_service.generate_decision_options`)

One `CouncilDecisionOption` is generated per distinct recommended action
across the case's assessments -- every option traces back to the
specific specialist(s) who proposed it:

- `benefits` / `risks` -- pulled from the supporting specialists' own
  `significance` / `evidence_limitations` text, never invented.
- `clinical_risk` -- `"high"` if any supporting specialist flagged
  `urgency="urgent"`, else `"low"`.
- `operational_impact` -- names which specialist(s) proposed the option.
- `financial_impact` -- **always left blank.** No real, supportable
  financial-estimation source exists in this codebase for these options
  today, and the brief explicitly instructs "do not fabricate financial
  estimates."
- `evidence_strength` -- derived from the average confidence of the
  option's supporting specialists.
- `reversibility` -- `"irreversible"` if the option's title implies
  permanent removal/discard/retirement, otherwise `"reversible"`.
- `required_authority` -- the highest authority tier any supporting
  specialist flagged as necessary.
- `expected_time_to_resolution` -- a generic bucket (same day / several
  days / 1-2 weeks) inferred from the option's action text (e.g. a
  manufacturer evaluation implies external turnaround).

This mirrors the brief's worked example directly: "Reclean and repeat
inspection" (fast, doesn't resolve possible structural corrosion), "Hold
for repair evaluation" (addresses possible degradation, instrument
unavailable), "Manufacturer evaluation" (design-specific assessment,
longer turnaround/possible cost) -- each with its own real evidence trail
rather than a single flattened recommendation.
