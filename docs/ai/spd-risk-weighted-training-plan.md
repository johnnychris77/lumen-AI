# SPD Risk-Weighted Training Dataset Plan

**Status:** Draft for review
**Scope:** Training/validation data for the SPD risk-weighted inspection model
that will eventually replace the pilot **Baseline Comparison Scoring Model**.

> ⚠️ No production diagnostic-accuracy claims. No FDA/regulatory claims. Every
> output stays advisory (`human_review_required: true`). The current scoring is a
> deterministic placeholder, not pixel-level computer vision.

This plan complements `docs/ai/model-training-dataset-plan.md` and focuses on the
**SPD risk weighting** the patch introduced: critical contamination and
structural damage must drive disposition far more aggressively than cosmetic
discoloration or normal wear.

---

## 1. Classes and example imagery to collect

Capture instrument-only images (no PHI) across these classes. Severity bands
mirror the scoring engine.

| Class | Severity bands | Example imagery to source |
|---|---|---|
| Blood | none / trace / visible / heavy | dried and fresh blood in lumens, hinges, box locks, serrations |
| Tissue | none / low / moderate / high | soft-tissue / protein residue in channels and jaws |
| Organic residue | none / low / moderate / high | mixed biological soil, dried fluids, films |
| Bone | none / low / moderate / high | calcified fragments / bone dust in cannulated shafts |
| Debris | none / low / moderate / high | particulate, lint, brush bristles, packaging fragments |
| Rust | none / surface / moderate / heavy | surface bloom → pitted heavy rust on stainless |
| Corrosion | none / minor / moderate / severe | galvanic/pitting corrosion, stained welds |
| Discoloration | none / minor / moderate / severe | heat tint, detergent staining, passivation color |
| Damage (crack / missing component / insulation) | none / cosmetic wear / functional concern / structural failure | cracked jaws, missing screws/inserts, breached insulation |

Each class needs a **clean / known-good** counterpart for the same instrument
type so normal machining/weld marks are not mislabeled as defects.

## 2. Labeling rules

- **Multi-label:** one image may carry several findings (e.g. rust + debris).
- **Per-finding severity** using the bands above. The label drives the SPD risk
  tier: blood visible/heavy, heavy rust, severe corrosion, crack, missing
  component, insulation damage → **critical**; debris, bone, moderate rust /
  corrosion, pitting → **high**; minor discoloration / cosmetic wear → **low**.
- **No standalone "bioburden" label.** Bioburden is a clinical umbrella term;
  label the concrete contaminants (blood, bone, tissue, organic residue, debris)
  and let the Overall Cleaning Assessment summarize them.
- **Region annotation** (box/mask) for localizable findings — feeds the future
  evidence map.
- **Two-reviewer rule** for critical classes (blood, crack, missing component);
  disagreements go to adjudication. Only adjudicated `gold` labels enter
  validation/test sets.
- **Uncertain** is a valid label — routes to supervisor review, excluded from the
  positive training set until resolved.
- **No causation / clinical-outcome labels** — label what is visible, not harm.

## 3. Image quality rules

- In focus, instrument fills the frame, even diffuse lighting (avoid blown
  highlights / deep shadow that hide or fake residue).
- Consistent scale reference where possible; capture lumens/channels with
  adequate illumination.
- Multiple angles for 3-D findings (hinges, box locks, cannulated shafts).
- Reject images with motion blur, heavy glare, or anything obscuring the finding.
- **No PHI in frame** — no patients, faces, names, MRNs, labels, or paperwork.
  Strip EXIF/metadata on ingest (the retention store does this automatically).

## 4. Supervisor validation process

1. Technician/labeler applies labels + severity + regions.
2. SPD supervisor / SME reviews each labeled image; critical classes require the
   two-reviewer + adjudication rule.
3. Adjudicated labels are marked `gold`; only `gold` enters validation/test.
4. All label changes are audit-logged (actor, timestamp, before/after).

## 5. Minimum dataset targets (pilot start)

Production targets are higher; these are minimums to begin training.

| Class group | Min positives per class |
|---|---|
| Clean / known-good | 500 (spread across instrument types) |
| Blood, tissue, organic residue | 300 each |
| Bone, debris | 200 each |
| Rust, corrosion (per severity band) | 150 per band |
| Discoloration | 150 |
| Crack, missing component, insulation damage | 200 each (oversample/augment — rare + critical) |

Augmentation (rotation, lighting, crop, mild blur) is allowed to balance classes
but **never** to fabricate a defect that isn't there.

## 6. False positive / false negative review process

- Compute per-class precision, recall, FPR, FNR with
  `app/analytics/model_evaluation.py`.
- **Critical contamination/damage classes optimize for recall** — a missed
  contaminated/cracked instrument is the costly error. Report critical-class
  recall separately and gate promotion on it.
- Maintain a **false-negative review queue**: every missed critical finding in
  shadow mode is re-reviewed by a supervisor and added to the training set.
- Track **false positives** that would cause unnecessary reprocessing; tune
  thresholds per class rather than globally.
- A model is promoted only after passing thresholds in **shadow mode**, and even
  then output remains advisory.

## 7. Web image usage caution

- **Do not** scrape clinical/patient images from the web.
- Public web images of instruments may be used **only for research and
  prototyping**, never as validated clinical training data unless image **rights
  and labeling are confirmed**.
- Tag every web-sourced image `source=web`, exclude it from validation/test sets,
  and never treat web labels as ground truth for accuracy claims.
- Production metrics are computed only on in-domain, consented data.
