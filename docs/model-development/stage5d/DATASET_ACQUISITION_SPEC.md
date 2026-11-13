# Stage 5D — Governed Instrument & Borescope Dataset Acquisition Specification

Status: **specification only — no such dataset has been acquired.** This document
defines the governed research acquisition and validation workflow for real
surgical-instrument and borescope imagery. It reuses the existing Project Canvas /
LCID ingestion, provenance, rights, consent, retention, and annotation controls.
It authorizes **no** collection by itself; each cohort requires the institutional
and laboratory approvals named in §7.

> Research-only. Lab specimens acquired under this spec must **never** re-enter
> clinical use. Hospital/patient data must **never** be ingested without the
> necessary institutional authorization (IRB/again-privacy/data-use agreement).

## 1. Intended research use (predefined)

Detect and localize surface/lumen anomalies on reusable surgical instruments from:

- **External-camera images** — stainless-steel instrument surfaces (macro photos).
- **Borescope images** — internal instrument lumens/channels.

The research question is *anomaly localization* (does an unexpected region exist,
and where), **not** confirmed material identity or sterility status. Confirmed
identity comes only from laboratory evidence (see `GROUND_TRUTH_PROTOCOL.md`).

## 2. Specimen classes to acquire

| Class | Description | Independent reference required |
|---|---|---|
| `verified_clean_reference` | Confirmed-clean reference instruments | Independent clean verification (not "looks clean") |
| `corrosion_documented` | Documented corrosion | Material characterization (EDS/XRD/SEM-EDS) + affected-area measurement |
| `pitting_documented` | Documented pitting | Microscopy/profilometry + pit geometry |
| `blood_like_residue` | Blood-like residues | Protein/hemoglobin assay or documented soil-identity confirmation |
| `bone_tissue_like_residue` | Bone-/tissue-like residues | Composition/independently-verified particle identity |
| `hard_negative_confounders` | Reflections, scratches, detergent films, mineral deposits, benign discoloration | Independent review that the surface is benign/normal |

**Hard negatives are mandatory.** A model that cannot separate corrosion from a
reflection or a detergent film is unsafe; each anomaly class ships with
confounders that visually resemble it.

> **No "absence of visible anomaly ⇒ normal".** An instrument is labeled
> `verified_clean_reference` only with an independent clean verification, never
> because nothing was visible. Unlabeled/uncertain images are their own states
> (see ground-truth protocol), never silently treated as normal.

## 3. Required per-image metadata (Canvas/LCID)

Every acquired image records, through the existing Canvas/LCID pipeline:

- physical instrument id, specimen id, **study/lab batch id**
- facility/source laboratory, imaging **device** and **acquisition session**
- **image content SHA-256** (integrity + duplicate detection)
- anatomy zone and **view** (external surface vs lumen; which aspect)
- modality (`external_camera` | `borescope`)
- illumination/lighting condition where controllable
- data-provenance class, rights, consent reference, retention status

These fields drive the leakage-safe grouping in `EVALUATION_PROTOCOL.md` (group by
instrument/specimen/session/batch/exact-duplicate) and the Stage 5C
`enforce_supplied_dataset_governance` integrity/tenant checks.

## 4. Governance gates (reused, not duplicated)

A candidate image enters research only when the existing controls pass:

1. **Provenance class** is research-authorized (`synthetic_experimental`,
   `external_nonclinical`, `laboratory_controlled`), or `real_clinical` **with**
   explicit approval **and** a verified research-use consent scope.
2. **Rights / quality / PHI / archival** structural gate passes.
3. **Retention** is active (bytes present, not purged).
4. **Tenant** isolation holds — no cross-tenant mixing in a dataset.
5. **Integrity** — image SHA-256 present and consistent.

Supplied (directly handed) datasets pass the **same** gates via
`enforce_supplied_dataset_governance`; they cannot bypass Canvas governance.

## 5. Modality separation

External-camera and borescope images are **governed and evaluated separately**
(different optics, scale, illumination, distortion). They are never pooled into one
threshold or one reported metric. Each modality carries its own calibration and
sealed test cohorts.

## 6. Acquisition integrity rules

- No PHI in images or metadata; borescope captures are reviewed for incidental PHI.
- Lab specimens are tracked as research-only inventory and **quarantined from
  clinical reuse** for their lifetime.
- Chain-of-custody from specimen → imaging session → stored image is recorded.
- Duplicates (same SHA / same physical specimen re-imaged) are tracked so they
  never straddle fit/calibration/test.

## 7. Outstanding approvals & evidence (BLOCKED until provided)

1. Institutional authorization for any clinical-adjacent or facility data; data-use
   agreements; IRB/ethics determinations where applicable.
2. Qualified laboratory partner(s) for the independent reference measurements in §2.
3. Specimen-sourcing agreements for documented corrosion/pitting/residue instruments
   and confirmed-clean references.
4. Borescope hardware + controlled capture protocol (illumination, focus, scale bar).
5. Statistical + clinical reviewer sign-off on target cohort sizes (see eval protocol).

**No real instrument or borescope images exist in this repository.** This spec is
the readiness blueprint; executed scientific acquisition is future work.
