# Project Council — Dissent Registry

Section 6 of the sprint brief.

## What gets recorded

Every specialist whose recommended action falls outside the consensus
majority gets a `CouncilDissentRecord`
(`council_dissent_service.record_dissent`):

- `dissenting_specialist`
- `disputed_conclusion` -- the majority position being disputed
- `evidence_supporting_dissent` -- the dissenter's own evidence
- `risk_if_ignored` -- the dissenter's `significance` field
- `additional_evidence_required` -- the dissenter's `evidence_limitations`
- `proposed_alternative_action` -- the dissenter's `recommended_action`
- `escalation_level` -- `"safety_critical"` if the dissenter is a
  safety/evidence specialist (Sentinel-X, Veritas) reporting `urgency=
  "urgent"`, otherwise `"standard"`

## Always displayed prominently

Dissent is never hidden from the final report. Every case-detail view
(`GET /api/council/cases/{id}`) includes the full dissent list alongside
the consensus outcome, and `council_agreement_map_service.
build_agreement_map` separately calls out `dissenting_specialists` next
to the consensus position, so a leader reading the case summary sees the
disagreement in the same view as the recommendation -- exactly the shape
of the brief's own worked example:

> Council majority: Proceed with increased monitoring.
> Sentinel-X dissent: Moderate corrosion in a high-risk drill-bit flute
> may represent progressive integrity failure.
> Veritas limitation: Current image quality is insufficient to
> distinguish corrosion from lighting artifact.
> Council outcome: INSUFFICIENT_EVIDENCE.
> Next action: Capture a new flute image and obtain supervisor review.
