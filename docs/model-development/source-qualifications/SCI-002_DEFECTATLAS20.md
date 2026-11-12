# LumenAI SCI-002 — DefectAtlas-20: Source Qualification

**Screening date:** 2026-11-12  
**Screening decision:** **REFERENCE_ONLY / CONDITIONAL EXPLORATORY RESEARCH CANDIDATE; NOT ACQUIRED; NO TRAINING APPROVAL**  
**Register:** [LUM-SCI-001](../SCIENTIFIC_EVIDENCE_AND_DATASET_ACQUISITION_REGISTER.md) | **Template:** [LUM-SCI-002](../EXTERNAL_SCIENTIFIC_SOURCE_QUALIFICATION_TEMPLATE.md)

## 1. Source identity and primary evidence

- **Paper:** Buettner et al. *DefectAtlas-20: A real-world image dataset for joint material and surface-condition classification*. *Data in Brief*, 2026, 68:113215. DOI: https://doi.org/10.1016/j.dib.2026.113215 .
- **Full text:** https://pmc.ncbi.nlm.nih.gov/articles/PMC13571519/ .
- **Dataset of record:** Zenodo DOI https://doi.org/10.5281/zenodo.21719370 ; record https://zenodo.org/records/21719370 .
- **Publisher paper license:** CC BY 4.0 as shown on PMC. **This does not settle the licensing of the separately downloadable dataset assets.**
- **Acquisition:** **NOT ACQUIRED.** Direct Zenodo record, exact dataset asset license, archive files/checksums, and overview.csv contents have not been independently inspected. The repository's research environment could not retrieve the Zenodo API record; a direct browser download/rights review is required.

## 2. Verified paper facts

| Property | Published evidence | LumenAI implication |
|---|---|---|
| Dataset | 13,233 RGB images over 20 material/condition classes | Cross-material visual robustness source, not a clinical surgical-instrument set |
| Images | 512×512 RGB PNG/sRGB; captured using consumer smartphones under heterogeneous real-world lighting and angles | Large domain shift vs borescope lumens, close-up metal, medical optics |
| Files described in article | `images.zip`, `overview.csv` | Manifest/CSV QA feasible *after acquisition rights cleared* |
| Metal subset | **Uncoated metal** 648 defect + 583 non-defect = **1,231**; **coated metal** 607 defect + 514 non-defect = **1,121**; combined **2,352** (1,255 defect / 1,097 non-defect) | Balanced-ish *binary visible-defect* research domain; not rust-specific |
| Labels | Image-level material and **defect/no_defect**, independently reviewed under published protocol | No segmentation, bounding boxes, rust vs pitting subtype, depth, clinical grade or laboratory-verified soil identity |
| Acquisition metadata | Published CSV schema includes image filename, class, material, defect label, width/height, camera make/model, lens, focal length, f-number, exposure, ISO, source format | Useful for stratification and lighting/device robustness research |
| Generalization | Different objects, backgrounds and cameras; review/quality filters applied | Evaluate shortcut learning; cannot assume absence of repeated object/session examples without record-level audit |

Source of numbers and schema: paper's specifications table, Table 1 and Table 3 (https://pmc.ncbi.nlm.nih.gov/articles/PMC13571519/).

## 3. Licensing, data-rights and asset audit — STOP

**Unresolved:** exact Zenodo *dataset* license, license version, image copyright and third-party contributors' commercial ML-training rights, derivative-model terms, redistribution restrictions, completeness of rights/attribution notice, and record/asset checksums. The paper's CC BY 4.0 license alone does not prove the downloadable image archive has identical rights.

**Decision:** NOT AUTHORIZED to import, train on or distribute these images or derivative image data until the exact dataset record/license and permissions have been captured and approved. Public metadata and the published article can be studied and cited.

## 4. Intended-use fit and explicit exclusions

| Task | Preliminary decision |
|---|---|
| Published descriptive research and experimental hypothesis | **REFERENCE_ONLY now** |
| External-image *metal surface defect* binary research | **CONDITIONAL** after rights + QA + scientific review |
| Non-clinical robustness study across cameras, glare, coatings and backgrounds | **CONDITIONAL** after rights + QA |
| Direct mapping to clinical *rust* or *pitting* detector | **NOT SUPPORTED** by label meanings |
| Infer rust degree, pit depth, cleaning failure, blood/bone/tissue residue | **NOT SUPPORTED** |
| Produce release/pass/fail recommendation or OEM defect rates | **PROHIBITED** without new real instrument ground truth + independent validation |

The word `no_defect` means *no visible defect under this dataset's labeling protocol*, **not** clinically clean, sterile or safe.

## 5. Planned metadata/data QA (only after permission)

1. Retrieve the Zenodo record's versioned API metadata, Rights/license identifier, file list, checksum and upload dates; archive authoritative evidence.
2. Validate `overview.csv` schema against paper's Table 3; confirm **13,233** rows and **2,352 metal images** exactly from data, not inferred counts.
3. Verify archive checksums, safe extraction, formats/dimensions/colors, duplicates/near-duplicates, blank/incorrect files, metadata mismatch and label completeness.
4. Check for related photos of the same object or acquisition session; construct **grouped splits** if groups exist; if provenance cannot support independent groups, explicitly downgrade validation claims.
5. Validate material-type and defect/no-defect labels in a blinded human sample; record inter-reviewer agreement and confounder/lighting concerns.
6. Define experiments in Project Lens **as experimental non-clinical**; do not silently convert material labels into LumenAI's clinical observation taxonomy.
7. If a future scientific reviewer proposes labeling a subset for `probable_corrosion_like_degradation`, collect new clinical/material reference evidence and independent adjudication before any such mapping.

## 6. Reuse existing LumenAI infrastructure

- Project Canvas: rights-approved intake, LCID, retention, existing annotation/review/adjudication, provenance.
- Project Lens: external research only after license clearance, with explicit `external_nonclinical` provenance in the research model card; it must not be mislabeled `real_clinical_ground_truth`.
- Keep approved clinical data and external research data separated in experiments. The currently coded training eligibility's provenance determination should be independently reviewed before any external data are registered, because this public dataset could otherwise be misinterpreted as ordinary “real” images.
- Existing model validation/promotion and human disposition controls remain binding. No direct OEM intelligence publication.

## 7. Signoffs and decisions

| Check | Status |
|---|---|
| Paper/publication identity | **PASS** |
| Published dataset sizes and class distribution | **PASS (paper only)** |
| Data ZIP, CSV and checksums validated | **PENDING** |
| Exact Zenodo asset license & commercial rights | **PENDING** |
| Clinical/SPD domain-fit review | **PENDING** |
| ML/metadata reviewer | **PENDING** |
| Privacy/right-to-train reviewer | **PENDING** |
| Project Canvas dataset eligibility | **NOT STARTED** |
| Project Lens model training | **BLOCKED** |
| Clinical model or OEM data release | **NOT AUTHORIZED** |

**Next evidence:** Zenodo record + exact archive rights; acquisition and QA report; metadata schema validation; blinded review and approved experimental protocol.
