# LumenAI Scientific Evidence & Dataset Acquisition Register (LUM-SCI-001)

**Version:** 1.0 (2026-11-12)  
**Status:** RESEARCH SCREENING — no external dataset ingested or approved for clinical training  
**Purpose:** Reuse credible corrosion science, blood/soil chemistry, and permitted external images without duplicating Project Canvas, Project Lens, the LCID registry, annotation workflows, or model governance.

## 1. Clinical mission and non-negotiable boundaries

LumenAI supports pre-sterilization instrument inspection: suspected abnormality detection **with or without a baseline**, anatomy-aware interpretation, documented uncertainty, qualified human disposition, and traceable evidence. Baselines enrich an inspection; they are not a prerequisite for visual inference. Research images may inform model development but **do not establish clinical performance** on surgical instruments or borescope imagery.

**Separation of evidence types**

1. **Scientific knowledge:** peer-reviewed methods, physical mechanisms, experimental findings; eligible for *reviewed knowledge references*, not automatic AI labels.
2. **External image datasets:** candidate pretraining, robustness, or research evaluation data; eligible only after rights, provenance, and domain-shift screening.
3. **Controlled laboratory reference images:** proposed standardized specimens with independently confirmed materials/conditions; requires an approved protocol and authorized lab.
4. **Real clinical instrument evidence:** intended-use images, expert-reviewed labels, independent evaluation; required for claims of clinical performance.

Never infer that brown color proves rust or blood, that color establishes bloodstain age, or that image similarity proves an instrument is safe/clean. Keep *suspected* visual findings separate from independent chemical/material confirmation. Preserve human review.

## 2. Initial verified source register

Status terms: **Reference only**, **Candidate — rights pending**, **Candidate — evaluate**, **Not acquired**. No source below is currently cleared for production clinical training.

| ID | Source / publication | Evidence, scope, and possible reuse | Rights and clinical limitations | Status / next action |
|---|---|---|---|---|
| SCI-001 | WPI / U.S. Army Research Laboratory, *Corrosion Image Data Set for Automating Scientific Assessment of Materials* (BMVC 2021); https://arl.wpi.edu/corrosion_dataset/ | 600 RGB JPG images (512×512) with expert corrosion ratings; research on ratings and corrosion-feature transfer. | Website states “MIT License © 2021 WPI,” but **verify that the downloadable image bytes, ratings, derivative models, and commercial use are covered** by the specific download README/license or direct written approval. Industrial corrosion, not surgical/borescope clinical data. | **Candidate — rights pending.** Read archive README; retain license evidence; inspect class/rating schema. |
| SCI-002 | Buettner et al., *DefectAtlas-20*, Data in Brief (2026); https://pmc.ncbi.nlm.nih.gov/articles/PMC13571519/ ; dataset https://doi.org/10.5281/zenodo.21719370 | 13,233 RGB PNG images, 512×512, 20 material-condition classes, including coated/uncoated metal, with image-level labels and camera metadata. Useful for general surface-defect pretraining/robustness research. | **Paper** is CC BY 4.0; **verify the dataset record's own license** and third-party image rights before commercial reuse. Labels do **not** specify rust, pitting, defect location, depth, or severity. Smartphone-domain shift from borescope captures. | **Candidate — rights pending.** Inspect Zenodo license and archive; evaluate *metal subset* and labeling adequacy. |
| SCI-003 | Bremmer et al., *Biphasic Oxidation of Oxy-Hemoglobin in Bloodstains*, PLOS ONE (2011); https://pmc.ncbi.nlm.nih.gov/articles/PMC3137592/ ; DOI:10.1371/journal.pone.0021845 | Spectroscopic evidence for oxyhemoglobin → methemoglobin → hemichrome changes, with temperature/humidity dependence. Informs knowledge, confounders, and prospective lab design. | Study investigated bloodstains on cotton using optical reflectance; **not a validated RGB model for stainless steel** and not a clinical imaging dataset. Avoid blood identification or age estimation from color alone. Article CC BY; figure/data reuse still requires attribution/right checks. | **Reference only.** Extract scientific features and limitations into a human-reviewed evidence note. |
| SCI-004 | Kremer & Ratanski, *Test Soil and Material Affinity for Reusable Device Cleaning Validations* (2023); https://pmc.ncbi.nlm.nih.gov/articles/PMC10764060/ ; DOI:10.2345/0899-8205-57.4.136 | Published study of 140 combinations across materials including stainless steel, four blood-based simulated soils, and five application methods. Helps design controlled research and negatives. | Methodological reference; publication is **not** a freely licensed training image corpus. Methods do not directly validate visual blood/bone detection. | **Reference only.** Evaluate with laboratory partner for protocol design. |
| SCI-005 | ASTM F3208-20, *Guide for Selecting Test Soils for Validation of Cleaning Methods for Reusable Medical Devices*; FDA recognition: https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfStandards/detail.cfm?standard__identification_no=41831 | Recognized standards reference for selecting representative blood/tissue/bone-like test soils and quantitative/visual endpoints for reusable-device cleaning validation. | **Copyrighted standard**, not an open dataset. Obtain licensed text when needed; do not redistribute standard content or treat test soils as a hospital cleaning-validation procedure. | **Reference only.** Acquire access through licensed institutional channel for protocol governance. |
| SCI-006 | ASTM G46-21, *Guide for Examination and Evaluation of Pitting Corrosion*; https://store.astm.org/standards/g46 | Reference for examination and evaluation of pitting and potential pit measurement dimensions. | Copyrighted standard, not a labeled-image dataset or a surgical-device severity-grade validation. | **Reference only.** Materials-science adviser to map measurable descriptors. |
| SCI-007 | ASTM G48-25, *Test Methods for Pitting and Crevice Corrosion Resistance ... Ferric Chloride*; https://store.astm.org/standards/g48 | Reference for accelerated corrosion-susceptibility laboratory research on stainless steels and related alloys. | Copyrighted standard; accelerated test response **does not equal** real-world device deterioration chronology or clinical severity. Experiments only by appropriately equipped laboratories. | **Reference only.** Research partner feasibility review. |

