# LumenAI Stage 3 — Controlled Laboratory Evidence Study Protocol (LUM-SCI-004)

**Version:** 0.1, protocol for scientific/clinical/ethics review — 2026-11-12  
**Status:** DRAFT; no laboratory partnership, specimen exposure, image acquisition, assay, trained model, or clinical validation is represented as completed  
**Program objective:** Provide scientifically measured, independently reviewed reference evidence to support research on suspected corrosion, rust-like deposits, pitting, blood-like residue, bone/tissue-like particles, and hard negative appearances on surgical-instrument materials.

**Existing foundations — do not duplicate:** [LUM-SCI-001 source register](../SCIENTIFIC_EVIDENCE_AND_DATASET_ACQUISITION_REGISTER.md); [Stage 2 dataset qualification](../STAGE_2_EXTERNAL_DATASET_QUALIFICATION_GATE.md); [LUM-CVP-001 clinical validation plan](../../clinical/clinical-validation-plan.md); [Clinical safety review](../../clinical/clinical-safety-review.md); [Project Lens first model scope](../FIRST_MODEL_SCOPE.md). Study observations must be mapped through the *existing* canonical ontology and Project Canvas/LCID annotation and Project Lens governance.

## 1. Scientific questions, estimands, and claims boundaries

**Primary research questions**
1. Under controlled, documented specimen conditions, which visual and spatial features can distinguish **suspected corrosion products**, **pits**, **blood-like residue**, and **bone/tissue-like particulate** from common false-positive appearances?
2. Can blinded visual observers identify *regions* whose material identity or surface state is independently established by laboratory evidence? Which findings remain ambiguous under normal RGB borescope imaging?
3. Can severity be described using *physical reference measurements* (area/coverage, pit counts/depth, confirmed soil loading, distribution and anatomy), rather than color alone or model class confidence?
4. Which instrument materials, finishes, illumination settings, anatomy zones, and imaging devices are associated with false negatives or false positives?
5. Does providing an approved compatible baseline improve interpretation **without becoming a prerequisite for standalone image inference**?

**Hypotheses to pre-register (not asserted as true):**
- H1: Localized image features plus controlled illumination outperform a global image color statistic on a blinded discrimination task.
- H2: Corrosion and biological-soil color ranges overlap enough that visual-only material identification requires an uncertainty/abstention pathway.
- H3: Physical pit measurements and visibly affected area add clinically useful severity information beyond classifier confidence.
- H4: Baseline-comparison evidence may improve localization for compatible image pairs, but an absent baseline must not suppress independently validated observation outputs.

**Intended output:** Research evidence and candidate feature/label definitions for future independent validation. **Not** a cleaning-validation study for a marketed reusable device, **not** evidence of sterilization, **not** a substitute for manufacturer IFUs, **not** a clinical “pass,” and **not** an FDA classification or clearance determination.

## 2. Governance, lab eligibility, and STOP rules

Only an institutionally approved, qualified materials/medical-device laboratory may design and execute specimen preparation, exposures, assays, and disposal. Obtain laboratory EHS/biosafety approval, appropriate equipment competency, material/chemical safety review, and written study oversight **before any experimentation**. No procedures involving pathogens, patient-derived specimens, regulated biological samples, hazardous chemicals, or medical instruments intended to return to service are authorized by this document. Prefer benign manufactured/standardized simulated soils in the first study; any biological blood/tissue work requires separate institutional biosafety review and supplier chain-of-custody, not this protocol alone.

