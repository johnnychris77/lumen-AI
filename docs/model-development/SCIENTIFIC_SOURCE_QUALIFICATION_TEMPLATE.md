# LumenAI External Scientific Source Qualification Form (LUM-SCI-002)

**Stage:** Research and rights screening only. **Decision is not a clinical model approval.**

Copy this file to a new immutable source record for each version of an external dataset, article, microscopy image collection, or laboratory reference. Use the [source register](SCIENTIFIC_EVIDENCE_AND_DATASET_ACQUISITION_REGISTER.md) as the index.

## A. Identity and traceability

| Field | Value |
|---|---|
| Source ID / version | TBD |
| Title / contributor / institution | TBD |
| Primary URL, DOI, repository record | TBD |
| Retrieval date (UTC), acquisition operator | TBD |
| Publication date / dataset version date | TBD |
| Asset inventory and file counts | TBD |
| Publisher checksum / independently calculated SHA-256 | TBD |
| Acquisition manifest path and immutable evidence location | TBD |

## B. Rights and privacy — hard stop before downloading for ingestion

| Check | Evidence / reviewer / date | Outcome (pass/fail/pending) |
|---|---|---|
| Exact dataset/image copyright owner verified | | PENDING |
| **Asset license** (distinct from article or website license) captured | | PENDING |
| Commercial model training and derivative model rights permitted | | PENDING |
| Redistribution and sublicensing restrictions understood | | PENDING |
| Institutional, lab, patient, and third-party permissions verified if applicable | | PENDING |
| PHI and personally identifying metadata screened | | PENDING |
| Intended facility/tenant, cross-tenant, and manufacturer-sharing permissions recorded | | PENDING |
| License terms/attribution and revocation requirements retained | | PENDING |
| Legal/data-governance approver signs off on authorized use | | PENDING |

**No ingestion or training authorization when any mandatory row is PENDING or FAIL.**

## C. Scientific and clinical suitability

- Source specimen: substrate/alloy/coating/finish, biological or artificial test soil, instrument family/model, anatomy, image modality, magnification, lighting, exposure/time and environmental conditions.
- Original labeling and truth: expert grading, blind independent review, microbiological/chemical assay, microscopy or metrology, uncertainty, label definitions, known confounders, class counts.
- Imaging fit: external photograph vs lumen borescope, focal length, resolution, color calibration, glare, motion blur, occlusion, view/zone metadata.
- Suitability score: relevance to target finding, generalizability, negative examples, likely shortcut features, duplication and leakage risks.
- **Approved task (select separately):** literature reference / exploratory visual evaluation / experimental pretraining / governed clinical training / sealed clinical validation / manufacturer intelligence.
- Explicit exclusions and unvalidated claims: TBD.
- Experimental / clinical performance thresholds and predeclared held-out groups: TBD.

## D. Proposed Canvas and Lens integration

Use existing components only:
1. Ingest via retained-image consent/rights checks and Project Canvas dataset ingestion.
2. Assign existing LCID, dataset version, physical-instrument identity and source provenance.
3. Route to independent annotation, blinded secondary review, adjudication, Ground Truth promotion.
4. Document training/evaluation split at **instrument, imaging session, and facility** levels; preserve sealed independent test data.
5. Record experimental vs real provenance in Project Lens model card, registry and release gates.
6. Clinical findings and instrument dispositions always require separately validated model behavior and qualified human oversight.
7. External-source commercial reuse rights are **not** the same as a hospital's rights to license its inspection data to OEMs.

Do not introduce a second dataset registry, taxonomy, AI model promotion ladder or manufacturer evidence store.

## E. Signed disposition

| Field | Decision |
|---|---|
| Scientific reviewer (name/date) | PENDING |
| Clinical SPD reviewer (name/date) | PENDING |
| Data-rights/privacy reviewer (name/date) | PENDING |
| ML/data-quality reviewer (name/date) | PENDING |
| Final use category | REJECT / REFERENCE_ONLY / RESEARCH_ONLY / EXPERIMENTAL_DATA_APPROVED / REAL_CLINICAL_GROUND_TRUTH_ELIGIBLE |
| Approver/date/evidence location | PENDING |
| Conditions and exclusions | TBD |
| Recheck/expiry | TBD |

**Default: REFERENCE_ONLY pending positive, documented authorization.** Documented approval in this form is a gate for research acquisition, not an automatic app-side data rights or clinical approval status.
