# Project Veritas — Collaboration With Other Agents

LumenAI AI Specialist, Section 16.

## No specialist may overwrite Veritas evidence findings

Every function in `veritas_specialist_collaboration_service.py` reads
another specialist's real, already-persisted output by reference and
returns a Veritas-specific opinion in a separate dict — it never mutates or
merges into the source. The orchestrator preserves separate agent
conclusions by construction.

## Aegis

`evidence_support_for_aegis(aegis_conclusion, veritas_assessment)` — does
Veritas's evidence readiness support Aegis's process conclusion? Aegis's
own signal (`vulcan_aegis_integration_service.compute_process_variation_
signal`'s output) is referenced verbatim, never edited.

## Vulcan

`evidence_support_for_vulcan(veritas_assessments)` — confirms instrument-
condition progression comparisons used comparable images/anatomy zones/
baseline versions, flagging when the assessments being compared resolved
against different baselines.

## Sage

`evidence_support_for_sage(sage_image_entry, veritas_training_entry)` —
cross-checks Sage's own education-image curation
(`SageEducationImageEntry.phi_review_status`/`supervisor_validated`)
against Veritas's independent training-dataset gate
(`VeritasTrainingDatasetEntry.dataset_status`), so education content only
uses approved, correctly labeled, rights-cleared images.

## Clinical Reasoning Agent

`evidence_support_for_clinical_reasoning(veritas_assessment)` — packages
evidence limitations and readiness status for the reasoning engine to
consider before finalizing a recommendation.

## API

```
GET /api/veritas/collaboration/clinical-reasoning/{assessment_id}
```
