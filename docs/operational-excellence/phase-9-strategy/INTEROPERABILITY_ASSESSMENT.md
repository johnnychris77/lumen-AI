# LPR-DIR-020 — Interoperability Assessment (Phase 9)

## Basis

Code-grounded assessment of interoperability primitives at `origin/main`. No live
external interoperability exists (not launched); this evaluates **what is built and
what standards work remains.**

## REST APIs

- **Real and substantial.** FastAPI app with ~1,912 endpoints; OpenAPI schema
  auto-generated; OIDC/JWKS-secured; 1,593 `require_*` authorization guards;
  tenant-scoped. This is the **strongest interoperability asset** — a documented,
  authenticated HTTP surface.
- **Gap (IOP-01, MEDIUM):** no published, versioned **partner API contract** (public
  API versioning policy, rate limits, external developer docs). Infinity
  developer-platform scaffolding (`infinity_platform`) exists but is not a governed
  public API program.

## Event-driven architecture

- **Real.** `nexus_event_bus_service` + `NexusEvent` / `NexusEventSubscription`
  provide an internal publish/subscribe layer with typed event kinds; Forge execution
  publishes events. This is a legitimate foundation for event-driven interop.
- **Gap (IOP-02, MEDIUM):** the bus is **in-process/internal**; there is no external
  streaming/webhook-out delivery with ret[ry]/DLQ semantics for partners, and inbound
  webhooks carry SEC-C-01.

## FHIR readiness

- **Scaffold only.** SMART-on-FHIR **Epic/Cerner adapters** exist (`nexus_connectors/
  adapters.py`) but there is **no FHIR resource model mapping, no FHIR server/client
  conformance, no validation against a FHIR sandbox (e.g. HAPI/Inferno).**
- **IOP-03 (HIGH):** FHIR is **aspirational, not implemented.** Claiming "FHIR
  readiness" beyond "adapter shells + OAuth intent" would overstate. Real FHIR support
  (resource mapping, US Core profiles, Inferno conformance) is a V2.0 workstream.

## HL7 opportunities

- **Not implemented.** No HL7 v2 (MLLP/ADT/ORM) parsing or generation in the codebase.
- **IOP-04 (opportunity):** HL7 v2 is still the dominant real-world SPD/OR integration
  transport; a v2 interface engine (or a broker like Mirth) is a concrete V2.0
  integration opportunity, higher near-term ROI than FHIR for sterile-processing
  workflows.

## Standards alignment

- Security/engineering standards were assessed in Phase 3 (ASVS/SSDF/SBOM). **Clinical
  interoperability standards (FHIR US Core, IHE, HL7 v2, GS1/UDI for instruments)** are
  **not yet mapped.** UDI/GS1 alignment for instrument identity is a natural fit with
  the existing `digital_twin_id`/LCID model (IOP-05, opportunity).

## Import/export capabilities

- **Real.** Dataset export framework (classification/object-detection/segmentation/
  multi-label) + evidence/report export exist and are test-verified. This is a genuine
  interoperability strength for **data portability** (governed, auditable export).

## Roll-up

| ID | Sev | Finding |
|---|---|---|
| IOP-03 | HIGH | FHIR is scaffold-only — no resource mapping/conformance |
| IOP-01 | MEDIUM | No governed public/partner API contract + versioning |
| IOP-02 | MEDIUM | Event bus internal-only; no external delivery semantics; inbound = SEC-C-01 |
| IOP-04 | OPP | HL7 v2 unimplemented — high near-term SPD/OR ROI |
| IOP-05 | OPP | No UDI/GS1 instrument-identity standard mapping |

**Positive:** REST+OpenAPI, an internal event bus, and governed import/export are real,
substantial interoperability foundations. **FHIR/HL7 standards work is the main gap**
and is a defined V2.0 program — not a current capability.
