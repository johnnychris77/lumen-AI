# Pilot Validation Protocol — Phase 18

## Purpose

Move LumenAI from technical readiness to evidence-backed operational
validation by running AI-assisted inspection alongside trained Sterile
Processing Department (SPD) supervisors at a live pilot site, and by
capturing measurable agreement and safety metrics against their review.

This protocol governs a single pilot validation cohort. It does not, on its
own, constitute regulatory clearance or a clinical study; see
`docs/validation/pilot-go-no-go-criteria.md` for the readiness gate this
protocol feeds into.

## Pilot Site

- One designated SPD pilot site per validation run, tracked by `tenant_id` /
  `facility_id`.
- Site must already have baseline image capture in place for at least one
  instrument family before enrollment (see Baseline Requirements below).
- Site coordinator is the single point of contact for supervisor scheduling
  and escalations.

## Participating Users

| Role | Responsibility |
|---|---|
| SPD Technician | Captures inspection images through the normal LumenAI workflow. |
| SPD Supervisor | Reviews AI output, confirms or corrects the finding, zone, severity, and final disposition — the ground-truth source. |
| SPD Manager / Admin | Monitors the pilot dashboard, safety review queue, and approves the go/no-go recommendation. |
| Quality/Safety Reviewer | Adjudicates any case in the safety review queue that a supervisor escalates. |

No patient-facing staff and no PHI-handling roles are part of this pilot.

## Instrument Types

Cohort should span at minimum:
- Rigid hand instruments (forceps, hemostats, scissors, rongeurs)
- Rotary/orthopedic instruments (drills, reamers, burrs)
- Rigid and flexible endoscopic instruments (scopes, cannulas)
- Electrosurgical instruments (insulated devices)

Custom/uncommon instrument types are recorded as free text (`instrument_family`)
rather than forced into a fixed enum, consistent with the rest of the platform.

## Image Capture Process

1. Technician performs the standard LumenAI inspection capture flow.
2. The system runs AI inference and records `ai_prediction` and
   `ai_confidence` for each finding.
3. Image and inference results are queued for supervisor review — no
   disposition is finalized on AI output alone.

No PHI or patient identifiers may appear in the image, file name, or any
associated metadata. Images are validated against the platform's existing
no-PHI intake checks before being added to the pilot cohort.

## Baseline Requirements

- Where a manufacturer or site-submitted baseline exists for the instrument,
  the case is tagged `baseline_source` (`vendor_baseline` or `site_capture`)
  and `has_baseline = true`.
- Cases without an available baseline are still eligible for the pilot but
  are flagged in the safety review queue as `missing_baseline_cases`.

## Supervisor Review Process

For every pilot inspection, the supervisor records (see
`docs/validation/ground-truth-review-workflow.md` for the full workflow):

- Whether they agree with the AI's finding (`supervisor_finding`)
- A corrected zone if the AI's zone assignment was wrong
  (`supervisor_zone_correction`)
- The final disposition (pass / reprocess / quarantine / escalate)
- A rationale for any disagreement or override

The system derives the ground-truth confusion-matrix label (`TP`/`TN`/`FP`/`FN`/
`inconclusive`) from `ai_prediction` and `supervisor_finding` — this label is
never accepted directly from a client, so it cannot be manually set to a
more favorable value.

## Success Criteria

- 100 pilot lumen images reviewed, baseline-linked where possible.
- Supervisor agreement rate at or above the threshold defined in
  `docs/validation/pilot-go-no-go-criteria.md`.
- Critical finding (blood, tissue, organic residue, crack, missing
  component) false-negative rate at or below the safety threshold.
- Zone assignment reliable enough that the safety queue's
  `missing_required_zones` count trends toward zero over the pilot.

## Safety Guardrails

- Every AI output requires human (supervisor) review before any clinical or
  operational disposition — enforced by `human_review_required: true` on
  every validation payload.
- No output ever asserts causation. Findings are described as "potential
  association," "possible contributing factor," or "quality review
  recommended."
- Every case entering the safety review queue is visible to the SPD manager
  role; critical missed findings are surfaced first.
- No FDA clearance or regulatory approval is claimed anywhere in pilot
  materials, dashboards, or generated reports.
- Hospital and reviewer identities are never included in any
  cross-hospital or aggregate reporting derived from this pilot.
