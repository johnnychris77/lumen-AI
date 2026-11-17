# P4.5 — Scientific Methodology Approval Package (RGI-10)

**Status:** DECISION-READY PROPOSAL for an authorized scientific-methodology reviewer. **The
metric implementation is NOT changed** by this document (`research/lens_vision/calibration.py::dice_iou`
still scores empty∩empty as `0.0`). No scientific performance claim is made; no benchmark result
is altered (all real benchmarks remain **BLOCKED** — no published pixel metrics exist). RGI-10
remains **OPEN** until an authorized reviewer records a decision in §4.

## 1. Four-case Dice / IoU behaviour

For predicted mask `P`, reference mask `G` (binary):

| # | Case | Current result | Mathematically | Contested? |
|---|------|----------------|----------------|------------|
| 1 | **P empty, G empty** (correct normal) | Dice 0.0 / IoU 0.0 (`|P|+|G|=0`) | 0/0 — a *definition*, not a measurement | **YES** |
| 2 | P non-empty, G empty (FP on normal) | 0.0 / 0.0 | no overlap with empty truth → 0 correct | No |
| 3 | P empty, G non-empty (missed anomaly) | 0.0 / 0.0 | complete miss → 0 correct | No |
| 4 | both non-empty | 2|P∩G|/(|P|+|G|) ; |P∩G|/|P∪G| | standard | No |

Only **case 1** is contested.

## 2. Published conventions for case 1
- **(a) Score 1.0** — correct empty prediction = perfect agreement (e.g. MONAI `ignore_empty=False`). Inflates the mean on normal-heavy cohorts.
- **(b) Exclude from aggregate** — empty-reference images contribute no overlap signal (e.g. MONAI `ignore_empty=True`, common default). Bias-neutral for the overlap question.
- **(c) Score 0.0 (current)** — penalizes a correct normal as total failure. Deflates the mean on normal-heavy cohorts.

## 3. Evaluation
1. **Mathematical interpretation:** case 1 is 0/0; the value is a chosen convention. (c) assigns the *worst* score to a *correct* outcome — a logical mismatch.
2. **Published conventions:** most libraries/papers use (a) or (b); (c) is uncommon.
3. **Per-image vs aggregate:** the choice only affects the aggregate mean; per-image it is degenerate. Pair pixel overlap (where a region exists) with a separate image-level normal/abnormal metric (AUROC/AP).
4. **Impact on model rankings:** (c) systematically rewards models that *over-predict* regions on normal images (they avoid the 0.0 penalty by making `P` non-empty→ but then case 2 gives 0.0 too) — net, (c) biases ranking by the normal fraction of the test split, which differs across cohorts → **rankings not comparable across cohorts**. (b) removes this coupling.
5. **Historical benchmark compatibility:** **none to break** — no LumenAI pixel metrics published (BLOCKED). Against external benchmarks, comparability requires matching *their* convention (usually a or b).
6. **Reproducibility:** all three are deterministic; choice does not affect reproducibility, only interpretation.
7. **Reporting transparency:** whichever is chosen must be stated explicitly, and `n_masked_images` (already returned by the experiment) reported alongside mean Dice/IoU.

## 4. Recommendation (not yet authorized — implementation preserved)
**Recommend (b): exclude empty∩empty from the pixel aggregate**, report `n_masked_images`
beside mean Dice/IoU, and carry the normal-vs-abnormal decision in the separate image-level
metrics. If comparability with a specific external benchmark that uses (a) is required, adopt
(a) **for that comparison only**, labelled explicitly. **Justification:** removes the current
downward, cohort-dependent bias of (c) without inflating; matches the common library default;
keeps "localized well" separate from "correctly called normal".

**On adoption:** when an authorized reviewer records (a/b/c) below, update `dice_iou`/the
aggregate to match **and adjust the regression tests in the same change**; until then, behaviour
is unchanged and RGI-10 stays OPEN and blocking for any published pixel-localization metric.

## 5. Unsigned scientific-methodology reviewer record (DO NOT prepopulate)
| Field | Value |
|---|---|
| Reviewer name / org / role | |
| Qualification / authority | |
| Scope reviewed (metric convention for pixel Dice/IoU) | |
| Decision (adopt a / b / c / other) | |
| Rationale | |
| Reporting requirements (e.g. report `n_masked_images`) | |
| Conditions | |
| Date | |
| Signature or authenticated approval reference | |

*No decision is issued here. RGI-10 remains OPEN until a qualified scientific-methodology
authority records a decision; the implementation is not changed without it.*
