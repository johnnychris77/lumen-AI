# Project Vulcan — Instrument Failure Taxonomy

LumenAI AI Specialist, Section 2.

## Structure

Seven groups, 36 leaves total, declared in
`app/models/vulcan_reliability.py` (`FAILURE_TAXONOMY`):

| Group | Leaves |
|---|---|
| Cleaning-related | retained blood, retained bone, tissue, organic residue, debris, obstruction |
| Condition-related | rust, corrosion, pitting, discoloration, surface degradation, staining |
| Mechanical | crack, misalignment, loose joint, damaged hinge, damaged ratchet, damaged serration, worn cutting edge, bent component, missing component |
| Scope-specific | damaged O-ring, damaged seal, lens damage, light-post damage, sheath damage, port damage, channel damage |
| Powered/orthopedic | damaged drill flute, damaged thread, worn cutting tip, damaged hub, metal deformation |
| Insulation-related | insulation breach, peeling insulation, exposed conductor, surface nick |
| Unknown | insufficient evidence, image quality limitation, anatomy not recognized, manufacturer evaluation required |

## Mapping real detections onto the taxonomy

`vulcan_failure_taxonomy_service.classify_finding_type` maps the CV
pipeline's real `InspectionFinding.finding_type` vocabulary (`blood`, `bone`,
`corrosion`, `insulation_damage`, etc. — see
`baseline_comparison_scoring_service.CLEANING_KPIS`/`KPI_LABELS`) onto the
closest taxonomy leaf. A `finding_type` outside the known mapping
classifies as Unknown (`insufficient_evidence`) rather than guessing —
Vulcan never fabricates a finer-grained classification the CV pipeline
never actually produced.

```
GET /api/vulcan/taxonomy
```

Returns the full `{group: [leaves]}` tree for the Instrument Forensics
Workspace's failure-category filter.
