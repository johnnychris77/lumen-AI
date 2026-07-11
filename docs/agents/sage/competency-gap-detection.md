# Project Sage — Competency Gap Detection

LumenAI AI Specialist, Section 3.

## Never a single-error conclusion

`sage_gap_detection_service.py` requires at least two occurrences
(`_MIN_OCCURRENCES = 2`) of the same real pattern before it ever produces a
gap. One isolated supervisor correction never becomes a competency gap.

## Real evidence sources

- **Missed anatomy zones** — `SupervisorReview.missing_zone_correct == False`
  grouped by `corrected_missing_zone` (repeated serration/O-ring/drill-bit
  flute omissions).
- **Anatomy label errors** — `SupervisorReview.zone_correct == False` grouped
  by `instrument_family`, so rigid-scope and flexible-endoscope gaps remain
  distinct rows, never merged.
- **Finding confusion** (e.g. blood vs. rust) — both members of a known
  confusable pair (`_CONFUSION_PAIRS`) are each individually corrected for
  the same technician.
- **Low inspection coverage** — repeated `Inspection.coverage_pct` below 70%.
- **Image-capture issues** — repeated `SupervisorReview.image_view_correct
  == False`. This codebase only measures the aggregate "image view correct"
  signal, not focus/lighting/angle individually — never fabricated beyond
  what is actually tracked.
- **Disposition errors** — repeated `SupervisorReview.override_action`
  (a supervisor overriding the AI's recommended disposition).

## Non-punitive language

Every gap's `narrative` is one of three fixed, non-punitive phrases scaled
to confidence:

| Confidence | Narrative |
|---|---|
| low (2 occurrences) | "Additional observation may be appropriate." |
| moderate (3-4) | "Targeted education may be beneficial." |
| high (5+) | "Competency verification is recommended." |

Sage never concludes that an individual is incompetent.

## API

```
POST /api/sage/gaps/detect/{technician}
GET  /api/sage/gaps?competency_domain=...&instrument_family=...&anatomy_zone=...
```

Both are leadership-only (`admin`/`spd_manager`) — individual-level gap data
is never exposed to a `viewer` or a peer technician.
