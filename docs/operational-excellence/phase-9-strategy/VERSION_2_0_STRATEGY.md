# LPR-DIR-020 — Version 2.0 Strategy (Phase 9)

## Framing

V2.0 is the **enterprise-platform expansion** (integrations, interoperability, real AI,
partner ecosystem). It is **explicitly downstream of V1.1 hardening** (Phase 8
`VERSION_1_1_ROADMAP.md`) and of a controlled production launch. **This roadmap
authorizes no code, no launch, no feature development** — it is governed planning.
Constraint honored: no uncontrolled feature development; every initiative traces to a
real capability gap or evidence-based opportunity.

## Sequencing gate (non-negotiable)

```
V1.1 (hardening)        close 1 CRITICAL + 8 HIGH → controlled supervised pilot
        │                (SEC-C-01, secrets, load test, HA/workers, scheduler,
        │                 IR/alerting, deploy/rollback) + measurement instrumentation
        ▼
V2.0 (enterprise)       only after the gate closes and the pilot yields real data
```

## V2.0 initiative prioritization

Scored on customer value (CV), technical feasibility (TF), regulatory impact (RI),
operational maturity needed (OM), strategic alignment (SA). H/M/L.

| Initiative | CV | TF | RI | OM | SA | Priority |
|---|---|---|---|---|---|---|
| **Real trained CV model** (offline, governed pipeline) | H | M | **H** | H | H | P0 (after data exists) |
| **HL7 v2 interface** (SPD/OR integration) | H | M | M | M | H | P1 |
| **FHIR real support** (US Core + Inferno conformance) | H | L | **H** | M | H | P1 |
| **EHR connector certification** (Epic/Cerner validated) | H | L | H | M | H | P1 |
| **Enterprise analytics + product-analytics stream** | H | M | L | M | H | P1 |
| **Public/partner API program** (versioned, docs, limits) | M | M | L | M | M | P2 |
| **Licensing/entitlement + billing integrity** | M | M | L | M | H | P2 |
| **HA Postgres / horizontal scale** (SCAL-01 depth) | M | M | L | H | M | P2 |
| **UDI/GS1 instrument-identity mapping** | M | M | M | L | M | P3 |

## Regulatory posture (must be explicit in V2.0)

A real trained model applied to clinical inspection **raises the regulatory profile
materially** (potential SaMD considerations). V2.0 planning must include a
regulatory-pathway assessment **before** any model is exposed to clinical use. **No
FDA/clearance claim is made or implied here**; this is a flag that RI is High for the
AI and FHIR initiatives.

## Explicit non-goals for V2.0

- No enterprise expansion **before** the production gate closes.
- No trained-model **production/clinical** claims without offline validation + a
  regulatory-pathway decision.
- No architecture change that weakens tenant isolation, audit, or the human-review
  requirement.

## Determination

A **governed, prioritized V2.0 strategy exists**, strictly gated behind V1.1 hardening
and a controlled launch. It is evidence-based (each item maps to a real gap:
INT-01..04, IOP-01..05, AIM-01..03, COM-01..04) and introduces no uncontrolled
development. **Execution is deferred; the plan is ready.**
