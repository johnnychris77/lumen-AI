# Workflow Timing Report — Phase 1

> **STATUS: TEMPLATE — NO PILOT HAS RUN. NO TIMING DATA EXISTS.**
> This file is the report structure only. Every number in it must come
> from completed Form A entries (`PILOT_OBSERVATION_FORMS.md`) captured
> at the real site. Populating it any other way would be fabricated
> evidence.

## Report structure (to be filled from real Form A data)

1. **Observation window and coverage** — dates, number of observed
   inspections, fraction of total pilot inspections observed.
2. **Per-step timing distribution** — for each workflow step
   (scan/select, capture, upload, baseline retrieval, inference,
   advisory review + decision, supervisor review, total): n, median,
   p90, min–max. Report `insufficient_data` for any step with n < 10.
3. **Interruption analysis** — count, causes, total time lost.
4. **Comparison to baseline process** — only if the site's pre-pilot
   inspection timing was measured; otherwise state "no pre-pilot
   baseline measured" rather than estimating.
5. **Findings for workflow burden** — against the burden threshold
   pre-agreed in the site record.
