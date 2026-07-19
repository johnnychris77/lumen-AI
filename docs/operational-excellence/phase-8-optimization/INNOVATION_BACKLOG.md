# LPR-DIR-019 — Innovation Backlog (Phase 8)

## Framing and guardrails

This is a **forward-looking, deliberately un-scheduled** idea backlog — **not** a
commitment and **not** authorized for development. Per the directive, "no
uncontrolled feature development; all enhancements must be evidence-based." Every
item here is therefore **gated behind V1.1 hardening** (the production
authorization gate must close first) and behind the **non-negotiable clinical
guardrails** (no causation claims, mandatory human review, no PHI, no
FDA/regulatory-clearance claims, anonymized cross-hospital identities, audited
sharing). Items are **candidates for evaluation**, ranked by evidence strength and
guardrail-fit, not a promise to build.

## Backlog (candidate ideas — evaluation only)

| ID | Idea | Rationale / evidence hook | Guardrail notes | Readiness |
|---|---|---|---|---|
| INN-01 | **Real trained CV candidate model** through the governed pipeline | Placeholder is honestly labeled "not a trained model"; registry/eval/human-review scaffolding already exists | Human review mandatory; offline eval before any exposure; no causation claims | Blocked on V1.1 + frozen PHI-free datasets (AR-17) |
| INN-02 | **Product-analytics + insights dashboards** (tenant-scoped, PHI-free) | Closes the Phase-8 measurement gap so *future* optimization is data-driven | No PHI; tenant isolation enforced | Blocked on V1.1 Theme 5 |
| INN-03 | **SLO/error-budget dashboards + auto-alerting** | Builds on OPS-OBS metrics once histograms exist | N/A | Blocked on OPS-OBS-01/-02 |
| INN-04 | **Cross-hospital benchmarking insights** (anonymized) | Platform already anonymizes cross-hospital intelligence | **Must** stay anonymized + audited + "potential association" framing | Blocked on V1.1 + governance review |
| INN-05 | **Distributed tracing–driven performance insights** | Localizes slow API→DB→storage requests | N/A | Blocked on OPS-OBS-03 |
| INN-06 | **Read-replica / HA Postgres** to remove the SPOF | Directly addresses SCAL-01 | N/A | Blocked on V1.1 Theme 3 |
| INN-07 | **Self-service tenant onboarding** | Enablement docs exist; would reduce onboarding friction *if/when* customers exist | Tenant isolation + audit on every step | Blocked on launch |
| INN-08 | **In-product feedback + feature-voting** | Turns future pilot signal into a prioritized backlog | No PHI in feedback payloads | Blocked on CFB-01 |

## How items graduate

An idea leaves this backlog only when **all** of: (a) the production gate is
closed (Theme 1), (b) it has an **evidence-based** business/quality rationale, (c)
it passes a **guardrail review** (clinical-safety + tenant-isolation + audit +
privacy), and (d) a human authorizes a scoped engineering directive for it. Until
then it stays a candidate.

## Explicitly out of scope

- Anything asserting **clinical efficacy, causation, or regulatory clearance.**
- Anything requiring **PHI** in analytics, feedback, training, or benchmarking.
- Anything that **weakens tenant isolation, auth, or the audit trail.**
- Any feature that **presumes production is live** — it is not.

## Determination

A healthy, **evidence-anchored innovation backlog exists**, fully gated behind
V1.1 hardening and the clinical guardrails. It represents **controlled** future
direction, not uncontrolled feature development, and commits the platform to
nothing until authorized.
