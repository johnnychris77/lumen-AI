# Root Cause Intelligence (v1.5)

## What it does
Lets a supervisor categorize a finding by its probable root cause and trends
recurring causes across the tenant.

## Why root cause is always human-assigned
The engine never infers *why* a finding occurred — only a human reviewing
the instrument and context can make that judgment. Auto-inferring a cause
from a finding type alone would be a fabricated causal claim, which the
platform's governance rules (`docs/architecture/*`, CLAUDE.md) explicitly
forbid: "never claim causation."

## Accepted vocabulary (`app/models/root_cause.py::ROOT_CAUSES`)
- `incomplete_manual_cleaning`
- `improper_brushing`
- `improper_flushing`
- `missed_inspection_zone`
- `poor_lighting`
- `image_quality`
- `instrument_damage`
- `manufacturer_wear`
- `unknown` — a legitimate, honest choice when the cause isn't identifiable
  at review time; not every finding needs a forced categorization.

## API
- `POST /api/quality/root-cause` — assign a root cause to a specific finding
  on a specific inspection (leadership only).
- `GET /api/quality/root-cause-trends` — recurring causes overall and by
  finding type, for any authenticated role.
