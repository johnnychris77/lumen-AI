# Stage 5D — Expert-Reviewed Ground-Truth & Reviewer Protocol

Status: **protocol only — no ground truth has been established.** Reuses the
existing Project Canvas annotation model (`Annotation` / `AnnotationVersion`) and
the Stage 5C scientific-evidence contract. It introduces **no** second annotation
database and **no** new clinical taxonomy.

## 1. Four separated truth layers

Ground truth is recorded in four strictly separated layers (Stage 5C contract):

1. **AI-generated anomaly** — research-only, uncalibrated spatial signal.
2. **Human visual assessment** — a reviewer's opinion; not confirmation.
3. **Laboratory-confirmed physical condition** — independently verified material
   identity/condition (EDS/XRD/microscopy/assay/composition).
4. **Clinical disposition** — **never produced in research.**

> Laboratory confirmation is **never** inferred from model confidence, color, or
> image appearance (`infer_identity_from_rgb` raises). A confirmed material identity
> comes only from verified lab evidence linked by an authorized reviewer
> (`is_lab_confirmed` + `ReviewerAuthorization`), with image/specimen matching.

## 2. Predefined annotation protocol

Fixed **before** any image is annotated:

- **Label space** — the Stage 5C evidence categories (corrosion-like, localized
  pitting, blood-like residue, bone/tissue-like particle, verified-normal surface,
  confounding surface) mapped onto the existing observation taxonomy. No new class.
- **Label types** — image-level label **and**, where applicable, spatial labels
  (pixel masks / bounding regions) verified against image dimensions, orientation,
  coordinate space, and annotation version (`verify_mask_alignment` / `verify_bbox`).
- **Decision rules** — what evidence a reviewer must see for each category; when to
  mark `unknown` / `insufficient_image` rather than guess; confounder handling.
- **Modality rules** — external-camera vs borescope annotation conventions.

## 3. Qualified reviewers & adjudication

- **Two independent qualified reviewers** annotate each image blind to each other
  and to the model output (double review — reused from Project Canvas).
- **Disagreements** are adjudicated by a predefined rule (third senior reviewer or
  consensus conference); the adjudication is recorded, not silently overwritten.
- Reviewer identity, role, and authorization are recorded; only an authenticated
  reviewer holding the `scientific_reviewer` role may link laboratory evidence
  (Stage 5D `ReviewerAuthorization`).
- Ground-truth status is read from the authoritative Annotation DB
  (`ground_truth_status == ACTIVE`); a missing label is `unlabeled`, never `normal`.

## 4. Laboratory evidence where scientifically necessary

For corrosion, pitting, blood-like, and bone/tissue-like classes, image labels are
**insufficient on their own**; an independent laboratory measurement / material
identification is required and recorded in the Stage 5C `LaboratoryEvidence`
contract, capturing:

- image id + **SHA-256**, instrument id, specimen id, imaging session
- material type + instrument anatomy; source laboratory, study, **reference method**
- independently-verified identity/condition; measurement value + **units** +
  **uncertainty** (number, `unknown`, or `None` — never a fabricated 0)
- mask/spatial-annotation reference; reviewer id, verification status, approval ref
- data rights, retention, provenance; explicit limitations + unresolved ambiguities

`validate_evidence` enforces category-appropriate reference methods and
measurements before any identity is recorded.

## 5. Recorded identity fields (per image)

Physical instrument id · specimen id · facility · study/lab batch · imaging device ·
acquisition session · image hash · anatomy zone · view · modality. These fields are
the grouping keys the evaluation protocol uses to prevent leakage.

## 6. Outstanding (BLOCKED until provided)

1. Qualified, credentialed reviewers + a signed annotation protocol version.
2. Laboratory partner(s) and methods for the independent reference measurements.
3. Adjudication panel and recorded inter-reviewer agreement (e.g. Cohen's/Fleiss' κ)
   on a pilot set before the main annotation campaign.
4. Governed storage of lab evidence linked to the retained images.

**No reviewed ground truth exists yet.** This protocol is the readiness blueprint.
