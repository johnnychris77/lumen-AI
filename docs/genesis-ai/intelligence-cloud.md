# Project Genesis AI — Instrument Intelligence API & Clinical Intelligence Exchange

LumenAI Network v5.3, Sections 7 & 8.

## Instrument Intelligence API (Section 7) — extends Nexus's v1 gateway

Never a second versioned API surface. `nexus_api_gateway.py` (v3.2,
already extended by Infinity, v5.0) gains three new `/api/v1/*`
endpoints, using the exact same `require_gateway_auth` dependency and
`api_version: "v1"` response shape as every other v1 endpoint:

```
GET /api/v1/instrument-registry?instrument_family=...   -- instrument metadata, anatomy profile link, inspection zones, Digital Twin/baseline template refs, knowledge references
GET /api/v1/anatomy                                     -- the Global Anatomy Registry
GET /api/v1/evidence                                    -- the Clinical Evidence Cloud
```

Named `instrument-registry`, not `instruments` — the pre-existing
`/api/v1/instruments` (v3.2) already means something different (a
tenant's own inspected-instrument list, derived from `Inspection` rows).

"Model compatibility" is not a fabricated matching engine — it's the
`digital_twin_template_ref`/`knowledge_references` already returned per
instrument, which a caller can cross-reference against GuardianX's AI
Model Registry (`/api/guardianx/models`) themselves.

## Clinical Intelligence Exchange (Section 8) — zero new tables

Olympus's `HIXExchangePackage`/`olympus_exchange_service.py` (v5.1)
already packages knowledge/workflow/Digital-Twin/education content with
mandatory governance approval and full provenance
(`content_ref_type`/`content_ref_id`, `reviewed_by`/`reviewed_at`,
de-identified `source_tenant_id`). Genesis AI extended
`HIX_PACKAGE_TYPES` with one new value, `research_dataset`, so P20's
governance-gated research datasets can flow through the exact same
exchange pipeline — never a second exchange model.

```
POST /api/genesis-ai/intelligence-exchange/research-dataset-packages
GET  /api/genesis-ai/intelligence-exchange/summary
```

`submit_research_dataset_package` is a convenience wrapper over
Olympus's generic `submit_package` — the full governance-review →
publish lifecycle (`docs/olympus/intelligence-exchange.md`) applies
unchanged.
