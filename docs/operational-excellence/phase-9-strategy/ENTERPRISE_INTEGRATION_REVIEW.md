# LPR-DIR-020 — Enterprise Integration Review (Phase 9)

## Honest framing

The directive states the platform "is operating successfully in production." **It is
not** — Phase 6 = GO WITH CONDITIONS (production withheld), Phase 7 = NOT LAUNCHED,
**1 CRITICAL (SEC-C-01) + 8 HIGH** open. So there are **no live integrations, no
connected EHRs, no production sync traffic** to assess. What this review does is
inventory the **real integration scaffolding in the codebase** and state honestly
what is built vs. what is validated vs. what is running (nothing is running).

## Integration capability inventory (real — from code)

| Target | Code present | Maturity (honest) |
|---|---|---|
| **EHR (Epic / Cerner)** | `services/nexus_connectors/adapters.py` — `EpicAdapter` (SMART on FHIR), `CernerAdapter`; `models/nexus_integration.py` (`NexusConnector`, `NexusConnectorCredential`, `NexusIdentityMapping`, `NexusSyncRun`, `NexusSyncedAsset`) | **Scaffold.** Adapter docstring: OAuth2/EHR-launch flows are a "deployment-time concern (real client registration with a hospital's Epic instance)." **Not tested against a live EHR; no certification.** |
| **Sterile Processing / instrument tracking** | `or_connect` service/model; instrument (`digital_twin_id`/LCID) domain; `federated_horizon` cross-facility | Domain model real; **no live vendor integration** (Censis/SPM/etc. not connected) |
| **Identity providers** | OIDC/JWKS enterprise path (`auth/jwks_validator.py`, `jwt_validator.py`, explicit algorithm allowlist) + HS256 issuers | **Real and test-verified** — strongest integration surface; still carries SEC-H-01/02 secret-hardening blockers |
| **Enterprise analytics** | `insight_report_service`, `horizon_trend_detection_service`, `analytics` routes | Compute code real; **no live data + no product-analytics stream** (Phase 8 gap) |
| **Cloud storage** | governed object-storage service (Foundation Sprint) — configurable backend | Real, DR-drilled (RTO 10.4 s); production bucket/keys are deployment config |
| **Notification services** | multiple `*_notification_service.py` (steward/council/pulse/platform/workflow) | In-app notification model real; **no external email/SMS/pager transport wired** (ties OPS-INC-01) |
| **Event bus** | `nexus_event_bus_service`, `NexusEvent`, `NexusEventSubscription` | Real internal event-driven layer (see Interoperability) |

## Findings

- **INT-01 (HIGH) — EHR adapters are unvalidated scaffolds.** Epic/Cerner adapters
  exist as SMART-on-FHIR shells; **no live EHR handshake, token exchange, or resource
  read has been exercised.** Enterprise EHR integration cannot be claimed as a
  capability — only as a starting point.
- **INT-02 (HIGH, inherited SEC-C-01) — the one live external ingress fails open.**
  The webhook ingress (`routes/integrations.py`) fails open when the signing secret
  is unset and derives tenant from the attacker-controllable `X-Tenant-Id` header.
  **Any enterprise inbound integration must not go live until this is fixed.**
- **INT-03 (MEDIUM) — no external notification transport.** Notifications are
  in-app only; enterprise on-call/paging (ties Phase 5 OPS-INC-01) is unbuilt.
- **INT-04 (MEDIUM) — no connector certification/conformance harness.** There is no
  test suite that validates a connector against a reference EHR/FHIR sandbox.

## Assessment

Enterprise integration is **architected, not operational.** The NEXUS connector
framework (adapters + credentials + identity mapping + sync runs + event bus) is a
**genuine, well-structured foundation**, and identity-provider integration is real
and tested. But **no integration is validated against a real external system**, and
the sole live external ingress carries a release-blocking CRITICAL. Enterprise
integration is a **V2.0 build-and-certify program**, gated behind production launch.