**Verification date:** 2026-11-12. Direct websites and publication abstracts were checked. The WPI download-package terms and Zenodo *dataset* record license have **not** been independently cleared; no archive download, rights transfer, clinical validation, or model training is represented as completed.

## 3. Data acquisition record required for every candidate

Assign immutable **source_id + source_version + retrieval_date + source_url + DOI/publication + institution + contact**. Capture:

- **Data rights:** copyright holder; exact asset license (not merely article/site license); commercial ML training permission; redistribution and derivative-model terms; attribution; sublicensing/tenant sharing restrictions; written authorization evidence; legal approver.
- **Dataset facts:** image count and format; known duplicates; camera and illumination; instrument/material type; manufacturer and model if provided; time/exposure conditions; label granularity; class balance; quality and image metadata; sample checksum and archive SHA-256.
- **Clinical fit:** intended-use match (external camera vs borescope); relevant steel alloys and surface finishes; instrument family and anatomy zone; detectable category; negative/confounder coverage; expert-rating definition; available independent laboratory confirmation.
- **Privacy and provenance:** PHI screening, facility permissions, image rights and consent; contributor provenance; source organization; export restrictions; allowed training vs reporting vs commercial intelligence rights.
- **Release decision:** Research owner, rights reviewer, materials/biochemistry reviewer, SPD clinical reviewer, ML reviewer, review date, decision, exclusions, rationale, expiration/recheck date, and signed evidence location.

Recommended disposition: **REJECT**, **REFERENCE_ONLY**, **RESEARCH_ONLY**, **EXPERIMENTAL_DATA_APPROVED**, or **REAL_CLINICAL_GROUND_TRUTH_ELIGIBLE**. These are *documentation decisions*, not new runtime registry statuses.

## 4. Scientific mapping to existing LumenAI ontology

Use the canonical vocabulary at backend/app/services/observation_taxonomy.py and existing Project Canvas annotation fields.

