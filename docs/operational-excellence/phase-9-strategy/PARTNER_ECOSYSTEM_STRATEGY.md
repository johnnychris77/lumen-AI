# LPR-DIR-020 — Partner Ecosystem Strategy (Phase 9)

## Framing

Forward-looking partner strategy. **No partnerships, LOIs, or pilots exist** (platform
not launched), so this is a **strategy and prioritization**, not a status report. Every
opportunity is **gated** behind (a) closing the production-authorization gate and (b) a
guardrail review (clinical safety, tenant isolation, audit, PHI, anonymization). No
commitment is made and no partner is named as engaged.

## Opportunity map (candidate — evaluation only)

| Partner class | Rationale / codebase hook | Value | Readiness / gate |
|---|---|---|---|
| **Healthcare providers (IDNs / hospitals)** | The customer; TenantMembership multi-tenancy + facility/system scoping (Atlas) already model this | Highest — design partners for a supervised pilot | Gated on launch + SEC-C-01 + IR/observability |
| **Device / instrument manufacturers** | Baseline library (`BaselineLibraryEntry`) + Digital Twin per instrument; anonymized cross-hospital intelligence | High — authoritative baselines + reliability insight (Vulcan domain) | Gated on launch; requires baseline-contribution governance |
| **Sterile-processing vendors (tracking systems)** | `or_connect`, NEXUS connectors, event bus; HL7 v2 opportunity (IOP-04) | High near-term — SPD workflow interop | Gated on connector-certification harness (INT-04) + HL7 build |
| **Cloud partners** | Governed object storage (configurable backend), container/GHCR release | Medium — hosting/compliance (HIPAA BAA) | Gated on production infra decisions (SCAL-01, SEC-INF-01) |
| **Research organizations** | Dataset registry + governed export + de-identification posture | Medium — validation studies, dataset collaboration | Gated on IRB/data-governance + PHI-free guarantees |

## Ecosystem enablers that must exist first

1. **A governed public/partner API program** (IOP-01) — versioned contract, external
   docs, rate limits (Infinity scaffolding is a start, not a program).
2. **Connector certification/conformance harness** (INT-04) — so a partner integration
   can be validated before go-live.
3. **HL7 v2 / FHIR real support** (IOP-03/-04) — table stakes for SPD/EHR partners.
4. **Data-sharing governance** — anonymization + audit already exist; formal
   partner-data agreements do not.

## Guardrails (non-negotiable for every partnership)

No PHI leaves the tenant boundary un-governed; cross-hospital identities anonymized;
every sharing action audited; no causation/regulatory claims in partner-facing outputs;
tenant isolation never weakened by an integration.

## Determination

A **coherent, evidence-anchored partner strategy exists** with clear priority
(providers → device makers → SPD vendors → cloud → research) and concrete codebase
hooks. It is **strategy, not traction** — every opportunity is gated behind production
launch and the enabling API/interop/governance work. Recommended first move: recruit
**1–2 provider design partners** for a supervised pilot *after* the gate closes.
