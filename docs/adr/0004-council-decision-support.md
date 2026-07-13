# ADR-0004: Council as Pure Decision Support (No Independent Analysis)

## Status
Accepted.

## Context
Leadership needed a way to see a synthesized, cross-specialist view of a decision — but any synthesis layer that ran its own independent analysis would risk contradicting, or worse, silently overriding a specialist's own real judgment (e.g. Council reaching a different reliability conclusion than Vulcan itself).

## Decision
Council performs **no independent analysis of its own** — every conclusion in a `CouncilCase` is sourced from a named specialist's real service call (Veritas, Aegis, Vulcan, Sage, Sentinel-X, Apollo, Athena, Pulse, Phoenix, Maestro, Research Agent), preserved with attribution, including dissent between specialists when it exists (`CouncilDissentRecord`). The human decision (`CouncilHumanDecision`) is the only place a real decision gets made; Council's job ends at presenting the specialists' assessments faithfully.

## Consequences
- **Positive**: verified during this review — Council never overwrites or re-derives a specialist's conclusion, and dissent between specialists is preserved rather than silently resolved.
- **Positive**: clear single responsibility, confirmed against the brief's "Decision Support. Only." requirement.
- **Negative**: Council depends directly on 11 other specialists' service functions with no abstraction layer between them — see ADR-0001's consequences and Technical Debt Register (dependency map §3) for the coupling-growth risk this creates.
