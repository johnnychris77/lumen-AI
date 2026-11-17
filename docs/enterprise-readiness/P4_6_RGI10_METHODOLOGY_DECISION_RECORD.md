# P4.6 — RGI-10 Scientific-Methodology Decision Record (Dice/IoU empty-case convention)

**Status:** DECISION-READY RECORD for a qualified, authorized scientific-methodology reviewer.
**The metric implementation is NOT changed by this document.** `research/lens_vision/calibration.py::dice_iou`
still scores empty∩empty as `0.0`; no benchmark result is altered (all real benchmarks remain
**BLOCKED**; no published pixel metrics exist). RGI-10 remains **OPEN** until an authorized reviewer
records a decision in §4. This record carries forward the analysis in
`P4_5_SCIENTIFIC_METHODOLOGY_APPROVAL.md` and states the **recommended** decision for the synthetic
pilot, **subject to qualified scientific review**.

---

## 1. The contested case

For predicted mask `P` and binary reference mask `G`:

| # | Case | Current result | Status |
|---|------|----------------|--------|
| 1 | **P empty, G empty** (correct normal) | Dice 0.0 / IoU 0.0 (`|P|+|G|=0`, i.e. 0/0) | **Contested** — a *convention*, not a measurement |
| 2 | P non-empty, G empty (FP on normal) | 0.0 / 0.0 | Not contested |
| 3 | P empty, G non-empty (missed anomaly) | 0.0 / 0.0 | Not contested |
| 4 | both non-empty | standard overlap formulas | Not contested |

## 2. Published conventions for case 1
- **(a) Score 1.0** — a correct empty prediction counts as perfect agreement (e.g. MONAI
  `ignore_empty=False`). *Inflates* the mean on normal-heavy cohorts.
- **(b) Exclude from the aggregate** — empty-reference images carry no overlap signal (e.g. MONAI
  `ignore_empty=True`, a common default). Bias-neutral for the overlap question.
- **(c) Score 0.0 (current)** — penalizes a correct normal as total failure. *Deflates* the mean on
  normal-heavy cohorts and makes cross-cohort rankings depend on the normal fraction.

## 3. Recommendation (for the synthetic pilot — subject to qualified scientific review)

**Recommended decision: adopt (b) — exclude empty-ground-truth / empty-prediction (empty∩empty)
cases from the aggregate Dice/IoU**, and report `n_masked_images` (already returned by the
experiment) alongside the mean Dice/IoU, carrying the normal-vs-abnormal signal in a **separate
image-level metric** (AUROC/AP).

**Justification:**
1. Case 1 is mathematically `0/0`; (c) assigns the *worst* score to a *correct* outcome — a logical
   mismatch.
2. (b) matches the common library default and removes the cohort-dependent downward bias of (c)
   without the upward inflation of (a).
3. It keeps "localized the region well" (pixel overlap, where a region exists) separate from
   "correctly called normal" (image-level) — the scientifically cleaner decomposition.
4. **Synthetic-pilot relevance:** a synthetic cohort's normal/abnormal mix is an authoring choice, so
   convention (c) would make synthetic-run aggregates especially sensitive to that mix; (b) makes the
   pixel metric interpretable regardless of the synthetic normal fraction.

**Conditions on adoption:** whichever convention is authorized, it must be **stated explicitly**
beside every reported metric, with `n_masked_images`. If comparability with a specific external
benchmark that uses (a) is ever required, adopt (a) **for that comparison only**, labelled
explicitly.

**Implementation note (not performed here):** when an authorized reviewer records (a/b/c), update
`dice_iou` / the aggregation to match **and adjust the regression tests in the same change**. Until
then behaviour is unchanged and RGI-10 stays **OPEN and blocking** for any published pixel-
localization metric. No synthetic metric may be reported as a performance figure before this
decision and the RGI-02 reviewer framework are recorded.

## 4. Unsigned scientific-methodology reviewer record (DO NOT prepopulate)
| Field | Value |
|---|---|
| Reviewer name / org / role | |
| Qualification / authority (metrics expertise) | |
| Scope reviewed (pixel Dice/IoU empty-case convention) | |
| Decision (adopt a / b / c / other) | |
| Rationale | |
| Reporting requirements (e.g. report `n_masked_images`, state convention) | |
| Conditions | |
| Date | |
| Signature or authenticated approval reference | |

*No decision is issued here. RGI-10 remains OPEN until a qualified scientific-methodology authority
records a decision; the implementation is not changed without it. The recommendation above is an
engineering/assurance proposal, not an authorized scientific decision.*
