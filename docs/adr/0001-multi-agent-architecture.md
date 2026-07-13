# ADR-0001: Multi-Agent / Multi-Specialist Architecture

## Status
Accepted (retroactively documented — this pattern was already established and in use across ~25 specialists before this ADR was written).

## Context
LumenAI needed to add reasoning capabilities across many distinct domains (instrument reliability, education, evidence integrity, risk, discovery, governance execution, etc.) without every new capability becoming a monolithic addition to one growing service, and without each new capability re-deriving judgments other parts of the system had already computed.

## Decision
Each domain becomes an independent "specialist": one model file (with a documented naming-disambiguation section citing what it composes vs. duplicates), a group of `<specialist>_*` service files, one route file mounted at its own `/api/<specialist>` prefix, and (usually) one frontend workspace. Specialists compose each other's already-computed outputs by direct function call — there is no message bus or event system between them. Two "meta" specialists (Council, Maestro) exist specifically to read across every other specialist and synthesize a single leadership-facing view.

## Consequences
- **Positive**: strong reuse discipline — verified in this review, no specialist duplicates another's core reasoning; Forge's approval chain alone is reused directly by 5 other specialists.
- **Positive**: high navigability — a developer who has read one specialist's docstring can predict the shape of any other.
- **Negative**: Council and Maestro grow linearly with specialist count (already ~10-11 direct dependencies each) since composition is by direct import, not a registry — see Technical Debt Register TD (dependency map §3). A future specialist count significantly beyond 25 may need a registry-based fan-out instead.
- **Negative**: two capabilities (Vision, Anatomy) that are used by nearly every specialist never received their own specialist treatment, and one capability (Aegis) is treated as a specialist in vocabulary without having independent model/data ownership — see Technical Debt Register TD-03, TD-08.