- **No patient-contact return:** Study specimens are purpose-made coupons, retired instruments with documented authorization, or manufacturer-supplied research-only samples. They must be labeled **NOT FOR CLINICAL USE** and excluded from SPD release workflows.
- **No human subjects/PHI assumption:** Collect no patient identities. If human-derived material or clinical specimens are proposed, conduct institutional human-subjects/IRB and biosafety determination before collection.
- **No ad hoc on-site experiments:** Do not expose clinical inventory to chemicals, soil or accelerated corrosion agents in SPD.
- **Rights and independence:** Have a signed laboratory data/materials agreement covering commercial ML-training rights, images, measurement files, attribution, publication, manufacturer sharing, and data retention. Facility permission to inspect does **not** automatically grant OEM licensing rights.
- **Safety review:** Clinical SPD reviewer, materials scientist, lab validation specialist, data-rights officer, and ML evaluation lead approve the protocol, measures, masking, and blinded sampling plan before data generation.
- **Regulatory claims:** Existing LumenAI documents contain proposed FDA pathways/targets. Treat regulatory classification and all performance targets as *planning assumptions pending specialist assessment*, not an established regulatory determination.

## 3. Study arms and ground-truth reference methods

Specimens should represent clinically relevant instrument surfaces, including applicable alloys and surface finishes; the materials expert chooses and documents the particular models/materials. ASTM F899-23 provides material-class context for surgical-instrument stainless steel; it is **not** a severity standard.

| Study arm | Authorized specimen concepts (lab selects methods) | Reference evidence independent of image | Proposed research label / confounders |
|---|---|---|---|
| C0 — Clean reference | Documented clean research-only stainless specimens across finishes, with optional benign non-target stains | Surface identity/condition, lab documentation, no target analyte on controls within assay limits | Clean-*relative to tested target*, not sterile or “safe” |
| C1 — Corrosion-like surface products | Documented laboratory corrosion specimens and naturally corroded retired materials after risk review | Materials characterization (e.g., optical microscopy and specialist-selected chemical/spectroscopic confirmation), calibrated affected area | Suspected corrosion/rust-like appearance; avoid inferring mechanism or time from color |
| C2 — Pitting/crevice degradation | Documented specimens with pitting or benign manufactured reference pits | Optical/3-D microscopy or profilometry: pit count, size, distribution, depth where measurable | Suspected pitting; distinguish pit depth from 2-D darkness; differentiate machining features/scratches |
| C3 — Blood-like soil | Approved commercially supplied simulated blood-relevant test soils or nonhazardous optical analogues; separate prospective bioapproved sub-study if justified | Supplier identity, independent chemical/protein/hemoglobin-related assay as appropriate; control swabs; loading and post-clean residue measures | **Blood-like visual appearance**, not “confirmed blood” without appropriate analytical reference |
| C4 — Bone/tissue-like residue | Nonclinical certified simulants, artificial particles or specifically authorized research material | Independent material/simulant identity, particle size/amount and location; laboratory assay/microscopy when appropriate | Suspected bone/tissue-like particulate; require tests for lookalikes |
| C5 — Hard negatives | Water/mineral deposits, detergent residue, benign dyes, lubricant, reflections, discoloration, machining marks, brushed surfaces, shadows, camera artifacts | Independently confirmed absence of target substance where possible and reference identity of lookalike | Prevent rust/blood/pit false positives; explicit ambiguous class permitted |
| C6 — Mixed findings | Approved combinations only after single-material arms characterized | Component-wise reference measurements + spatial annotations; uncertainty documented | Multi-label / overlapping regions; cannot assume exclusive categories |

**Why independent reference measurements matter:** FDA cleaning-validation guidance emphasizes clinically relevant test soils and quantitative residual-soil measures. A separate medical-device-cleaning study investigated 140 material/soil/application combinations and found material-specific adhesion differences. These sources guide *study design* but do not validate computer-vision substance identification on stainless instruments.

## 4. Experimental factors and controlled imaging

Pre-register factor ranges and sample sizes with a statistician and lab lead; **no arbitrary stage-to-time equation or color threshold**. Record factors rather than hiding them:
- **Material identity:** documented steel alloy/material grade, finish, coating/passivation, instrument type/family, geometry and anatomy zone.
- **Condition:** scientifically determined soil identity or corrosion mechanism, independently measured amount/distribution, specimen history and exposure batch.
- **Temporal factor:** repeated measurements only if safely approved by the lab; paired images at *prespecified* relative timepoints and environmental conditions, with an *independent* lab measurement at each timepoint. Time is not a diagnosis or age estimate from a photograph.
- **Environment:** measured room temperature, relative humidity, visible surface wetness/condensation, lighting, background and calibration target if available.
- **Capture:** the actual LumenAI-compatible borescope plus an independent calibrated macro/microscope reference system; lighting profile, white balance, exposure, focus, working distance, field of view, image mode, view/orientation.
- **Replicates:** across independently prepared physical specimens, preparation batches, imaging sessions, equipment/camera operators, and laboratory sites where feasible.

