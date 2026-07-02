# Pilot Validation Protocol (Phase 18)

Structured plan to validate LumenAI in a real SPD workflow using pilot-site
images, supervisor labels, and measurable clinical performance.

## Pilot site
A single sterile processing department (SPD) or ambulatory/endoscopy center
running the LumenAI pilot. One tenant; no cross-tenant data.

## Participating users
- **Technicians** — capture images and run inspections.
- **SPD supervisors / managers** — record ground-truth reviews (the label source).
- **Admin** — configures baselines, reviews the validation dashboard and report.

## Instrument types
Anatomy-aware families in scope: rigid scope, flexible endoscope, drill bit,
Kerrison/rongeur, scissors, needle holder, laparoscopic, general forceps. Lumened
instruments are prioritized for the initial cohort.

## Image capture process
Borescope or phone capture (per existing capture workflow), EXIF-stripped, de-identified.
No PHI, no patient identifiers, no faces/documents in frame.

## Baseline requirements
Where possible each inspected instrument type has an approved manufacturer or
vendor baseline so the AI produces a baseline-comparison score. Missing-baseline
cases are flagged (they route to the safety queue).

## Supervisor review process
For every reviewed inspection the supervisor records: AI prediction, whether the
AI flagged a finding, whether they confirm a finding, zone correction, finding
type, final disposition, and rationale. This produces a ground-truth label
(see `ground-truth-review-workflow.md`).

## Success criteria
- Supervisor agreement ≥ 80%.
- Safety-critical false-negative rate ≤ 5% (blood/tissue/organic residue/crack/
  missing component).
- No unresolved critical safety issue.
- Documented limitations.

## Safety guardrails
- AI is **decision-support only**; a supervisor owns every disposition.
- `human_review_required: true` on all outputs.
- Zone assignment is pilot logic, not CV segmentation.
- No FDA/regulatory claims.
- False negatives and high-confidence disagreements are surfaced in the safety
  review queue for mandatory human follow-up.
