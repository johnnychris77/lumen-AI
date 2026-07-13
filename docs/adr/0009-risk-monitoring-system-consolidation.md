# ADR-0009: Risk/Monitoring System Consolidation (Proposed — needs a decision)

## Status
**Proposed.** Raised as Technical Debt Register TD-07.

## Context
Three risk/monitoring systems currently coexist: `simulation_engine.py` (v2.5, predictive scenario engine, historically also called "Project Sentinel"), `sentinel_orchestration.py` (v3.0, "Project Sentinel," continuous advisory monitoring), and `sentinelx_risk.py` (Project Sentinel-X, the current composite clinical-risk/patient-safety specialist). Sentinel-X was deliberately built with a distinct `sentinelx_` prefix and `/api/sentinelx` mount specifically to avoid colliding with the still-active older Sentinel system — a reactive naming fix, not a scope consolidation. Both `/sentinel` and `/risk` exist as separate, live frontend routes today.

## Decision needed
Whether these three systems should remain permanently separate (each serving a genuinely distinct purpose — scenario simulation vs. advisory monitoring vs. composite clinical risk) or whether two of them should be formally merged or one deprecated, now that Sentinel-X's composite scoring may have absorbed what the older Sentinel system was providing.

## Consequences
- **If kept separate**: at minimum, rename the user-facing surfaces so "Sentinel" (legacy) and "Sentinel-X" (current) are less confusable to end users than they are today, and document in this ADR set why each remains necessary.
- **If consolidated**: requires a migration plan for any UI/API consumers of the deprecated system(s), and an update to every specialist that currently reads from the system being retired.
- Either way, this decision should be made and recorded before any of the three systems receives significant new investment, per the architecture-freeze policy.
