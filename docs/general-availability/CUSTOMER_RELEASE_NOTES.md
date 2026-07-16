# LumenAI Release Notes — Version 1.0 (Pilot Program)

**Important:** LumenAI Version 1.0 is being made available as a **limited,
disclosed pilot program**, not a General Availability release. This
document describes exactly what is and is not included, so that any
participating facility has an accurate picture before agreeing to
participate.

## What LumenAI does in this release

LumenAI supports sterile processing inspection workflows with:

- **Advisory Mode**: an AI-generated recommendation is shown to the
  technician after image analysis, alongside its confidence, an evidence
  summary, and a clear statement that it is a recommendation, not a
  definitive conclusion. The technician and, subsequently, the supervisor
  retain full authority to accept, modify, or reject it.
- **Full audit trail**: every recommendation interaction, disposition
  action, and safety event is logged with a tamper-evident, hash-chained
  audit record.
- **Human oversight throughout**: no recommendation is ever auto-approved,
  auto-promoted, or acted on without an explicit human decision.

## What LumenAI does not yet do

- **The current inspection-scoring pipeline is a deterministic baseline,
  not a fully trained computer-vision model.** It supports `debris` and
  `corrosion` findings; all other categories are explicitly marked
  not-evaluated rather than guessed. See `KNOWN_LIMITATIONS.md` for the
  complete, honest list.
- **This release has not yet completed a real-world pilot at any
  facility.** Everything described above has been built and tested in a
  software-engineering sense; it has not yet been operated with real
  patients' instrument data at a real facility. Your facility's
  participation, if you choose to proceed, would be among the first.
- **No regulatory clearance is claimed.** LumenAI does not claim FDA
  clearance or any other regulatory approval for any finding it presents.

## What participating in this pilot involves

- A defined pilot duration and success criteria, agreed in advance and
  recorded per facility.
- Your facility's clinical, quality, and IT leads participating in a
  scheduled Clinical Review Board review of pilot progress.
- Structured feedback collection from your technicians, supervisors, and
  quality staff.
- A data governance agreement (BAA/DPA) specific to your facility, executed
  before any real patient-adjacent data is processed.

## Support during the pilot

See `SUPPORT_HANDBOOK.md` for how to reach support, severity definitions,
and escalation paths during the pilot period.

## What's next

At the conclusion of a successful pilot — with real safety, performance,
and adoption evidence, not test data — LumenAI will be considered for
broader General Availability. See `docs/general-availability/
GENERAL_AVAILABILITY_REPORT.md` for the specific criteria that decision
depends on.
