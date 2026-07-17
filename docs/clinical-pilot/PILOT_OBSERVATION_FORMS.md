# Pilot Observation Forms — Phase 1

Blank instruments to be completed **during** the pilot. Print or
transcribe per site preference; completed forms attach to the pilot
evidence record. (Forms are inherently pre-pilot artifacts; the data in
them can only come from the real pilot.)

## Form A — Workflow timing (one per observed inspection)

| Field | Entry |
|---|---|
| Date / time / observer | |
| Inspection ID / LCID | |
| Instrument family / anatomy zone | |
| Step timings (mm:ss): scan/select | |
| — capture | |
| — upload (incl. retries) | |
| — baseline retrieval outcome + time | |
| — inference time | |
| — advisory review + decision | |
| — supervisor review (if any) | |
| — total wall time | |
| Interruptions (what, how long) | |

## Form B — Human factors (per participant, weekly)

Rate 1–5 and comment: ease of use · navigation · finding clarity ·
recommendation clarity · confidence display comprehension · workflow
interruption level · training adequacy. Free text: what slowed you
down; what would you change; anything you didn't trust and why.

## Form C — AI performance observation log (running)

| Date | LCID | Advisory shown | Confidence | Baseline outcome | Technician action (accept/modify/reject + reason) | Escalated? | Human final classification | Notes |
|---|---|---|---|---|---|---|---|---|

Observation only — this log makes no accuracy claim; false
positive/negative tallies are computed later only against governed
Ground Truth, and reported `insufficient_data` when counts are small.

## Form D — Safety / unexpected event (one per event)

Event type (unexpected behavior / software failure / workflow
interruption / incorrect image association / missing baseline / data
integrity / security / near miss) · date-time · reporter · what
happened (facts only) · immediate action · AI panel paused? ·
severity (SEV-1/2/3 per `PILOT_PROTOCOL.md`) · corrective action ·
closure sign-off (name, date).

## Form E — Governance spot-check (weekly, supervisor or sponsor delegate)

- [ ] Random inspection traces end-to-end: LCID → image hash → inference record (model version) → decision → audit chain verified
- [ ] Annotation/GT entries this week are versioned, none edited in place
- [ ] Baseline links used this week are ACTIVE and hash-verified
- [ ] Digital Twin timeline reflects this week's inspections
- [ ] Backup ran and verified this week (site schedule)
