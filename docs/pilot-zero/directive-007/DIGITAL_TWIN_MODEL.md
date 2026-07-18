# LPZ-DIR-007 — Digital Twin Model

**Purpose:** define the logical structure of a **Digital Twin** — the governed,
evolving record of a single reusable surgical instrument that ties together its
identity, inspection history, approved baselines, Ground Truth, and audit trail.
This is a **governance model**, not new software; each field is mapped to the
identity/records already present in the repository so the model is auditable
against reality.

Guardrails: no new AI functionality, no model training, no hospital deployment
workflow, no unsupported clinical/regulatory claim. The Digital Twin is a
**data-provenance construct**, not a clinical device or a predictor.

## Logical structure

| Field | Definition | System mapping (today) |
|---|---|---|
| **Digital Twin UUID** | Permanent, immutable identity of the twin | `digital_twin_id` (UDI/barcode-derived via `ml.lcid_service`, never fabricated) |
| **Instrument UUID** | The physical instrument the twin represents | LCID instrument identity |
| **Manufacturer** | Instrument manufacturer | `BaselineLibraryEntry.manufacturer_name`, `Annotation.manufacturer` |
| **Model** | Instrument model | `BaselineLibraryEntry.model_name`, `Annotation.instrument_model` |
| **Instrument Family** | Family/type grouping | `Annotation.instrument_family`, dataset entry |
| **Instrument Type** | Specific type within a family | family/model attributes |
| **Serial Number** (if available) | Unit-level identity when marked | LCID identity (optional) |
| **Tray Association** | Tray/set membership | flow/registration records |
| **Lumen Configuration** | Cannulation/lumen structure | annotation `lumen_region`, family attributes |
| **Anatomical Regions** | Engineering regions of interest | annotation `anatomical_zone` (instrument regions) |
| **Inspection History** | Inspections referencing this twin | `Annotation.inspection_id`, inspection records |
| **Baseline References** | Approved baselines for the twin | `BaselineImageLink` / `BaselineLibraryEntry` (ACTIVE) |
| **Ground Truth Links** | Approved GT records for its images | `Annotation` (GT ACTIVE) |
| **Image History** | Registered images of the instrument | `RetainedImage` / LCID `DatasetRegistryEntry` |
| **Annotation History** | Annotations across its images | `Annotation` / `AnnotationVersion` |
| **Lifecycle Status** | Twin state (active/retired) | governance overlay (see gap note) |
| **Version** | Twin revision | governance overlay (see gap note) |
| **Audit History** | Attributable change log | audit trail |
| **Relationships to future AI outputs** | Link slot for later model outputs | reserved; not populated under this directive |

## Identity rules

1. **Never fabricated.** The Digital Twin UUID derives from a real instrument
   identity (barcode/UDI) via `lcid_service`; it is never invented.
2. **Stable identity, versioned content.** The UUID is permanent; the twin's
   associated content (baselines, GT, history) evolves beneath it with versions.
3. **One twin per instrument identity.** The twin is the single governed anchor
   that all image/annotation/baseline/GT records for that instrument reference.
4. **No PHI.** The twin describes an instrument; no patient data enters it.

## Relationships (summary)

```
Instrument identity (UDI/barcode)
   └─ Digital Twin (this model)
        ├─ Image History      (RetainedImage / LCID entries)
        ├─ Annotation History (Annotation / AnnotationVersion)
        ├─ Ground Truth Links (approved GT)
        ├─ Baseline References(approved BaselineImageLink / BaselineLibraryEntry)
        ├─ Inspection History (inspections)
        ├─ Audit History      (audit trail)
        └─ Future AI outputs  (reserved link, not populated here)
```

## Governance note (existing system — honest gap)

Today the instrument Digital Twin is an **identity string** (`digital_twin_id`)
reused consistently across `Annotation`, LCID `DatasetRegistryEntry`, and the
baseline image library — not a single aggregate table. (Note: the module
`app/models/digital_twin.py` models **SPD workflow/operations** simulation, a
different concept, and is out of scope here.) There is also a `digital_quality_twin`
and several specialist twin *services* (Apollo/Oracle/Sentinel) that read this
identity.

This directive defines the **logical** Digital Twin model above and records, as a
migration recommendation (not implemented here), the option of a governed
aggregate "instrument Digital Twin" record carrying `Lifecycle Status`, `Version`,
and explicit reference lists — composed from the existing identity and records
rather than duplicating them. See `DIGITAL_TWIN_GOVERNANCE.md` and
`DIRECTIVE_007_REPORT.md`.
