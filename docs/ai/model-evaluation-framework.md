# LumenAI Model Evaluation Framework

**Status:** Draft for review
**Implementation:** `backend/app/analytics/model_evaluation.py`
(tests: `backend/tests/test_model_evaluation.py`)

How any inspection model — the current **pilot Baseline Comparison Scoring
Model** or a future computer-vision model — is measured before it is allowed to
influence a disposition.

> No production diagnostic-accuracy claim is made by computing these metrics.
> They are validation tooling; all output stays advisory.

---

## Metrics (per KPI class)

For each class (present vs. absent), against `gold` ground-truth labels:

- **Precision** — of the instruments flagged for a finding, how many truly had it.
- **Recall (sensitivity)** — of the instruments that truly had a finding, how
  many were caught. **Primary metric for critical classes.**
- **False-positive rate (FPR)** — clean instruments wrongly flagged (drives
  unnecessary reprocessing).
- **False-negative rate (FNR)** — contaminated/damaged instruments missed (the
  patient-safety risk).
- **F1 / accuracy** — summary balance and overall correctness.
- **Confusion matrix** — TP / FP / TN / FN counts.

## Human-reviewer agreement

- **Percent agreement** and **Cohen's kappa** between the model and a human
  reviewer (chance-corrected). Used both for inter-rater reliability during
  labeling and for model-vs-reviewer comparison in shadow mode.

## Promotion gates (proposed, to be ratified)

A model is **not** promoted out of shadow mode until, on the in-domain held-out
test set:

- Critical classes (blood, bioburden, tissue, organic residue, crack, missing
  component): **recall ≥ target** (high), FNR below the agreed ceiling.
- FPR within an operationally acceptable band (limit needless reprocessing).
- Probabilities are **calibrated** (a "70%" means ~70%).
- Reviewer agreement (kappa) at or above the agreed threshold.
- No instrument leakage between train and test.

## Process

1. **Shadow mode:** run the candidate model alongside the active engine; log
   predictions and reviewer dispositions; compute the metrics above. Do **not**
   change dispositions.
2. **Review:** quality/IP sign-off on the metrics, per class, per instrument type.
3. **Staged enable:** turn on per instrument type where gates pass; keep others
   in shadow.
4. **Monitor:** ongoing drift + calibration checks; reviewer corrections feed
   back as labels (active learning).

## API surface

```python
from app.analytics.model_evaluation import (
    binary_metrics, per_class_report, confusion_matrix, reviewer_agreement,
)

report = per_class_report(y_true_by_kpi, y_pred_by_kpi)   # precision/recall/FPR/FNR/...
agree  = reviewer_agreement(model_labels, reviewer_labels) # %, Cohen's kappa
```
