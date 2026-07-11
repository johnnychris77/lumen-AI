# Project GuardianX — Trust Score

LumenAI Network v5.2, Section 9.

## Reuse map — three of five scores are not new engines

| Trust Score | Source |
|---|---|
| Knowledge Trust Score | `phoenix_platform_health_service.compute_knowledge_health_score` (Phoenix, v4.9) — reused directly |
| Workflow Trust Score | `phoenix_platform_health_service.compute_workflow_health_score` (Phoenix, v4.9) — reused directly |
| Digital Twin Trust Score | `phoenix_platform_health_service.compute_digital_twin_health_score` (Phoenix, v4.9) — reused directly |
| Model Trust Score | Genuinely new — composes an `AIModelRegistryEntry`'s validation status, certification status, governance status, and open high/critical risk count from the AI Risk Registry |
| Platform Trust Score | Genuinely new, assurance-specific composite — governance approval ratio across every registered model, averaged with Knowledge/Workflow/Digital Twin scores |

Platform Trust Score is deliberately **not** the same thing as Phoenix's
Platform Maturity Index (which measures platform *improvement* across 9
dimensions) or Phoenix's own Platform Health (operational health) — it
specifically weighs governance/certification/risk posture, the
assurance question this sprint exists to answer.

## "Display why each score was calculated"

Every computation is persisted as an `AIAssuranceTrustSnapshot` — one
generic table with a `scope` discriminator
(`platform`/`model`/`knowledge`/`workflow`/`digital_twin`) rather than
five separate tables, following the same pattern as
`NetworkGovernanceCase` (Olympus). The `components` breakdown is always
stored alongside the overall number, so "why" is never lost to a single
opaque figure.

A tenant or model with no real data yet scores `None` on a component,
never a default/optimistic number — the same honesty discipline Phoenix
established for its own health scores.

```
POST /api/guardianx/trust/models/{id}/compute
POST /api/guardianx/trust/knowledge/compute
POST /api/guardianx/trust/workflow/compute
POST /api/guardianx/trust/digital-twin/compute
POST /api/guardianx/trust/platform/compute
GET  /api/guardianx/trust/history?scope=...&scope_ref_id=...
```