| Scientific material | Possible clinical observation target | Evidence needed beyond color | Explicit prohibition |
|---|---|---|---|
| Iron oxides / metal corrosion products | probable_corrosion_like_degradation; proposed reviewer subtype *suspected rust* | Independently verified material, spatial distribution, substrate/finish information, specialist grading | Do not equate all red-brown deposits with rust |
| Surface pits / localized corrosion | probable_corrosion_like_degradation; proposed reviewer subtype *suspected pitting* | Microscopy/3-D surface evidence where feasible; expert location/depth/area rating | Do not equate dark pixels with pit depth |
| Blood-related residue | probable_blood_like_residue | Test-soil provenance and independent residue identification/assays in lab references | Do not conclude “confirmed blood” or estimate stain age from RGB appearance |
| Bone/tissue test soils | probable_bone_like_fragment / probable_tissue_or_organic_residue | Independently documented specimen/soil identity and localization | Do not treat appearance alone as proof of biological material |
| Clean or non-target contamination confounders | no_observable_abnormality **only within evaluated categories** | Verified clean/reference controls, non-target dyes/lubricants, reflective and damaged-but-unsoiled controls | Do not claim sterile/safe from images |

**Severity** must be a separately reviewed, category-specific measurement framework (e.g., visibly affected area, distribution, pit measurement, anatomy zone, examiner agreement), with uncertainty. It cannot be a conversion from classifier probability or arbitrary color stages.

## 5. Gated process: no bypass of existing Canvas/Lens governance

0. **Discover:** record trustworthy citation and exact dataset/standard identity.
1. **Rights review:** verify licensing and written permits; if unresolved, use for reading only, not image ingestion/training.
2. **Scientific suitability:** screen material, capture domain, annotations, gold standard, and confounders; assign appropriate use and exclusions.
3. **Data QA and provenance:** controlled acquisition; archive hash and source manifest; remove duplicates; verify PHI/consent and lab/sample identity.
4. **Canvas intake:** reuse dataset_ingestion_service → retained-image rights/consent gates → LCID Dataset Registry → existing annotation/review/adjudication → Ground Truth promotion. **No parallel image registry or self-promoted AI label.**
5. **Lens experiments:** use permitted experimental data for research/transfer learning **only**; group-safe splits by physical instrument/session/site and confirm facility-independent test sets. Existing model governance and model card must record provenance.
6. **Clinical validation:** blinded reader/ground-truth evaluation on intended-use borescope/clinical images; per-class sensitivity, false-negative rates, calibration, abstention, anatomy/lighting performance, inter-rater reliability; human review, go/no-go and documented intended-use boundaries.
7. **Commercial data release (separate):** confirmed findings alone are insufficient; verify hospital contracts, data-sharing consent, attribution, aggregation thresholds, manufacturer authorization, and data product licensing before OEM access.

No acquisition step authorizes operational clinical inference, manufacturer defect reporting, or clinical model promotion.

## 6. Next actions, in order

- **A1 — SCI-001 WPI:** inspect the archive README and rights; sample image labels; decide research-only scope.
- **A2 — SCI-002 DefectAtlas:** verify Zenodo record license/assets and inspect metal-subset metadata; define a domain-shift experiment, not a clinical endpoint.
- **A3 — SCI-003/004 blood science:** scientific adviser documents blood-like visual confounders and the need for independent chemical confirmation.
- **A4 — SCI-005/006/007 standards:** obtain institutional access and partner review; agree on measurables for soils, pitting, and surface corrosion.
- **A5 — Laboratory partner study proposal:** materials expert + cleaning-validation/biochemistry lab + SPD clinical reviewers; blinded imaging and independent reference measurements; no unapproved human biohazard work.
- **A6 — Clinical pilot:** acquire controlled real borescope images under signed data rights and existing Canvas procedures; maintain a sealed held-out evaluation set.

**Institutional outreach:** WPI, university materials laboratories (including MIT/Harvard research groups where pertinent), and accredited medical-device cleaning-validation laboratories are prospective partners, **not** represented as confirmed data providers.

## 7. Existing source-of-truth links (do not duplicate)

- [Project Lens first model scope](FIRST_MODEL_SCOPE.md)
- [Training eligibility report](TRAINING_ELIGIBILITY_REPORT.md)
- [Live inference integration](LIVE_INFERENCE_INTEGRATION.md)
- [Product capability maturity matrix](../product-truth-reset/PRODUCT_CAPABILITY_MATRIX.md)
- [Clinical validation plan](../clinical-validation/CLINICAL_VALIDATION_PLAN.md)
- [Frozen clinical architecture](../../VERSION_1_0.md)

**Acceptance for this documentation milestone:** Seven sources enumerated; provenance and license uncertainties disclosed; named use cases and exclusions; clear human/clinical/data rights gates; direct reuse of existing governance; no dataset bytes, trained model, inference outputs, or runtime behavior changed.