**Standardized capture:** Include scale reference/calibration where practical; preserve original image bytes, EXIF/camera metadata if available, image hash and capture settings. Reject or mark obscured/overexposed/out-of-focus images with documented reasons; **do not selectively remove hard negatives or quality failures from evaluation denominators**.

**Controlled comparison sub-study:** capture matched baseline and changed-condition views only when physical instrument identity, view/zone, scale/orientation and imaging compatibility are documented. Baseline may aid deviation analysis but is **optional** for the standalone defect-detection task.

## 5. Measurement endpoints and reporting rules

**Scientific truth, separate from model outputs:**
- Corrosion material identity: confirmed / suspected / indeterminate by independent laboratory method; assay/microscopy and analyst provenance.
- Corrosion extent: measured area fraction and spatial distribution (where physically calibrated); no fixed color-to-severity stage.
- Pitting: count, density/area, measurable width/diameter/depth (lab method must report measurement resolution, detection limit and calibration), and geometry location.
- Soil/residue: independently confirmed surrogate/soil identity; quantified mass, protein/hemoglobin-related or other validated assay marker when scientifically suitable, recovery efficiency, limit of detection/quantification, and anatomical localization.
- Reference annotations: polygon/bounding box/region, visible-area limitations, disagreement/adjudication, reference-to-camera geometric transform if a spatial mapping is possible.
- Human assessment: blinded visual labels and confidence, agreement (e.g., kappa), human-vs-physical truth discrepancy.

**Research-model endpoints to compute, not preclaim:** per-finding sensitivity/recall, specificity, precision, FPR/FNR, localization overlap when well-annotated, severity ordinal error against *expert physical grading*, calibration, abstention/coverage, and subgroup variation by metal finish, instrument family, anatomy, camera, and lighting. Track accuracy only as a secondary summary.

**Safety-first:** suspicious residue and significant damage require independent human review; image-only “no finding” does not imply microbiologically clean, sterile or reusable. No model performance percentage is asserted by this protocol.

## 6. Truth hierarchy, evidence linkage, and leakage controls

1. Primary truth = independently verified specimen identity + assays/metrology; maintain a **material_truth_status** separate from visual label.
2. Independent blinded human reviewers annotate the same images; clinical reviewer adjudicates disagreement. Store observer judgments separately from lab assay truth.
3. Keep physical-specimen identifier, laboratory batch, imaging session, and paired timepoints grouped when splitting. **No frame from the same specimen/experiment in both training and sealed test.**
4. Reserve a separate intended-use evaluation cohort of real surgical-instrument borescope captures, including different cameras/facilities and difficult negatives, before clinical claims.
5. Record stage/source provenance as `laboratory_controlled` or `external_nonclinical` in governing metadata; *never* let a facility-name-based heuristic promote such data to `real_clinical`. Stage 2 identified the current provenance limitation in Project Lens; it must be addressed and tested **before** Canvas/Lens ingestion.
6. All actual Canvas/LCID imports remain subject to existing consent, rights, data-quality and blinded-ground-truth approval controls. Do not create a new registry or bypass the model promotion ladder.

## 7. Laboratory partner work packages (non-operational protocol)

**WP-A Materials:** confirm study material classes and suitability; plan corrosion/pit reference measurements and analysis; document limits and uncertainty.

**WP-B Cleaning-validation/biochemistry:** select clinically relevant, authorized simulated soils; plan independent material identity/soil residue assays; document test controls, recovery and assay limits.

**WP-C Imaging and ML:** calibrate imaging instrumentation, identify measurable spatial evidence, propose group-safe data-split protocol and qualitative error analysis; perform **research-only** experiments after rights and provenance gates.

