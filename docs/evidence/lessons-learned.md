# Lessons Learned

Real lessons captured from prior pilot, implementation, and platform-
development work — not hypothetical best practices.

## From the Bon Secours pilot exercise (`docs/pilot/pilot-findings-analysis.md`)

1. **Image capture friction kills adoption.** A separate, two-step image
   upload flow was skipped in 100% of Week 1 pilot cases. This directly
   shaped later phases' emphasis on making capture part of the natural
   inspection workflow rather than a bolt-on step — see the
   `inspected_zones` capture built into `POST /api/inspections` (Phase 20
   command center's coverage engine depends on this being captured
   inline, not as an afterthought).
2. **Silent scoring gaps are worse than visible ones.** The original
   scoring engine silently returned 0 for five of seven finding
   categories rather than surfacing an "unscored" state. This directly
   informed the platform-wide honesty convention now enforced everywhere:
   a metric with no real data returns `null`, never a fabricated
   `0` (see the pattern throughout Phases 18/20/21/23 — e.g.
   `docs/command-center/readiness-score-model.md`'s "honesty
   constraints" section).
3. **Persist operational context, not just clinical findings.**
   Facility/department/tray identity were not originally persisted as ORM
   columns, which blocked tray-level and facility-level reporting. This
   is why Phase 20's command center's Tray Readiness and Facility
   Readiness modules explicitly depend on these fields
   (`Inspection.facility_name`/`department`/`tray_id`) being captured at
   inspection time.

## From platform architecture work (Phases 17–23)

4. **A five-value decision vocabulary, once adopted, should not be
   silently extended.** Phase 19.5 drafted a six-value decision
   vocabulary and then explicitly reverted to keeping the original
   five-value `PASS`/`MONITOR`/`SUPERVISOR REVIEW`/`REPROCESS`/`REMOVE
   FROM SERVICE` outcome after weighing the cost of renaming a value
   asserted by ~2,300 tests against the benefit of a slightly richer
   vocabulary — see
   `docs/architecture/lumenai-clinical-intelligence-architecture.md`
   §Layer 7. Lesson: a "nicer" vocabulary is not worth breaking a
   load-bearing contract; extend via a sub-field instead
   (`repair_candidate` in Phase 20's `classify_readiness`).
5. **One supervisor decision should produce every downstream artifact in
   one transaction, not require re-entry.** Early designs had a
   supervisor review, a pilot validation ground-truth case, and a
   decision-ledger entry as three separate manual submissions. Phases 18,
   21, and 23 progressively wired all three into the single existing
   `POST /inspections/{id}/supervisor-review` submission — the lesson
   generalized from the Bon Secours image-capture friction finding above:
   every extra manual step a real user has to take is adoption risk.

## Process for adding future entries

After every pilot, go-live, or incident review, add a dated entry here
with: what happened, what it revealed, and what changed in the product or
process as a result. A lesson without a resulting change is a complaint,
not a lesson — this document should only contain the latter.
