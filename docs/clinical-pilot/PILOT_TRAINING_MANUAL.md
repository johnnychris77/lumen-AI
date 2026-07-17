# Pilot Training Manual — Phase 1

Training is a go-live precondition (`PILOT_READINESS_ASSESSMENT.md`
DoD). No users have been trained yet — no users exist. This manual is
the curriculum to deliver on site, built from the guides in this
directory and the full walkthrough in
`docs/pilot/pilot-user-training-guide.md`.

## Session 1 — All pilot participants (45 min)

* What LumenAI is in this pilot: an **advisory, experimental** system
  being observed — and what it is not (not validated, not a decision
  maker, not a replacement for any procedure step).
* The one rule: LumenAI advises; humans decide.
* The safety invariants in plain language (contamination can never show
  PASS; unavailable is never PASS; every disposition is human).
* Data governance in plain language: permanent image IDs, append-only
  audit, no PHI in imaging metadata, how pilot data may (and may not)
  be used.

## Session 2 — Technicians (60 min, hands-on at the bench)

* Walkthrough of `TECHNICIAN_GUIDE.md` steps 1–7 on the dry-run rig.
* Practice: good capture vs. quality-flagged capture; a
  `no_approved_baseline` case; an `AI ANALYSIS UNAVAILABLE` case; an
  escalation.
* Each technician performs 3 supervised end-to-end dry-run inspections
  (test targets, not clinical instruments).
* Filling the observation and timing forms.

## Session 3 — Supervisors (60 min)

* Walkthrough of `SUPERVISOR_GUIDE.md`: queue types, completing a
  review, what your entries become (provenance).
* Automation-bias and distrust signals to watch for.
* Pause authority, mandatory pause triggers, restart procedure.
* Safety-event classification and the reporting path.

## Session 4 — Site IT + sponsor (30 min)

* Environment overview per `PILOT_SITE_GUIDE.md`; where backups,
  monitoring, and alerts live; who is paged and when.
* The stop conditions and the amendment process.

## Competency check (required before first clinical use)

Each participant: completes their role's dry-run tasks without
assistance; states the one rule and the never-PASS invariants
unprompted; locates the escalation and event-reporting paths. Record
completion per person in the training log attached to the site record.
