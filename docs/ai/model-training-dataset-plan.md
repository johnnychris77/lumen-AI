# LumenAI Model Training Dataset Plan

**Status:** Draft for review
**Scope:** Dataset to train/validate a real image-based inspection model that
replaces the current **pilot Baseline Comparison Scoring Model**.

> ⚠️ No production diagnostic-accuracy claims. No FDA/regulatory claims. Every
> output stays advisory (`human_review_required: true`).

---

## 1. Image categories (classes to label)

**Contamination**
- blood
- bone
- tissue
- bioburden
- debris
- other organic residue

**Instrument condition**
- rust — severity: none / surface / moderate / heavy
- discoloration — severity: none / minor / moderate / severe
- corrosion — severity: none / minor / moderate / severe
- pitting (wear) — none / minor / moderate / severe
- crack — present / absent (+ region)
- insulation damage — present / absent (+ region)
- missing component — present / absent

**Identification (no learning needed — decode/match)**
- barcode, QR/UDI, KeyDot: detected + decoded value

Plus a **clean / known-good** class (no findings) — essential as the negative
class so the model learns "normal."

## 2. Labeling rules

- **Multi-label:** an image may carry several findings (e.g. rust + debris).
- **Per-finding severity** using the published scales above. Blood:
  none/trace/visible/heavy.
- **Region annotation** (bounding box or mask) for localizable findings (rust,
  corrosion, residue, crack, missing component) — enables the evidence map.
- **Instrument type** recorded per image; label against the **approved baseline**
  for that instrument so "normal weld/machining marks" are not mislabeled as
  defects.
- **Two-label rule for critical classes** (blood, crack, missing component):
  each must be labeled by **two reviewers**; disagreements go to adjudication.
- **Uncertain** is a valid label — do not force a class. Uncertain images route
  to supervisor review and are excluded from the training positive set until
  resolved.
- **No causation/clinical-outcome labels** — we label what is visible, not harm.

## 3. Minimum image count per class (to start)

These are **pilot minimums** to begin training; production targets are higher.

| Class group | Min positives per class | Notes |
|---|---|---|
| Clean / known-good | 500 | Negative anchor; spread across instrument types |
| Blood, bioburden, tissue, organic residue | 300 each | Critical contamination — prioritize |
| Bone, debris | 200 each | |
| Rust, corrosion (per severity level) | 150 per severity | Need spread across none→heavy |
| Discoloration, pitting | 150 each | |
| Crack, missing component, insulation damage | 200 each | Rare + critical — oversample/augment |

Augmentation (rotation, lighting, crop, mild blur) is allowed to balance classes
but **never** to fabricate a defect that isn't there.

## 4. Supervisor review process

1. Technician/labeler applies labels + regions.
2. **SPD supervisor / SME** reviews each labeled image; critical classes require
   the two-reviewer + adjudication rule (§2).
3. Adjudicated labels are marked `gold`; only `gold` labels enter the
   validation/test sets.
4. All label changes are audit-logged (actor, timestamp, before/after) —
   consistent with the platform's audit requirements.

## 5. Quality-control process

- **Inter-rater reliability:** track Cohen's kappa between reviewers per class
  (see `app/analytics/model_evaluation.reviewer_agreement`); investigate classes
  below an agreed threshold.
- **Held-out test set** per instrument type; **no instrument** appears in both
  train and test (prevent leakage).
- **Label audits:** periodic re-review of a random sample; correct drift.
- **Class balance + calibration** checks before any model is promoted.
- Critical classes optimize for **recall** (a missed contamination/crack is the
  costly error) and are reported separately.

## 6. PHI avoidance

- Images are of **instruments only** — no patients, faces, names, MRNs, or
  documents in frame. Reject any image containing PHI.
- Strip EXIF/metadata on ingest; store no patient identifiers.
- The platform currently stores **only SHA-256 hashes**. Training requires a
  **separate, access-controlled image store** with explicit retention consent —
  a prerequisite, not a default.
- De-identify file names (`{instrument_type}_{seq}` — no facility/patient data).

## 7. Acceptable image sources

- **Primary:** images captured in-workflow on consented sites, with the
  retention controls above.
- **Reference/known-good:** manufacturer/vendor baseline reference images.
- **SME-curated demo sets** created specifically for labeling (no PHI).
- Phantom/test instruments deliberately soiled or aged for rare classes (with
  documented provenance).

## 8. Web image usage caution

- **Do not** scrape clinical/patient images from the web.
- General web images of instruments may be used **only** for early
  bootstrapping/augmentation, and only if license permits, clearly tagged
  `source=web` and **excluded from validation/test sets** (they are not
  representative of the deployment's cameras, lighting, or instruments).
- Never treat web-sourced labels as ground truth for accuracy claims.
- Track `source` on every image; production metrics are computed on in-domain,
  consented data only.

## 9. How this feeds the model

The labeled set trains the multi-label detector + severity heads described in
`docs/computer-vision-plan.md`. Validation uses
`app/analytics/model_evaluation.py` (precision, recall, FPR/FNR, confusion
matrix, reviewer agreement). A model is promoted only after passing the
validation thresholds in **shadow mode**, and even then output remains advisory.
