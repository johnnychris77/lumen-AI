# Technician Guide — Clinical Pilot (Phase 1)

Companion to `docs/pilot/pilot-user-training-guide.md` (full platform
walkthrough) and `docs/advisory-pilot/ADVISORY_MODE_GUIDE.md`. This
guide is the short, pilot-specific version for the inspection bench.

## The one rule

**LumenAI advises; you decide.** Nothing the screen shows replaces your
inspection judgment or your department's procedure. During this pilot
the AI's suggestions come from an **experimental model that has never
been trained on real instrument images** — treat them as observations
being evaluated, not guidance to follow.

## Your workflow

1. **Scan or select the instrument.** Confirm the instrument family and
   anatomy context shown match the physical instrument. Wrong context =
   stop and correct before capturing.
2. **Capture the borescope image** at the standardized station settings.
3. **Upload.** The system assigns a permanent image ID (LCID) and
   verifies the file hash. If upload fails, retry; if it fails again,
   log it on the observation form and continue your normal manual
   inspection — the pilot never blocks your real work.
4. **Review what the system shows**, in this order:
   * *Image quality* — if flagged poor, recapture.
   * *Baseline panel* — a reference image if a compatible approved
     baseline exists; "no approved baseline" is a normal, honest state.
   * *AI advisory panel* — probable observation with confidence and
     disclosure labels. `AI ANALYSIS UNAVAILABLE — MANUAL INSPECTION
     REQUIRED` means exactly that; it is never a pass.
5. **Make your decision** — accept, modify, or reject the advisory
   suggestion, and record what you actually did. When you modify or
   reject, add the reason: that feedback is one of the most valuable
   things the pilot collects.
6. **Escalate** when the system asks (unknown finding, low confidence,
   contamination-class observation, persistent finding after
   recleaning) or whenever your own judgment says so. Escalating is
   never penalized.
7. **Note anything odd** on the observation form: wrong image shown,
   slow steps, confusing wording, workflow interruptions.

## What can never happen

* A probable-contamination observation can never display as PASS.
* An unavailable or failed analysis can never display as PASS.
* The system never auto-passes an instrument; every disposition is a
  human decision.

If you ever see the screen contradict these, stop using the AI panel,
finish the inspection manually, and report it immediately — that is a
safety event with top priority.
