# LumenAI SCI-001 — WPI/ARL Corrosion Dataset: Source Qualification

**Screening date:** 2026-11-12  
**Screening decision:** **REFERENCE_ONLY / CONDITIONAL RESEARCH CANDIDATE; NOT ACQUIRED; NO TRAINING APPROVAL**  
**Source record:** [LUM-SCI-001](../SCIENTIFIC_EVIDENCE_AND_DATASET_ACQUISITION_REGISTER.md)  
**Qualification standard:** [LUM-SCI-002](../EXTERNAL_SCIENTIFIC_SOURCE_QUALIFICATION_TEMPLATE.md)

## 1. Identity and primary evidence

- **Title:** *Corrosion Image Data Set for Automating Scientific Assessment of Materials*.
- **Authors:** Biao Yin et al.; WPI and U.S. Army Research Laboratory.
- **Publication:** BMVC 2021, DOI: [10.5244/C.35.417](https://doi.org/10.5244/C.35.417).
- **Publisher paper:** https://www.bmva-archive.org.uk/bmvc/2021/assets/papers/1544.pdf .
- **Dataset landing page:** https://arl.wpi.edu/corrosion_dataset/ .
- **Public author research code:** https://github.com/Josephyiin/BMVC21--Corrosion-Image-Data-Set-for-Automating-Scientific-Assessment-of-MaterialsCorrosion-Image .
- **Dataset acquisition:** **NOT ACQUIRED**. The site's linked download archive, included README, specific file license, full metadata/labels, and hashes have not been inspected.

## 2. Confirmed facts versus assumptions

| Field | Verified from published source | Qualification implication |
|---|---|---|
| Size | 600 RGB JPG images, 512×512 pixels | Small external research set, not suitable by itself for clinical validation |
| Ground truth | Expert corrosion ratings for coated laboratory panels | Useful *ordinal materials-science* benchmark only |
| Class distribution | Rating **5, 6, 7, 8, 9**, **120 images per class** | Distinct five-class task; do **not** infer clinical rust stages |
| Meaning of ratings | ASTM **D1654** scribe-creep corrosion width from deliberate cuts; ratings decrease with increasing creep; source rating scale spans 0–10 but released set contains only 5–9 | Neither biological contamination nor corrosion/pit **depth**; not a stainless-surgical-instrument severity scale |
| Test articles | Approximately 4×6-inch **coated** panels (topcoat, primer, pretreatment, substrate), with one/two scribes | Significant domain gap from uncoated/polished stainless surgical instruments and borescope lumen views |
| Environments | Accelerated static salt fog (ASTM B117) and cyclic corrosion experiments | Conditions and timepoints do **not** yield a natural chronological rust-color sequence |
| Confounders | Water stains, coating/background colors, scribe patterns, noise and tiny corrosion regions | Control against models learning scribe geometry, coatings or lighting |
| Model outcomes | Paper reports accuracy up to ~0.83 in tested classification setting | Published benchmark result; **not** LumenAI performance |

Sources: primary BMVC paper sections 3–4, figures 1–4 and dataset website (links above). Do not reproduce the copyrighted ASTM standard from the paper.

## 3. Asset rights and provenance gate — STOP

1. WPI website and author's linked code page display **MIT License © 2021 WPI** and citation instructions.
2. **Not yet independently verified:** whether the **downloaded dataset images and ratings**, their derivatives, and commercial model-training/reuse are unambiguously covered by the license attached to that download; whether any third-party materials are excluded.
3. Archive README, archive checksums and any dataset-specific notices have **not** been retrieved.
4. No signed legal/data-governance approval exists for LumenAI reuse.

**Decision: FAIL CLOSED / RIGHTS PENDING.** The public page's MIT statement is encouraging but not sufficient for our commercial-rights evidence chain. Request source-specific confirmation from WPI if the archive terms are ambiguous.

**Contact:** gr-wpi-arl-dsrg@wpi.edu (public project page). No outreach has been sent.

## 4. Intended LumenAI use and explicit exclusions

| Use case | Preliminary assessment |
|---|---|
| Read and cite methods; learn expert grading methodology | **Allowed as a research reference** |
| Define corrosion-area/texture and negative-confounder research hypotheses | **Suitable in principle** |
| Experiment with self-supervised representations on external image data | **Conditional: rights and QA approval first; experimental only** |
| Train direct clinical *rust degree* estimator from rating labels | **NOT SUITABLE**: rating concerns coated-panel scribe creep |
| Train blood/bone/tissue/pitting diagnosis or borescope lumen localization | **NOT SUITABLE / NO LABELS** |
| Assert clinical clean/safe, instrument-pass or OEM device-failure rates | **PROHIBITED** |

Anatomy view, surgical alloy, true instrument identity, microstructure, pitting depth, lab chemistry, and external-to-borescope image transfer are not supplied as verified clinical labels.

## 5. Dataset QA plan after license verification

1. Record exact archive URL, publication/version, rights notices, immutable archive SHA-256 and acquisition operator/date in a controlled source manifest (not the application database).
2. Inventory files, decode and hash all images, validate dimensions/color modes, and confirm **600 total / 120 per class, ratings 5–9**; record failures rather than silently excluding samples.
3. Resolve duplicate/near-duplicate images and potential **same physical panel / longitudinal timepoint** leakage. If original specimen identifiers cannot be obtained, do not claim specimen-independent validation.
4. Have a materials expert review sample labels, scribe geometry, grade interpretation, and color/finish confounders before approving an *experimental* model task.
5. Test permitted non-clinical experiments separately; document measured metrics and subgroup failure analysis.
6. Never map its rating to `probable_corrosion_like_degradation` severity labels or clinical recommendations without **new instrument-specific expert annotation and independent validation**.
7. Keep model artifacts at Experimental and outside clinical inference and manufacturer intelligence. Project Canvas/LCID intake only after all usage-rights/retention/privacy gates pass.

## 6. Review signatures / pending evidence

| Gate | Status |
|---|---|
| Primary publication identity | **PASS** |
| Rating definition and class inventory (paper-level) | **PASS** |
| Archive bytes / README / checksum | **PENDING** |
| Dataset image and derivative commercial license | **PENDING** |
| Materials-science reviewer | **PENDING** |
| Clinical/SPD reviewer | **PENDING** |
| Data rights & privacy reviewer | **PENDING** |
| Project Canvas/ML governance review | **PENDING** |
| Project Lens experiment approval | **BLOCKED** |
| Clinical model or OEM export authorization | **NOT AUTHORIZED** |

**Next evidence needed:** source archive license/README; verified inventory; written rights clarification if needed; materials-specialist review.
