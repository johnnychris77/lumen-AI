# ADR-0002: Digital Twin Systems

## Status
Accepted, with a flagged consolidation candidate.

## Context
Three separate needs arose at different points in the platform's history: simulating SPD workflow-station/instrument flow (P10), forecasting overall quality state with what-if intervention modeling (P22), and tracking a governance-health composite score over time per department (Apollo). Each was built as its own "digital twin" rather than one twin extended three times.

## Decision
Keep three independently-scoped twin systems — `digital_twin.py` (workflow/flow simulation), `digital_quality_twin.py` (quality forecasting), and Apollo's `QualityTwinSnapshot` (governance health) — each documented as deliberately distinct in scope rather than a naming collision. Oracle's Digital Twin Research composes the latter two by reading their already-computed output (`twin_history`, `compute_progression`) rather than re-deriving twin state a fourth time.

## Consequences
- **Positive**: each twin stays scoped to what it actually models; no single twin became an overloaded catch-all.
- **Negative**: three systems sharing the phrase "digital twin" is a real source of confusion for anyone new to the codebase, and for end users navigating twin-related dashboards.
- **Follow-up**: Technical Debt Register TD-07 flags this as a consolidation candidate for a future decision — not urgent, since the three systems don't functionally overlap, but worth a naming/UX pass.
