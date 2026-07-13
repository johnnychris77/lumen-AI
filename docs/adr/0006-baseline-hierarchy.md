# ADR-0006: Baseline Hierarchy (Manufacturer / Vendor / Network)

## Status
Accepted.

## Context
Instrument condition baselines can come from multiple sources of decreasing authority: the manufacturer, a vendor's own submission, or a network-aggregated baseline contributed by peer facilities. The platform needed one consistent resolution order rather than each specialist picking a baseline source independently.

## Decision
`baseline_comparison_scoring_service.resolve_baseline` is the single resolution function for the real 3-tier baseline source hierarchy (manufacturer > vendor > network), backed by `BaselineLibraryEntry` (P15) with its own approval workflow. Veritas's `VeritasBaselineResolution`/`VeritasBaselineGovernanceAction` govern this resolution rather than re-implementing it — notably, Veritas's docstring is explicit that it folds its governance tiers onto the real 3-tier hierarchy rather than fabricating additional tiers that don't exist in the underlying data.

## Consequences
- **Positive**: one resolution order, one governance layer — no specialist has its own competing baseline-priority logic.
- **Positive**: the explicit refusal to fabricate extra tiers is a good instance of this codebase's general discipline of not overclaiming structure the data doesn't actually have.
