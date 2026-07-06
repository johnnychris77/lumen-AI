# Continuous Improvement Tracker (v1.5)

## What it tracks
Named quality initiatives from proposal through completion:
`initiative`, `owner`, `target_date`, `status`
(`proposed`/`in_progress`/`completed`/`abandoned`), `expected_impact`,
`actual_impact`.

## Why `actual_impact` is a free-text field a human fills in
Observed impact requires human judgment about what changed and why — a raw
before/after metric delta can't distinguish "this initiative worked" from
"pass rate also improved for an unrelated reason." The tracker records the
initiative's lifecycle; a leader records the actual outcome once observed,
alongside whichever dashboard metrics they used to judge it.

## API
- `GET /api/quality/improvement-initiatives` — list (leadership only).
- `POST /api/quality/improvement-initiatives` — create.
- `PATCH /api/quality/improvement-initiatives/{id}` — update status/actual_impact.
