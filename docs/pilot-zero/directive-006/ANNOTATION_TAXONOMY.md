# LPZ-DIR-006 — Annotation Taxonomy (Controlled Vocabulary)

**Purpose:** a **controlled vocabulary** for annotating inspection images so
that annotations are reproducible and comparable across reviewers and over time.
Free-text is not Ground Truth. Every governed observation shall use a term from
this vocabulary; where a finding does not fit, **Unknown Finding** is the correct
governed answer.

Guiding rules:
* **"Unknown" is a valid outcome.** Annotators are never forced to classify an
  uncertain finding into a specific defect class.
* **Engineering, not clinical.** These terms describe the *image of an
  instrument*. No clinical or diagnostic meaning is asserted.
* **One controlled term per observation**, with optional appearance attributes;
  multiple observations per image are allowed, each independently reviewable.

## Category groups

### A. Identification
| Term | Applies to |
|---|---|
| `instrument_identification` | The instrument identity captured/confirmed |
| `tray_identification` | The tray/set the instrument belongs to |
| `instrument_family` | Family/type grouping (e.g., forceps, scope) |
| `anatomical_zone` | Instrument region context (engineering zone, not patient anatomy) |
| `lumen_region` | Interior/lumen region of a cannulated instrument |

### B. Clean / acceptable surface
| Term | Meaning |
|---|---|
| `clean_surface` | Surface appears free of residual soil in the image |

### C. Residual / contamination findings (engineering appearance)
| Term | Meaning |
|---|---|
| `residual_soil` | Apparent residual soil on the surface |
| `moisture` | Apparent moisture/droplets |
| `staining` | Discoloration/staining |
| `retained_foreign_material` | Apparent foreign material retained on/in the instrument |
| `fiber` | Fiber-like material |
| `debris` | Loose particulate/debris |
| `obstruction` | Apparent blockage (e.g., lumen obstruction) |

### D. Material / surface condition findings
| Term | Meaning |
|---|---|
| `corrosion` | Apparent corrosion |
| `pitting` | Surface pitting |
| `scratches` | Surface scratches |
| `cracks` | Apparent cracking |

### E. Uncertainty / non-classifiable
| Term | Meaning |
|---|---|
| `unknown_finding` | A real finding is present but does not fit a defined class |
| `unable_to_determine` | Cannot decide from the available evidence |

### F. Image quality / artifact
| Term | Meaning |
|---|---|
| `image_artifact` | Capture artifact, not a property of the instrument |
| `poor_focus` | Image too out of focus to annotate reliably |
| `poor_lighting` | Lighting inadequate/uneven for reliable annotation |
| `incomplete_coverage` | The region of interest is not fully imaged |

## Appearance attributes (optional modifiers)

Attributes refine a finding without changing its class (stored as a list;
system: `Annotation.appearance_attributes_json`). Examples: `color:dark`,
`extent:focal|diffuse`, `location:hinge|tip|lumen|serration`,
`amount:trace|moderate|heavy`. Attributes are optional and never required to
force certainty.

## Severity vocabulary (engineering)

Severity describes appearance prominence, not clinical risk. Controlled set:
`none / minimal / moderate / prominent`. Severity is optional for
identification and quality terms. System: `Annotation.severity`.

## Region types

Where a finding is spatially localized, the region is recorded with a controlled
region type (system: `REGION_TYPES`): `bounding_box`, `polygon`,
`segmentation_mask`, `point`, `whole_image_classification`. (`future_3d` is
reserved and not implemented — never fabricated.)

## Rules of use

1. **Prefer the specific term**; fall back to `unknown_finding` rather than
   forcing a wrong class.
2. **Quality first:** if the image is `poor_focus` / `poor_lighting` /
   `incomplete_coverage`, annotate the quality limitation — a finding annotated
   on an unreliable image inherits reduced confidence.
3. **Artifact vs. finding:** if a mark is a capture artifact, use
   `image_artifact`; do not record it as a surface finding.
4. **No new terms ad hoc.** New controlled terms are added only through a
   governed change to this document (versioned), never invented in-line.
5. **Evidence required:** each observation must reference the supporting region
   / baseline evidence (`ANNOTATION_GUIDELINES.md`).

## Governance note (existing system)

Today `Annotation.primary_observation` / `secondary_observation` are free
`String(80)` columns. This taxonomy is the **controlled list** a future,
separately-authorized validation layer should enforce (allow-list check on
create/update). Recording it here does not change code under this directive.
