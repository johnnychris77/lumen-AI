# Project Genesis AI — Clinical Evidence Cloud & Manufacturer Knowledge Portal

LumenAI Network v5.3, Sections 3 & 4.

## Clinical Evidence Cloud (Section 3) — zero new tables

Horizon's `ClinicalEvidenceReference`/`RecommendationEvidenceLink`
(`federated_horizon.py`, v3.4) already cover every category Section 3
names — peer-reviewed literature, manufacturer guidance (IFUs), AAMI,
AORN, organization-approved SOPs, internal validation studies — via
`EVIDENCE_TYPES`, and already link evidence directly to any
recommendation-producing row via
`horizon_evidence_service.link_evidence_to_recommendation`. All CRUD
stays at the existing `/api/horizon/evidence*` endpoints; Genesis AI
only adds a coverage summary:

```
GET /api/genesis-ai/evidence-cloud/summary
```

The Instrument Intelligence API also exposes evidence at
`GET /api/v1/evidence` (see `docs/genesis-ai/intelligence-cloud.md`).

## Manufacturer Knowledge Portal (Section 4) — genuinely new

Beacon's `beacon_manufacturer_portal_service.py` (v3.5) is read-only
analytics *for* a manufacturer to view its own instrument population's
quality trends — nothing lets a manufacturer *publish* content.
`ManufacturerKnowledgeUpdate` is the write side: updated IFUs,
inspection guidance, cleaning updates, repair advisories, and design
revisions, each version-controlled (`supersedes_id` forms a real chain,
the same pattern as `QualityPolicy`/`StandardsPublication`) and
reviewable — `status` can only reach `published` through an explicit
`review_update` call, never automatically.

```
POST /api/genesis-ai/manufacturer-updates
POST /api/genesis-ai/manufacturer-updates/{id}/review
GET  /api/genesis-ai/manufacturer-updates/{id}
GET  /api/genesis-ai/manufacturer-updates/{id}/version-chain
GET  /api/genesis-ai/manufacturer-updates?manufacturer_tenant_id=...&update_type=...&status=...
```
