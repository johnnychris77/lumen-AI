# LumenAI — Architecture Decision Record Index

Objective 14 deliverable. Individual ADRs live in `docs/adr/` (previously an empty scaffold — this review populates it for the first time). Two ADRs are marked **Proposed** rather than **Accepted** because this review surfaced a real open decision that needs a human call, not a retroactive description of an already-settled choice.

| ADR | Title | Status |
|---|---|---|
| [0001](../adr/0001-multi-agent-architecture.md) | Multi-Agent / Multi-Specialist Architecture | Accepted |
| [0002](../adr/0002-digital-twin-systems.md) | Digital Twin Systems | Accepted, consolidation flagged |
| [0003](../adr/0003-knowledge-graph.md) | Knowledge Graph as a Shared Reasoning Layer | Accepted |
| [0004](../adr/0004-council-decision-support.md) | Council as Pure Decision Support | Accepted |
| [0005](../adr/0005-evidence-governance.md) | Evidence Governance Ownership (Veritas) | Accepted |
| [0006](../adr/0006-baseline-hierarchy.md) | Baseline Hierarchy (Manufacturer/Vendor/Network) | Accepted |
| [0007](../adr/0007-tenant-isolation.md) | Tenant Isolation Model | Accepted, two open findings |
| [0008](../adr/0008-aegis-specialist-status.md) | Aegis's Specialist Status | **Proposed — needs a decision** |
| [0009](../adr/0009-risk-monitoring-system-consolidation.md) | Risk/Monitoring System Consolidation | **Proposed — needs a decision** |

## Going forward

Per the Architecture Freeze declared in [ARCHITECTURE_INVENTORY.md](./ARCHITECTURE_INVENTORY.md): any new agent, module, dashboard, API, or workflow requires a new ADR in `docs/adr/` before implementation, reviewed against this index and the [Technical Debt Register](./TECHNICAL_DEBT_REGISTER.md). Use the format established in ADR-0001 through 0009 (Status / Context / Decision / Consequences).
