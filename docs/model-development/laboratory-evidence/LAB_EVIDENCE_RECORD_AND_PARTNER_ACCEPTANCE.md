# LumenAI Stage 3 — Laboratory Evidence Record & Partner Acceptance Package (LUM-SCI-005)

**Version:** 0.1 / 2026-11-12. **Status:** template; no laboratory results, partners or approvals exist.  
**Owner:** existing LumenAI science/model-governance program, not a new backend registry.  
**Protocol:** [LUM-SCI-004](STAGE_3_CONTROLLED_LAB_STUDY_PROTOCOL.md).

## A. Laboratory partner qualification

| Control / qualification | Evidence required | Reviewer / status |
|---|---|---|
| Scope and capabilities | documented materials characterization, calibrated optical/microscopy and/or quantitative soil assays, imaging of representative stainless specimens | PENDING |
| Institutional oversight | EHS/biosafety approval, appropriately trained personnel, specimen exclusions, ethics/IRB determination when applicable | PENDING |
| Quality and repeatability | documented SOPs, method verification, calibration and traceability, replicate analysis, uncertainty, blank/positive/negative controls | PENDING |
| Data rights | executed image/data-use license allowing specified ML experiments, derived model terms, retention, confidentiality, limitations on OEM release | PENDING |
| Independent truth | defined materials/assay reference method and expert reviewers; analyst blinded to model predictions where feasible | PENDING |
| Information security | role-controlled storage, de-identification plan, file hashing, retention/deletion, transfer agreement, isolation from patient clinical inventory | PENDING |
| Scientific design | pre-registered hypothesis, sample-size rationale, distinct specimen batches and camera/session holdout, full failure analysis | PENDING |
| Clinical governance | SPD clinical reviewer, manufacturer IFU/anatomy applicability and separation of lab outcomes from clinical release decisions | PENDING |

**No lab is preapproved by name, reputation, credentials, or a published paper alone.** MIT, Harvard, WPI, and qualified commercial laboratories are *prospective* contacts only.

## B. Proposed reference evidence manifest (conceptual fields, not a new database schema)

### Identity, licensing and chain of custody
- `study_id`, `study_protocol_version`, `lab_id`, `specimen_id`, `batch_id`, `acquisition_session_id`, `capture_id`, `capture_timestamp_utc`.
- `specimen_origin` (research-only coupon / retired instrument / authorized manufacturer test sample), `not_for_clinical_use=true`, `custody_record_ref`.
- `material_alloy`, `surface_finish`, `instrument_family`, `model_or_catalog`, `anatomy_zone`, `specimen_configuration`.
- `rights_evidence_ref`, `commercial_ml_train_use`, `oem_external_release_allowed`, `retention_rule`, `human_material_or_phi_review_status`.
- `source_provenance = laboratory_controlled` **must remain separate from real_clinical**, even though actual lab photographs are real images.

### Imaging
- `image_sha256`, `original_image_location`, `camera_device_id`, `modality` (borescope/macro/microscope), `objective_or_lens`, `magnification_or_working_distance`, `orientation`, `illumination`, `white_balance`, `exposure`, `focus_grade`.
- `scale_reference_ref`, `color_reference_ref`, `image_width_px`, `image_height_px`, `capture_operator`, `camera_calibration_version`.
- Record `baseline_id` and `baseline_compatibility` **only if independently available**; null is a normal independent-inference case.

### Independent reference / laboratory truth
- `material_truth_status` (confirmed/suspected/indeterminate/not_tested), `reference_finding_type`, `reference_assay_or_metrology_method`, `method_revision`, `analyst_id`, `assay_date`.
- `assay_target`, `unit`, `measured_value`, `measurement_uncertainty`, `limit_of_detection`, `limit_of_quantification`, `blank_control_result`, `positive_control_result`.
- Corrosion: `verified_corrosion_product`, `affected_area_mm2`, `affected_area_fraction`, `reference_instrument_area_mm2`.
- Pits: `pit_count`, `pit_diameter_distribution`, `pit_depth_distribution`, `profilometry_method`, `measurement_resolution`.
- Residue: `verified_soil_identity`, `source_or_analogue`, `mass_or_protein_reference`, `recovery_efficiency` if measured.
- `physical_truth_region_ref`, `geometric_registration_status`, `truth_limitations`.
- Do not substitute color/visual classification for chemical or physical confirmation.

