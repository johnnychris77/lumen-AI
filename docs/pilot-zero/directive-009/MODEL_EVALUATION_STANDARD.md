# LPZ-DIR-009 — Model Evaluation Standard

**Purpose:** define the **methodology** for evaluating candidate vision models so
results are honest, reproducible, and independently testable. This standard
defines *how* to measure — it does **not** establish deployment thresholds and
makes **no** diagnostic-performance claim.

Guardrail: evaluation produces evidence for human judgement. It does not authorize
deployment, and no metric here is a clinical-performance guarantee. Where data is
insufficient, report "insufficient data" — never a fabricated figure.

## Evaluation methodology (metrics)

Evaluate on the **sealed test partition** of the frozen dataset version (Directive
008), never on training/validation data. Report, as applicable to the model
family:

| Metric | What it measures |
|---|---|
| **Precision** | Correctness of positive predictions |
| **Recall** | Coverage of actual positives |
| **Sensitivity** | = recall for the positive class |
| **Specificity** | Correctness on actual negatives |
| **F1 Score** | Harmonic mean of precision/recall |
| **Calibration** | Agreement of predicted confidence with observed frequency |
| **Confusion Matrix** | Full class-by-class breakdown |
| **ROC** | TPR vs. FPR across thresholds |
| **AUC** | Area under the ROC curve |
| **False Positive Analysis** | Characterization of FP cases |
| **False Negative Analysis** | Characterization of FN cases |
| **Performance by Instrument Family** | Stratified performance |
| **Performance by Manufacturer** | Stratified performance |
| **Performance by Image Quality** | Stratified performance |
| **Unknown Classification Rate** | How often the model abstains |

## Methodology rules

1. **Sealed test only.** Metrics are computed on held-out test data disjoint from
   train/validation (leakage-safe partition, Directive 008).
2. **Stratified reporting.** Report by instrument family, manufacturer, and image
   quality — aggregate numbers alone are insufficient.
3. **Honest uncertainty.** Report the Unknown/abstention rate; a model that abstains
   appropriately is more trustworthy than one that forces a class.
4. **Calibration matters.** Report calibration, not just discrimination — confidence
   must mean something.
5. **Error analysis required.** Characterize false positives and false negatives
   (what, where, why) — not just counts.
6. **Reproducible.** Evaluation is deterministic given the model version + test
   partition + protocol; the evaluation run is recorded and re-runnable.
7. **No thresholds here.** This standard does **not** set pass/deploy thresholds.
   Promotion gates (`MODEL_PROMOTION_STANDARD.md`) reference evaluation *evidence*;
   any future clinical threshold is a separate, explicitly-authorized decision.
8. **No performance claim.** Reported metrics describe the candidate on this test
   set; they are not a clinical or diagnostic guarantee.

## Evaluation record (expected outcome)

Each evaluated model version produces a recorded evaluation package: the metric set
(or "insufficient data"), stratified breakdowns, calibration report, confusion
matrix, and false-positive/false-negative analyses — reproducible from the model
version + sealed test partition + protocol.

## Governance note (existing system)

`ml.evaluation` computes precision/recall/specificity/sensitivity/F1, PR/ROC
signals, and calibration in pure Python; `ml.error_analysis` characterizes errors;
`ModelRegistryEntry` stores `evaluation_metrics`, `calibration_report`, and
`error_analysis_report`. Governance additions recorded for a future authorized
change: pin an **evaluation version** and the exact test-partition reference into
each evaluation record, and standardize the stratified-by-family/manufacturer/
quality breakdown as a required output. No code is changed under this directive.
