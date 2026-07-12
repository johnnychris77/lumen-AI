# Project Veritas — Baseline Resolution Hierarchy

LumenAI AI Specialist, Section 2.

## Built on the real resolution engine

`veritas_baseline_resolution_service.resolve_governed_baseline` calls
`baseline_comparison_scoring_service.resolve_baseline` directly (which
already implements manufacturer -> vendor -> hospital priority across both
real baseline sources) and enriches the result with manufacturer/model/
reviewer/image-count fields fetched from whichever real table matched.

Since `resolve_baseline` doesn't expose *which* table (`BaselineLibraryEntry`
vs. `EnterpriseVendorBaselineSubscription`) produced a hit, Veritas calls the
same two private resolution helpers (`_resolve_from_library`,
`_resolve_from_uploaded`) directly to track that distinction honestly.

## Five-tier hierarchy, mapped onto three real tiers

The brief names five priority tiers (manufacturer / manufacturer-authorized
/ vendor / organization / instrument-specific historical). This codebase's
real baseline sources only distinguish three (manufacturer / vendor /
hospital) — "manufacturer-authorized" and "instrument-specific historical"
are not separately tracked anywhere and are honestly folded into the
nearest real tier rather than fabricated as if a five-tier system existed.

## Never a silent substitution

`resolve_baseline` already only returns *approved* entries. When nothing
approved is found, Veritas returns `resolution_status =
SUPERVISOR_REVIEW_REQUIRED` with the brief's exact message:

> "No approved baseline is available for this instrument and anatomy zone.
> A final baseline-dependent score cannot be issued."

## Anatomy zone is carried through, not filtered on

Neither real baseline table tracks anatomy zone. `anatomy_zone` on
`VeritasBaselineResolution` is the caller's requested zone, kept for
display/audit only — never used as a fabricated filter the underlying
tables can't actually support.

## API

```
POST /api/veritas/assess/{inspection_id}
```

(Baseline resolution runs as the first step of the full evidence
assessment; see `veritas-evidence-agent.md`.)
