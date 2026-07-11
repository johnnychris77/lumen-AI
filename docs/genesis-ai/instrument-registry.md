# Project Genesis AI — Global Instrument Registry & Global Anatomy Registry

LumenAI Network v5.3, Sections 1 & 2.

**"Project Genesis AI" is not "Project Genesis" (v4.0, `platform_core.py`,
the platform/module/plugin registry)** — they share a name prefix by
coincidence of sprint naming only.

## Global Instrument Registry (Section 1) — extends P15, no new table

P15's `RegistryInstrument` (`app/models/instrument_registry.py`) is
already a real, global, network-aggregate instrument registry —
manufacturer, model, category, anonymized network defect/pass rates,
k-anonymity-gated. Genesis AI extends it directly with:

| Brief item | Column |
|---|---|
| Family | `instrument_family` |
| IFU Versions | `ifu_versions_json` |
| Anatomy Profiles | `anatomy_profile_id` (references `AnatomyProfile`, below) |
| Inspection Zones | `inspection_zones_json` |
| Digital Twin Templates | `digital_twin_template_ref` |
| Baseline Templates | `baseline_template_ref` |
| Failure Modes | `failure_modes_json` |
| Repair Guidance | `repair_guidance` |
| Knowledge References | `knowledge_references_json` |

`instrument_registry_service.py`'s existing functions (and its seeded-
mock-fallback behavior for demo data) are untouched —
`genesis_ai_instrument_registry_service.py` only manages the new
columns, and only ever on real rows; it never fabricates a profile.

```
PATCH /api/genesis-ai/instruments/{id}/profile
GET   /api/genesis-ai/instruments/{id}/profile
GET   /api/genesis-ai/instruments/families/{family}
```

## Global Anatomy Registry (Section 2) — genuinely new

No anatomy-profile standardization taxonomy exists anywhere in this
codebase — every existing `zone`/`instrument_type` field elsewhere is
free text. `AnatomyProfile` covers the full named list (scissors,
forceps, needle holders, Kerrisons, rongeurs, drill bits, rigid scopes,
flexible endoscopes, powered instruments, robotic instruments, implants)
plus an explicit `other` value for "future expansion" — never a silent
rejection of an instrument type the taxonomy hasn't caught up to yet.

```
POST /api/genesis-ai/anatomy-profiles
GET  /api/genesis-ai/anatomy-profiles/{id}
GET  /api/genesis-ai/anatomy-profiles?profile_type=scissors
GET  /api/genesis-ai/anatomy-profiles/summary
```
