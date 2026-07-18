# LPZ-DIR-006 — Annotation Guidelines

**Purpose:** per-category guidance so different reviewers produce the **same**
governed annotation for the same image. Each entry gives a definition,
inclusion/exclusion criteria, examples, borderline cases, common mistakes,
reviewer guidance, and evidence requirements. Engineering appearance only — no
clinical or diagnostic meaning is asserted.

**Universal evidence requirement:** every annotation must reference the image
region supporting it (region type + coordinates) and, where a comparison is
made, the baseline evidence used. An observation with no evidence reference is
not eligible for Ground Truth.

**Universal uncertainty rule:** when the correct class is genuinely unclear,
record `unknown_finding` or `unable_to_determine` with a comment — do **not**
force a specific class.

---

## Identification terms

### `instrument_identification` / `tray_identification` / `instrument_family`
* **Definition:** the identity/grouping of the imaged item.
* **Inclusion:** identity confirmed via barcode/UDI or governed record.
* **Exclusion:** identity guessed from appearance alone → use `unknown_finding`.
* **Examples:** confirmed UDI match; family = "ring-handled forceps".
* **Borderline:** worn/illegible marking → record what is confirmed; flag the
  rest Unknown.
* **Common mistakes:** inferring model from shape; back-filling identity.
* **Reviewer guidance:** verify identity source, not just plausibility.
* **Evidence:** identity source reference; region if a marking is cited.

### `anatomical_zone` / `lumen_region`
* **Definition:** the engineering region of the instrument being imaged
  (e.g., tip, hinge, serration, lumen interior). *Not* patient anatomy.
* **Inclusion:** the region is clearly the subject of the capture.
* **Exclusion:** region ambiguous or partially imaged → consider
  `incomplete_coverage`.
* **Evidence:** region annotation locating the zone.

---

## Acceptable-surface term

### `clean_surface`
* **Definition:** the imaged surface appears free of residual soil.
* **Inclusion:** adequate quality image; no apparent soil/material/moisture.
* **Exclusion:** poor quality image (cannot assert clean) → annotate the quality
  limitation instead; **absence of visible soil on a poor image is not evidence
  of cleanliness.**
* **Borderline:** faint marks that may be reflection → attribute to
  `image_artifact` only if clearly an artifact; else Unknown.
* **Common mistakes:** calling an under-lit or out-of-focus image "clean".
* **Reviewer guidance:** require sufficient quality before accepting `clean`.
* **Evidence:** whole-image or region reference; quality level recorded.

---

## Residual / contamination terms
(`residual_soil`, `moisture`, `staining`, `retained_foreign_material`, `fiber`,
`debris`, `obstruction`)

* **Definition:** apparent residue/material/condition visible in the image.
* **Inclusion:** a discrete, describable appearance consistent with the term.
* **Exclusion:** capture artifact (glare, dust on optics) → `image_artifact`;
  uncertain nature → `unknown_finding`.
* **Examples:** particulate lodged in serrations = `debris`; thread-like strand
  = `fiber`; darkened patch = `staining`; lumen blocked = `obstruction`.
* **Borderline:** moisture vs. glare; stain vs. shadow — use attributes and, if
  unresolved, Unknown.
* **Common mistakes:** over-claiming a specific material; merging two distinct
  findings into one annotation.
* **Reviewer guidance:** one finding per annotation; localize with a region.
* **Evidence:** region annotation; appearance attributes
  (`amount`, `extent`, `location`).

---

## Material / surface-condition terms
(`corrosion`, `pitting`, `scratches`, `cracks`)

* **Definition:** apparent surface/material condition of the instrument.
* **Inclusion:** visible condition consistent with the term.
* **Exclusion:** reflection/marking that mimics the condition → `image_artifact`
  or Unknown.
* **Borderline:** scratch vs. crack — if depth/continuity is unclear, record the
  more conservative term or Unknown with a comment.
* **Common mistakes:** diagnosing severity beyond what the image supports.
* **Reviewer guidance:** severity reflects *appearance prominence*, not risk.
* **Evidence:** region annotation; severity; attributes.

---

## Uncertainty terms

### `unknown_finding`
* **Definition:** a real finding is present but does not match a defined class.
* **Inclusion:** something is clearly there; its class is not determinable.
* **Exclusion:** the annotator simply hasn't looked carefully — look first.
* **Reviewer guidance:** Unknown is a **governed, acceptable outcome**; it feeds
  the learning loop, it is not a failure.
* **Evidence:** region + comment describing what is seen.

### `unable_to_determine`
* **Definition:** the evidence does not permit any classification (including
  clean vs. not).
* **Inclusion:** quality or coverage prevents a call.
* **Reviewer guidance:** prefer this over a low-confidence guess.

---

## Quality / artifact terms
(`image_artifact`, `poor_focus`, `poor_lighting`, `incomplete_coverage`)

* **Definition:** a property of the *capture*, not the instrument.
* **Inclusion:** the image limitation is the salient fact.
* **Exclusion:** a true instrument finding → use the finding term (and note
  quality separately if relevant).
* **Reviewer guidance:** quality terms should gate confidence and may route the
  image back to re-capture rather than to Ground Truth.
* **Evidence:** whole-image or region reference; quality level.

---

## Reviewer checklist (every annotation)
1. Is the identity confirmed (not inferred)?
2. Is the image quality adequate for the claim being made?
3. Is exactly one controlled term used per observation, with a region?
4. Is the evidence (region / baseline) referenced?
5. Is confidence recorded as **reviewer** confidence (not AI certainty)?
6. If uncertain, is Unknown / Unable to Determine used instead of a guess?
7. Are separation-of-duties rules respected (reviewer ≠ annotator)?
