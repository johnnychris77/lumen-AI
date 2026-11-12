# LumenAI Stage 2 — External Dataset Qualification Gate (LUM-SCI-003)

**Assessment date:** 2026-11-12  
**Mode:** Research audit and documentation only; no data downloaded/ingested, no production code or trained model changed.  
**Depends on:** [LUM-SCI-001](SCIENTIFIC_EVIDENCE_AND_DATASET_ACQUISITION_REGISTER.md) and [LUM-SCI-002](EXTERNAL_SCIENTIFIC_SOURCE_QUALIFICATION_TEMPLATE.md).

## Status and decision

| Source | Scientific qualification | Rights | Proposed scoped use | Stage 2 outcome |
|---|---|---|---|---|
| [SCI-001 WPI/ARL corrosion images](source-qualifications/SCI-001_WPI_CORROSION_DATASET.md) | 600 coated, deliberately scribed corrosion panels; expert ASTM D1654 scribe-creep grades 5–9 | Image archive license/third-party rights **not verified** | Corrosion image *methods research*, not a surgical rust-severity calibration set | **CONDITIONAL; REFERENCE_ONLY until licensed** |
| [SCI-002 DefectAtlas-20](source-qualifications/SCI-002_DEFECTATLAS20.md) | 13,233 general images; 2,352 coated/uncoated metal; *binary visible defect* labels | Zenodo image archive license and commercial derivative terms **not verified** | Nonclinical metal-surface defect pretraining/robustness experiments after rights approval | **CONDITIONAL; REFERENCE_ONLY until licensed** |

**No greenlight for acquisition, model training, clinical inference, clinical severity claims, or OEM commercialization.** Only published metadata and methods were reviewed.

## Why this matters

1. **Target-label mismatch:** WPI's ordinal classes are the result of *scribe-creep measurements* on coated panels, not five stages of rust oxidation on surgical instruments. DefectAtlas `defect` is not equivalent to rust/pitting/blood/bone and `no_defect` is not clinically clean.
2. **Imaging-domain mismatch:** External cameras, coated panels, consumer phones and industrial surfaces are not representative of borescope imagery on reusable surgical instruments. Hard negatives: glare, discoloration from manufacturing/cleaning, coating reflection, mineral/soap residue, shadows, and texture.
3. **Provenance risk:** `backend/app/services/ml/training_eligibility_service.py::compute_training_eligibility()` currently derives `data_provenance = "real"` if any facility provenance is not the specific “Synthetic Experimental Lab” marker. **A real external nonclinical dataset could thus be treated as “real” by a downstream component, even though it is not validated clinical data.** Do not import these sources into the training-eligible workflow until an explicit external-research-versus-real-clinical provenance policy and tests are implemented and approved. This is a documented gate, not an assertion that the current system has ingested such images.
4. **Clinical safety:** Image appearance can support suspicion but does not prove chemical identity or a patient's instrument is clean/safe. Baseline-independent AI inference is a desired capability, but only when appropriately validated.

## What must happen before experimental dataset intake

- [ ] Verified asset-specific licenses and commercial/derivative rights on archival evidence; data rights approver signs.
- [ ] Approved acquisition manifest (immutable URL/version/date, archive/CSV/image checksums, license, upload custodian, allowed use).
- [ ] Dataset inspection and statistical QA plan performed against actual downloaded bytes in authorized storage, not GitHub.
- [ ] Scientific advisor signs label interpretation and material/camera domain-fit summary.
- [ ] Clinical SPD reviewer agrees that external labels are **research-only** and do not imply clinical ground truth.
- [ ] Data-governance team approves explicit provenance classes **synthetic_experimental / external_nonclinical / laboratory_controlled / real_clinical**, and how eligibility/promotion read them.
- [ ] Existing Project Canvas/LCID and Project Lens integration evaluated for nonclinical source separation, with end-to-end leakage/provenance tests.
- [ ] Research-only evaluation plan, ablation hypotheses, expected failure modes, and independent held-out instrument-photo testing predeclared.

## Next recommended engineering work (separate, not in Stage 2)

**First unblocker is not a new CV model.** It is a small, tested provenance gate in the *existing* dataset/annotation/model registry pipeline that prevents research photographs from being categorized as real clinical Ground Truth solely because they have non-synthetic facility strings. Extend the existing provenance contracts and verify tenant, license, and ground-truth safety; do **not** fork Project Canvas or Project Lens.

After dataset rights and controls pass, run isolated experimental transfer-learning or robustness analyses and publish evidence reports. No production defect-scoring change until the independent clinical validation gate passes.

## Sources / audit record

- WPI website: https://arl.wpi.edu/corrosion_dataset/
- Yin et al., BMVC 2021 paper: https://www.bmva-archive.org.uk/bmvc/2021/assets/papers/1544.pdf
- DefectAtlas article: https://pmc.ncbi.nlm.nih.gov/articles/PMC13571519/
- Dataset DOI: https://doi.org/10.5281/zenodo.21719370
- Local network access to the Zenodo record failed in this research environment; authoritative license not independently checked. The paper itself is CC BY 4.0, which cannot be assumed to cover archive images.

**Exit criterion:** A qualified rights reviewer and independent scientific/clinical reviewers approve each source for a clearly scoped use; no inferred permission and no implicit clinical label promotion.
