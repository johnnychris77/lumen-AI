# Supervisor Guide — Clinical Pilot (Phase 1)

For SPD supervisors and the clinical sponsor's delegates. Companion to
the technician guide and `docs/advisory-pilot/PILOT_DASHBOARD_GUIDE.md`.

## Your role in the pilot

You are the human-oversight layer the whole design assumes. During
Phase 1 you: review policy-required escalations, spot-check routine
advisory output, complete supervisor reviews (your entries become the
labeled data provenance record), watch for automation bias in the team,
and hold the authority to pause the AI panel at any time.

## Review queue — what arrives and why

* **Unknown findings** — the model saw something outside its supported
  classes; your classification feeds the governed learning loop (it
  never becomes Ground Truth automatically).
* **Low-confidence actionable observations** — the system abstained
  from asserting; your read stands.
* **Contamination-class observations** — always require review; the
  decision engine has already forced a reclean/reinspect recommendation
  regardless of any baseline similarity.
* **Persistent findings after recleaning**, structural/repair concerns,
  and any technician-initiated escalation.

Routine clean inspections do **not** require your approval — if you see
routine items flooding the queue, that's a policy-tuning finding for
the observation log, not a workload you should absorb silently.

## Completing a supervisor review

Record your own classification, whether the AI's observation was
correct/incorrect/not-assessable, the corrected recommendation where
applicable, and the final disposition. Write full sentences where the
form allows — your reasoning is retained verbatim as evidence. Your
review is stored append-only with your identity and timestamp in the
audit trail.

## Watching the humans, not just the machine

Flag on the observation form if you see: technicians accepting advisory
output without looking at the image; treating a probability as a
confirmation; skipping normal inspection steps because "the AI said
clean"; or distrust so high the panel is being ignored entirely. Both
extremes are pilot findings.

## Pausing the AI panel

You can direct the team to disregard/disable the advisory panel at any
time (manual workflow always remains complete). Mandatory pause
triggers are listed in `PILOT_PROTOCOL.md` §Safety. Record every pause,
its reason, and the restart approval on the safety form.
