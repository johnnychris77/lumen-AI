# Project Sage — Competency Taxonomy

LumenAI AI Specialist, Section 2.

## Structure

Seven domains, 52 leaves total, declared in
`app/models/sage_education.py` (`COMPETENCY_TAXONOMY`):

| Domain | Leaves |
|---|---|
| Instrument identification | manufacturer recognition, instrument-family recognition, model recognition, instrument differentiation, rigid scope vs flexible endoscope, powered vs manual instrument |
| Anatomy recognition | serrations, grooves, box locks, hinges, ratchets, drill-bit flutes, threaded regions, lumens, cannulated channels, O-ring areas, scope ports, insulation edges, handle seams |
| Inspection technique | visual inspection, magnification, borescope inspection, articulation and actuation, image capture, lighting, focus, angle selection, inspection coverage |
| Contamination recognition | blood, bone, tissue, organic residue, debris |
| Condition recognition | rust, corrosion, discoloration, pitting, crack, wear, missing components, insulation damage |
| Clinical decision support | reclean, repeat inspection, supervisor review, repair evaluation, manufacturer evaluation, remove from service |
| Documentation | inspection evidence, supervisor notes, baseline selection, anatomy-zone labeling, final disposition |

## Mapping real signal onto the taxonomy

`sage_competency_taxonomy_service.py` maps real, already-recorded signal onto
taxonomy leaves rather than fabricating new tracking:

- `finding_type` strings (the CV pipeline's real vocabulary) map onto the
  contamination/condition leaves.
- `SupervisorReview` boolean-correction fields (`zone_correct`,
  `instrument_family_correct`, `image_view_correct`) map onto anatomy/
  instrument-identification/technique leaves.

```
GET /api/sage/taxonomy
```
