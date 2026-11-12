# LumenAI External Scientific Source Qualification Record (LUM-SCI-002)

**Purpose:** A reusable, manual, evidence-backed decision form for each source in [LUM-SCI-001](SCIENTIFIC_EVIDENCE_AND_DATASET_ACQUISITION_REGISTER.md). This is a documentation template, **not** permission to download, import, train, promote a model, or commercialize data.

Copy this template to an individual per-source review record. Replace brackets with real evidence. Preserve original source files, review artifacts, and approval dates in authorized storage; do not commit patient images or restricted datasets to GitHub.

## A. Source identity

- Register ID: [SCI-00X]
- Source / authors / institution: [ ]
- Paper DOI / version / date: [ ]
- Dataset record / immutable version / retrieval link: [ ]
- Data controller/copyright holder and contact: [ ]
- Data modality: [publication / standard / microscopy / RGB / borescope / spectral / other]
- Sample size / usable image count: [ ]
- Intended use: [scientific knowledge / pretraining / robustness research / model training / validation]
- **Acquisition status:** NOT_ACQUIRED / QUARANTINED / RIGHTS_REVIEWED / QA_PASSED / REJECTED

## B. Licensing and confidentiality gate (blocking)

- Exact data asset license and version: [ ]
- Proof document URL/archive/hash: [ ]
- Commercial AI training permitted? [yes / no / unresolved]
- Derivative model and distribution permitted? [yes / no / unresolved]
- Attribution and reporting restrictions: [ ]
- Institutional written authorization required/obtained? [ ]
- Facility data-sharing/consent/BAA or other contractual restrictions: [ ]
- Privacy and PHI assessment: [ ]
- Reviewer / date / decision: [ ]

**STOP if any rights or privacy item is unresolved.** Journal article CC BY, institutional website MIT license, and public download accessibility do not necessarily license separate image datasets. Do not present this review as legal advice.

## C. Scientific relevance gate

- Target clinical ontology category / proposed reviewer subtype: [ ]
- Material (steel alloy / coated/uncoated), surface finish, instrument anatomy: [ ]
- Image capture domain and dimensions: [ ]
- Positive label meaning / verification method: [ ]
- Negative controls and visual confounders: [ ]
- Labels localize defects? [yes / no / unknown]
- Severity has measured physical reference? [yes / no / unknown]
- Laboratory confirmation? [chemical/material test / microscopy / expert rating / none]
- Independently reviewed annotations and inter-rater agreement: [ ]
- Domain shift vs intended LumenAI borescope workflow: [ ]
- Potential unintended claims: [ ]
- Clinical/material reviewer / date: [ ]

**No direct mapping from generic 'metal_defect' to confirmed 'rust', 'pitting', 'blood', or a severity grade.** No bloodstain age estimates or proof of clean/sterile/safe from an RGB photograph.

## D. Data QA and existing Project Canvas mapping

- Archive SHA-256: [ ]
- Asset count before/after duplicates, decoding failures and exclusions: [ ]
- Source manifest and retrieval record: [ ]
- Consent and permitted retention evidence: [ ]
- Dataset version, acquisition batch, and LCID mapping (if approved): [ ]
- Existing dataset ingestion workflow used: [ ]
- Annotation task and existing ground-truth adjudication pathway: [ ]
- Grouping keys for leakage-safe splits (instrument/session/facility): [ ]
- Holdout source/instrument/camera separation: [ ]
- Training data use approved? [research only / experimental / no]
- Project Canvas reviewer / date: [ ]

## E. Model-validation and commercial boundaries

- Project Lens experimental hypothesis: [ ]
- Intended-use clinical validation plan and per-class detection metrics: [ ]
- False-negative and abstention thresholds: [reviewed clinical protocol]
- Candidate model promotion status: [NOT ELIGIBLE unless separately approved]
- Manufacturer intelligence data product rights: [NOT AUTHORIZED unless separately signed]
- Allowed report audience, aggregation and privacy safeguards: [ ]
- Independent clinical reviewer: [ ]
- Data rights/quality reviewer: [ ]
- ML/model governance reviewer: [ ]
- Final disposition: REJECT / REFERENCE_ONLY / RESEARCH_ONLY / EXPERIMENTAL_DATA_APPROVED / REAL_CLINICAL_GROUND_TRUTH_ELIGIBLE
- Evidence links, signed decision, date, recheck/expiry: [ ]

## F. Initial evaluation tasks by source

- [ ] **SCI-001 WPI:** Download package README/licensing verification; confirm labels and rating protocol with WPI; research-only until signed off.
- [ ] **SCI-002 DefectAtlas:** Check Zenodo record's Rights section for exact dataset license; inspect image/CSV class schema; define metal-only exploratory experiment and abstention limits.
- [ ] **SCI-003 hemoglobin:** Literature evidence note: chemistry, substrate differences, lighting confounders and validation needs.
- [ ] **SCI-004 test-soil study:** Lab-method review for control groups and independently confirmed residue identity.
- [ ] **SCI-005 F3208:** Institutional licensed-standard review, no standard text/image redistribution.
- [ ] **SCI-006 G46:** Materials reviewer defines measurable pit extent/depth evidence and limitations.
- [ ] **SCI-007 G48:** Materials reviewer evaluates accelerated-test applicability, not clinical age staging.

## G. Acceptance gate

This record is complete only when all material rights, scientific provenance, and intended use are verified, all reviewers have recorded decisions, and the result is attached to the pre-existing evidence/ontology/dataset governance. **No automatic model promotion, no change to production inference, no OEM release.**
