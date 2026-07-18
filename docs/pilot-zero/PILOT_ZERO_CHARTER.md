# Pilot Zero Program — Charter

## What Pilot Zero is

An **internal research and engineering program** to develop LumenAI's
first validated computer-vision candidate models on real inspection
imagery, under full governance. It replaces the platform's deterministic
placeholder scoring through governed datasets and candidate models.

Pilot Zero is **not** a clinical deployment, **not** a hospital
implementation, and **not** FDA validation. LumenAI is a vendor-neutral
Clinical Inspection Intelligence Platform, not a borescope manufacturer;
Pilot Zero consumes images from compatible inspection hardware.

The Version 1.0 platform architecture is **frozen**: no new features,
specialists, modules, dashboards, or workflows unless required to
support Pilot Zero. Any recommendation expanding scope beyond Pilot
Zero is rejected unless explicitly approved by the program owner.

## Standing engineering law (applies to every workstream)

* Every artifact version-controlled; every process auditable.
* Every dataset has provenance; every image has metadata (and a
  permanent LCID); every annotation has reviewer attribution; every
  Ground Truth record is versioned; every model is traceable to its
  dataset, configuration, and code revision.
* Human clinical authority is preserved in every design.
* Operate toward future ISO 13485, IEC 62304, ISO 14971, SOC 2, HIPAA,
  and FDA expectations **without claiming compliance with any of them**.
* No unsupported claims — performance, clinical, or regulatory.

## Workstreams (priority order)

| WS | Name | Maps to priorities | Status |
|---|---|---|---|
| 1 | Security and Engineering Gate | 1–4 (integrity, security, governance, reproducible builds) | ACTIVE — `WS1_SECURITY_ENGINEERING_GATE.md` |
| 2 | Hardware Qualification | 5 | Pending WS1 exit |
| 3 | Image Acquisition | 6 | Pending WS2 |
| 4 | Instrument Registry | 7 | Pending WS1 |
| 5 | Baseline Development | 8 | Pending WS3/WS4 |
| 6 | Annotation | 9 | Pending WS3 |
| 7 | Ground Truth | 10 | Pending WS6 |
| 8 | Dataset Governance | 11 | Pending WS7 |
| 9 | Candidate Model Development | 12 | Pending WS8 |
| 10 | Technical Validation | 13 | Pending WS9 |
| 11 | Pilot Alpha Readiness | 14 | Pending WS10 |

Every engineering task in the program must map to exactly one
workstream; tasks that map to none are out of scope by definition.

## Inherited assets (already built and tested; reused, not rebuilt)

LCID identity + dataset registry + frozen dataset versions; Canvas
ingestion; annotation database with double-blind review and versioned
Ground Truth; Atlas baseline library with hash-verified access; model
registry with checksummed artifacts and the 5-stage promotion ladder;
reproducible training pipeline; hash-chained append-only audit;
governed object storage; executed backup/restore/DR procedures;
PostgreSQL-verified persistence. Pilot Zero's job is to feed this
machinery **real** images for the first time — not to rebuild it.

## Program-level risk register (top entries)

1. **Gate that doesn't gate** (WS1): CI has never executed on a PR;
   until fixed, every other workstream's evidence lacks independent
   verification. Mitigation: WS1 is first, and blocks WS2+.
2. **Synthetic-data habit**: all existing model evidence is synthetic;
   program success requires refusing to let synthetic data creep into
   Candidate claims (enforced in code: `Candidate` requires real
   provenance).
3. **Scope regrowth**: the platform's history is expansive; the freeze
   plus the workstream-mapping rule are the controls.
4. **Single-environment fragility**: development containers are
   ephemeral; the durable substrate decision (WS2 dependency) is a
   program owner action.
