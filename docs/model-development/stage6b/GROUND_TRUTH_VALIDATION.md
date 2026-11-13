# Stage 6B — Scientifically-Validated Ground Truth

Status: **protocol only — no validated ground truth exists.** Reuses the existing
Project Canvas annotation/adjudication mechanisms and the Stage 5C evidence contract.

## 1. Qualified reviewers + independent adjudication (reused)

- Each image is annotated by **two qualified reviewers**, blind to each other and to
  the model output.
- Disagreements go to a predefined **adjudication** (third senior reviewer / consensus
  conference); the adjudication and the **unresolved discrepancies are preserved**,
  never silently overwritten.
- **Reviewer agreement is measured and reported** (e.g. Cohen's κ for two reviewers,
  Fleiss' κ for more; per-category), on a pilot set before the main campaign and on the
  full set.

## 2. Evidence linked to the correct physical entity

Every laboratory-evidence record is linked to the correct **physical specimen,
acquisition session, image (SHA-256), and verified spatial region** — enforced by the
Stage 5D `link_observation` + `ReviewerAuthorization` (authenticated reviewer whose
identity matches the verifier; anomaly image-hash/specimen must match the evidence).

## 3. Visual appearance vs confirmed material identity

The four Stage 5C layers stay separate: AI anomaly / human visual assessment /
laboratory-confirmed identity / clinical disposition. **Visual appearance never becomes
a confirmed identity.** Specifically:

| Claim | Required confirming evidence |
|---|---|
| **Corrosion** | Material **or** dimensional evidence (EDS/XRD/SEM-EDS material characterization, or validated surface metrology) |
| **Pitting** | Dimensional evidence (optical/SEM microscopy or profilometry; pit geometry) |
| **Blood-/bone-/tissue-like residue** | Relevant **analytical confirmation** (protein/hemoglobin assay, composition/FTIR, histology) **or** a documented **known reference specimen / simulant** with stated provenance |
| **Confounder (benign)** | Independent review / reference standard |

A residue claim backed only by appearance is recorded as *visual-only, unconfirmed*; it
is never promoted to a confirmed identity.

## 4. Recorded identity fields (per image)

Physical instrument ID · specimen ID · facility · study batch · imaging device ·
acquisition session · image hash · anatomy zone · view · modality — these are the
grouping keys the leakage-safe evaluation uses (Stage 6B comprehensive grouping).

## 5. Outstanding (BLOCKED)

1. Qualified, credentialed reviewers + a signed annotation protocol version.
2. Laboratory partner(s) + methods per category; or documented reference specimens/
   simulants for residue classes.
3. Recorded inter-reviewer agreement on a pilot set.
4. Governed storage of evidence linked to retained images with reviewer attribution.

No validated ground truth exists yet; this is the readiness blueprint.
