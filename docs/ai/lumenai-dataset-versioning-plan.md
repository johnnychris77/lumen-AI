# LumenAI Dataset Versioning Plan

**Status:** Draft for review
**Purpose:** Version the labeled image data that will train and validate a real
image-based inspection model, and govern how supervisor feedback becomes ground
truth.

> ⚠️ Advisory pilot. No production diagnostic-accuracy or FDA/regulatory claims.
> Every model output remains `human_review_required: true`.

---

## Dataset versions

### Dataset v1 — pilot bootstrap
- ~100 labeled lumen images.
- Manufacturer/vendor **baseline reference images** for the covered instruments.
- **Inspection images** captured in-workflow (browser capture / station kiosk).
- **Supervisor labels**: agreement/disagreement on the AI clinical review, with
  rationale, captured via the supervisor-review endpoint.
- Goal: establish the labeling pipeline and a first calibration set. Not for
  accuracy claims.

### Dataset v2 — breadth
- 500+ labeled images.
- **Multiple manufacturers** and instrument families.
- **Multiple contamination types** (blood, tissue, organic residue, debris,
  bone) at graded severities.
- **Varied lighting and capture devices** (different borescopes, UVC grabbers,
  station vs per-workstation).
- Goal: class balance + severity spread sufficient to begin shadow-mode
  evaluation of a candidate model.

### Dataset v3 — real-world generalization
- **Multi-hospital** images (consented sites).
- **Multi-device capture** across borescope makes/models.
- **Real-world variation**: soil load, wear, reprocessing states.
- **Longitudinal instrument tracking** (same instrument over time) for
  degradation/drift modeling.
- Goal: in-domain generalization; promotion gated on held-out multi-site metrics.

---

## Labeling process
- Multi-label per image (an image may carry several findings) with per-finding
  severity using the published scales.
- Instrument type recorded; images labeled against the **approved baseline** so
  normal machining/weld marks are not mislabeled.
- **Supervisor feedback** (agree / partially agree / disagree + rationale +
  override) is captured on real inspections and joined to the image as a label
  signal.
- Critical classes (blood, crack, missing component) require **two reviewers**
  with adjudication before a label is promoted to `gold`.
- `uncertain` is a valid label and routes to supervisor review; excluded from
  the positive training set until resolved.

## Supervisor validation
1. Technician/labeler applies labels + regions.
2. SPD supervisor/SME reviews; critical classes use the two-reviewer rule.
3. Adjudicated labels marked `gold`; only `gold` enters validation/test sets.
4. Every label change is audit-logged (actor, timestamp, before/after).

## Model evaluation plan
- Metrics via `app/analytics/model_evaluation.py`: precision, recall, FPR/FNR,
  confusion matrix, reviewer agreement (Cohen's kappa).
- Critical contamination/damage classes optimize for **recall** and are reported
  separately.
- Candidate models run in **shadow mode** (no disposition change) until they pass
  the promotion thresholds on a held-out, multi-instrument test set.

## False positive / false negative review
- Every shadow-mode **false negative** on a critical class is re-reviewed and
  added to the training set.
- **False positives** that would cause unnecessary reprocessing are tracked and
  thresholds tuned per class, not globally.
- Supervisor `disagree` / `override` events are a primary source of FP/FN signal.

## Dataset governance
- Each version is immutable once released; changes create a new version.
- `source` tracked per image (in-workflow / baseline / demo / web).
- Train/test split keeps **no instrument in both** sets (prevents leakage).
- Access-controlled storage; retention is opt-in (`RETAIN_INSPECTION_IMAGES`)
  with recorded consent.

## PHI avoidance
- Images are of **instruments only** — no patients, faces, names, MRNs, or
  documents in frame; reject any image containing PHI.
- EXIF/metadata stripped on ingest; de-identified filenames
  (`{instrument_type}_{seq}`).
- Only SHA-256 hashes are stored unless retention is explicitly enabled.

## Image rights and consent guidance
- In-workflow images require site retention **consent** before storage.
- Public web images may be used **only for research/prototyping**, never as
  validated clinical training data unless rights and labeling are confirmed;
  tag `source=web` and exclude from validation/test.
- Never treat web-sourced labels as ground truth for accuracy claims.