### Reviewer observations and governance
- `visual_observation_category` maps to the existing `observation_taxonomy.py`; distinct proposed scientific subtypes must not silently mutate the production vocabulary.
- `visual_region_annotation_ref`, `visual_severity_descriptor`, `reviewer_id`, `review_round`, `review_blinded`, `confidence`, `review_disagreement`, `adjudication_ref`.
- `dataset_version`, `source_license_status`, `lcid` (only after governed Canvas intake), `ground_truth_approval_ref`, `group_split_key`, `holdout_sealed`, `model_eligibility_status`.
- **Never write fabricated values as zeros.** Use null/unknown and reason; maintain original lab record independent of AI and human annotations.

## C. Research quality-control checks

1. **Identity:** unique `specimen_id` and timepoint; no image attached to multiple incompatible specimen labels.
2. **Physical truth:** confirmed/suspected/indeterminate status tied to original lab report; blanks and relevant negative controls included.
3. **Image integrity:** original bytes hash verified; capture settings complete, calibrated area/depth claims tied to metrology.
4. **Reviewer independence:** lab analyst and annotation reviewers separated where feasible; blind adjudication and disagreement retained.
5. **No leakage:** all frames, timepoints, augmentations and modalities from the same `specimen_id` in one split; guard against batch/site leakage.
6. **Source isolation:** external_nonclinical and laboratory_controlled evidence must not become real_clinical through free-text facility names.
7. **Safety:** no “confirmed blood,” “sterile,” “clean,” “safe,” or “degree of rust” based on pigment/color-only heuristics.
8. **OEM separation:** original lab rights, hospital/tenant rights, reviewer confirmation and manufacturer data license are distinct gates.

## D. Minimal research study analysis plan

| Question | Reference measurement | Primary performance description | Controls |
|---|---|---|---|
| Rust-like appearance vs false positives | independent material identification and affected area | class-specific sensitivity, precision, false-negative rate + calibration | dyes, residue, lighting, finishes |
| Suspected pitting localization | calibrated microscopy/profilometry and expert annotations | per-pit/region detection, false negatives by small pit size, location overlap | machining, scratch, shadows |
| Blood-like residue vs rust | independently verified test-soil identity and relevant assay | sensitivity/specificity and abstention under class ambiguity | rust/iron oxide, cleaning residue and dyed controls |
| Bone/tissue-like particulate | reference simulant identity, particle geometry and location | per-object recall and zone-specific uncertainty | lint, dust, detergent and plastic fragments |
| Severity | physical area/size/depth or expert-adjudicated severity framework | ordinal error, agreement and calibration per finding category | differing alloys, cameras and specimen batches |
| Baseline value | paired compatible images, otherwise null | standalone image performance vs baseline-enriched performance in matched cohorts | blinded comparison; never gate standalone inference |

Predeclare confidence intervals, minimum samples and acceptance criteria with scientific/statistical reviewers. The existing clinical validation plan's thresholds are **future validation targets**, not established LumenAI results.

## E. Deliverables from a qualified lab (not yet supplied)

- Signed protocol, EHS/ethics approvals and lab QA method references.
- Specimen provenance/rights manifest and instrument material identity.
- Independently measured test reference table with units, detection limits and uncertainty.
- Calibrated original images, hashes, camera/capture provenance, hard negatives, all unusable images with reasons.
- Blinded reviewer annotations, discordance/adjudication records, physical-truth reconciliation.
- Replicate/reproducibility statistics, deviations, instrument/session grouped splits and sealed evaluation cohort.
- Signed materials/biochemistry/SPD/ML review and *research-only* model-release boundaries.
- Data-transfer/retention contract, including manufacturer sharing restrictions.

**Acceptance:** L0 only when laboratory, clinical, rights, ethics/safety and statistics approvals are documented. L1–L4 remain unperformed until corresponding evidence exists.

## F. Blocking implementation dependency

Current `backend/app/services/ml/training_eligibility_service.py` has a **synthetic-marker versus real** provenance heuristic. Before lab or external sources are ingested, update the existing dataset/annotation/registry path with explicit, validated provenance categories and deny-by-default training promotion rules. That is a separate engineering PR; this file does not create runtime objects.

**Current state:** Document/template only. No partner contracted; no reference specimen was manipulated; no dataset downloaded or model trained.
