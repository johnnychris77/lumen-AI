# Zone-Aware Training Plan (Phase 15)

**Status:** Draft for review

## Dataset fields (per image)
instrument_type · instrument_family · finding_type · severity · zone_type ·
zone_risk · retention_risk · image_angle · lighting_quality ·
supervisor_confirmed_zone · corrected_zone · corrected_severity ·
corrected_recommendation · recommended_cleaning_response · source · consent.

## Instrument coverage (examples required)
drill bits, rigid scopes, cannulated instruments, serrated forceps, laparoscopic
instruments, hinged instruments, box-lock instruments, insulated instruments —
with clean/known-good examples per zone.

## Labeling rules
- Multi-label per image; each finding tagged with its **zone**, severity, and the
  recommended cleaning response.
- Region annotation (box/mask) on the zone once CV localization is trained.
- Critical findings (blood/crack/missing component) get two-reviewer adjudication;
  only `gold` labels enter validation/test.
- Uncertain zone → `unspecified region` / `image quality insufficient`.

## Supervisor validation workflow
Supervisor review captures: AI finding correct? · AI zone correct? · corrected
zone · corrected severity · corrected recommendation · final disposition ·
rationale. Stored in `supervisor_reviews` as labeled training data and the primary
source of per-zone ground truth and FP/FN signal.

## Model evaluation
Per-zone precision/recall (did the model name the right zone?) alongside finding-
type metrics; critical-zone recall reported separately; shadow-mode only until
per-zone thresholds are met.

## Future heatmap / bounding-box roadmap
SVG anatomy maps → clickable zones → image overlays → heatmaps → segmentation
masks. Not fabricated in the pilot.

## PHI avoidance & image rights
Instrument-only imagery; EXIF stripped; de-identified filenames; opt-in retention
with recorded consent. Web images for research/prototyping only, tagged
`source=web`, excluded from validation/test, never treated as ground truth.