**WP-D Clinical SPD and governance:** approve instrument zones, IFU context, meaningful review categories, observer eligibility, risk scenarios, and human disposition boundaries; review trial outputs against existing LUM-CVP-001, not an invented parallel clinical approval.

Lab teams own detailed SOPs, required apparatus, specimen recipes, sample counts and safety conditions under their approved quality system. This document intentionally does not prescribe hazardous preparation or corrosion chemistry procedures.

## 8. Phased milestones and acceptance

**L0 — Protocol approval (not yet):** named scientific principal investigator; partner site qualification; EHS/ethics and data-rights signoff; pre-registered endpoints, measurement methods, specimen counts and confidence intervals; budget and material/IFU restrictions.

**L1 — Feasibility (not yet):** documented small reference panel of research-only specimens with calibrated photos, replicate reference measurements, negative controls and complete acquisition manifest. No acceptance from unmeasured photos alone.

**L2 — Reproducibility (not yet):** independent preparation/camera/session batches, analyst agreement, metrology or assay repeatability, missing-data report and blinded evaluation.

**L3 — Experimental ML (blocked until Stage 2 provenance gate):** qualified lab data can support strictly research-only experiments, with explicit nonclinical provenance and a sealed external validation cohort. No clinical model promotion.

**L4 — Clinical transfer (separate future gate):** use validated clinical images and the existing blinded multi-site LUM-CVP-001 protocol; metrics approved by a clinical governance body; regulatory evaluation and clinical signoff. This laboratory study by itself cannot satisfy that gate.

**Current status:** L0 through L4 not executed. No lab selected, no approved recipe, no specimen data, no accepted clinical model.

## 9. Verified primary references and applicability limits

1. **FDA, Reprocessing Medical Devices in Health Care Settings: Validation Methods and Labeling (2015)** — https://www.fda.gov/regulatory-information/search-fda-guidance-documents/reprocessing-medical-devices-health-care-settings-validation-methods-and-labeling — principles of clinically relevant soil, appropriate cleaning endpoints, and IFU validation; not an AI vision validation method.
2. **FDA recognition, ASTM F3208-20** — https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfStandards/detail.cfm?standard__identification_no=41831 — selecting reusable-device simulated test soils; not a general-purpose hospital cleaning check.
3. **FDA recognition, ANSI/AAMI ST98:2022** — https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfstandards/detail.cfm?standard__identification_no=43767 — manufacturer cleaning-process validation requirements; **not** LumenAI AI clinical validation.
4. **FDA recognition, ASTM F3293-18** — https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfStandards/detail.cfm?standard__identification_no=37515 — device-soiling application considerations (licensed standard needed for detailed procedures).
5. **FDA recognition, ASTM F3321-19** — https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfstandards/detail.cfm?standard__identification_no=40959 — extraction of residual test soils.
6. **ASTM F899-23** — https://store.astm.org/standards/f899 — surgical instrument stainless-alloy material classes; not a corrosion clinical grade.
7. **ASTM G46-21** — https://store.astm.org/g0046-21.html — pitting examination and evaluation reference; requires specialist interpretation.
8. **ASTM G48-25** — https://store.astm.org/g0048-25.html — comparative susceptibility in accelerated chloride environments; does **not** define real-life corrosion time stages.
9. **Kremer & Ratanski (2023), Test Soil and Material Affinity for Reusable Device Cleaning Validations** — https://pmc.ncbi.nlm.nih.gov/articles/PMC10764060/ — 140 material/soil/application combinations; supports study factor selection, not vision accuracy.
10. **Bremmer et al. (2011), Biphasic Oxidation of Oxy-Hemoglobin in Bloodstains** — https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0021845 — spectral changes and temperature/humidity effects on a different substrate; no direct transfer to stainless-steel RGB classification, or visual age inference.

Standards are copyrighted and may need institutional licensed access. This protocol links to official abstracts and peer-reviewed sources without redistributing protected standard procedures.
