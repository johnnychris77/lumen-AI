# P4.4 — Scientific Metric Methodology Decision Package (RGI-10)

**Status:** DECISION PACKAGE for an authorized scientific-methodology decision. **The existing
implementation is preserved** (`research/lens_vision/calibration.py::dice_iou` currently scores
empty∩empty as `0.0`) and is **NOT changed** by this document. No scientific performance claim
is made, and no benchmark result is altered (all real benchmarks remain **BLOCKED** pending
governed data and a licensed checkpoint, so there are no published pixel metrics to change).

Scope: the per-image Dice and IoU convention for the four prediction/ground-truth mask cases,
and whether a change would affect benchmark interpretation (which, if so, requires an
authorized decision before adoption).

---

## 1. The four cases and current behaviour

For a predicted anomaly mask `P` and reference mask `G` (both binary grids):

| # | Case | Current `dice_iou` result | Is the result scientifically defensible? |
|---|------|---------------------------|------------------------------------------|
| 1 | **P empty, G empty** (correct "no anomaly") | Dice = 0.0, IoU = 0.0 (`pred+gt == 0`) | **No** — a correct normal prediction is scored as a total miss |
| 2 | P non-empty, G empty (false-positive region on a normal) | Dice = 0.0, IoU = 0.0 | Yes — no overlap with an empty truth is correctly 0 |
| 3 | P empty, G non-empty (missed a real anomaly) | Dice = 0.0, IoU = 0.0 | Yes — a complete miss is correctly 0 |
| 4 | both non-empty | 2·|P∩G| / (|P|+|G|); |P∩G|/|P∪G| | Yes — standard |

Only **case 1** is contested. Cases 2–4 are standard and correct.

## 2. Established conventions for case 1 (empty∩empty)

| Convention | Case-1 score | Used by / rationale | Effect on mean |
|---|---|---|---|
| **(a) Score 1.0** (perfect agreement) | Dice=1.0, IoU=1.0 | Common in medical-imaging segmentation libraries (e.g., MONAI's `ignore_empty=False`): a correct empty prediction is perfect agreement | **Inflates** mean over normal-heavy cohorts |
| **(b) Exclude from aggregate** | undefined / skipped | Common default (e.g., MONAI `ignore_empty=True`): empty-reference images contribute no pixel-overlap signal | Mean computed only over images with a real ground-truth region (no inflation/deflation) |
| **(c) Score 0.0** (current) | Dice=0.0, IoU=0.0 | Penalizes a correct normal as a failure | **Deflates** mean over normal-heavy cohorts (a bias) |

## 3. Assessment

- **Per-image vs. aggregate.** Per-image, case 1 is a degenerate (0/0) denominator; the
  convention is a *definition*, not a measurement. The aggregate (mean Dice/IoU) is where the
  choice biases the reported number.
- **Empty-case handling.** Current (c) treats a correct no-anomaly localization as a total
  failure — a **systematic downward bias** that grows with the fraction of normal images in the
  test split. For a sterile-instrument cohort (mostly normal), this bias can be large.
- **Reproducibility.** All three conventions are deterministic; the choice does not affect
  reproducibility, only interpretation.
- **Historical / published-result comparability.** No LumenAI pixel metrics have been published
  (benchmarks BLOCKED), so there is **no backward-compatibility constraint** today — the
  decision can be made cleanly before any first publication. Against *external* benchmarks,
  comparability requires matching their convention (most report (a) or (b), not (c)).
- **Bias by convention.** (a) inflates on normal-heavy cohorts; (c) deflates; **(b) is
  bias-neutral** for the pixel-overlap question because it measures overlap only where a
  reference region exists, and pairs naturally with a separate image-level normal/abnormal
  metric (AUROC/AP) for the "did we correctly call it normal?" question.

## 4. Recommendation (not yet authorized — implementation preserved)

**Recommended policy:** adopt **(b) exclude empty∩empty from the pixel aggregate**, and report
`n_masked_images` alongside mean Dice/IoU (the experiment already returns `n_masked_images`), so
the pixel metric measures localization quality only where a ground-truth region exists; the
normal-vs-abnormal decision is covered by the separate image-level metrics. If comparability
with a specific external benchmark that uses (a) is required, adopt (a) **for that comparison
only** and label it explicitly.

**Rationale:** (b) removes the current downward bias without inflating, is the common library
default, and cleanly separates "localized the anomaly well" from "correctly called it normal."

## 5. Why this is preserved, not changed now
Per the P4.3/P4.4 brief, changing the empty∩empty convention alters the interpretation of any
reported mean Dice/IoU, so it requires an **authorized scientific-methodology decision**. Until
that decision is recorded:
- `dice_iou` behaviour is **unchanged** (still 0.0 for empty∩empty), documented in code.
- No pixel metrics are published (benchmarks BLOCKED), so nothing is retroactively altered.
- **RGI-10 remains OPEN** and is release-blocking for any published pixel-localization metric.

A recorded decision (option a/b/c) by an authorized methodology owner closes RGI-10; only then
should `dice_iou`/the aggregate be updated to match, with the regression tests adjusted in the
same change.
