# SPD Champion Guide

## Who this is for

The SPD supervisor, lead tech, or educator who owns day-to-day adoption
of LumenAI within the department — the primary point of contact between
frontline staff and the implementation team.

## Your responsibilities

1. **Own the rollout schedule.** Work through
   `docs/customer/30-day-go-live-plan.md` week by week with your team.
2. **Train your team.** Use `docs/customer/training-matrix.md` to confirm
   every technician and supervisor role has completed the right training
   before they start using LumenAI unsupervised.
3. **Load baselines.** Coordinate with vendors/manufacturers to get
   approved baselines loaded for your site's top instrument families
   before go-live (baseline governance — see
   `docs/architecture/domain-model.md`'s Baseline entity).
4. **Be the first line of support.** Most day-to-day questions ("why did
   it flag this?", "how do I correct a zone?") should go through you
   first — use `docs/knowledge-graph/reasoning-engine.md` and the
   Knowledge Graph Explorer (`/knowledge-graph`) to understand and
   explain AI reasoning to your team before escalating to LumenAI
   support.
5. **Watch the safety queue.** Check the Supervisor Review Queue and
   High-Risk Findings Queue
   (`/pre-sterilization-command-center`) daily — these are the
   inspections that need a human decision *now*.
6. **Report friction, not just problems.** If technicians are
   consistently missing zone coverage on a specific instrument family,
   that's a training-matrix gap, not a bug — flag it for the Day 60
   optimization review (`docs/customer/60-day-optimization-plan.md`).

## What good supervisor review looks like

- **Agree** when the AI's finding, zone, and recommendation all look
  correct — no rationale required beyond the agreement itself.
- **Partially agree or disagree** with a written rationale when the
  finding is right but the zone is wrong (or vice versa) — use the
  `corrected_zone`/`corrected_instrument_family`/`corrected_severity`
  fields; this becomes real labeled training data (Phase 18), not just a
  note that disappears.
- **Override** the recommended disposition only when there's a clinical
  reason to do so, always with a rationale — overrides are tracked
  (`most_common_supervisor_override` in the Enterprise Knowledge
  Analytics) and repeated overrides of the same type are a signal worth
  investigating, not just accepting.

## Daily/weekly rhythm

| Cadence | Activity |
|---|---|
| Daily | Clear the Supervisor Review Queue; check High-Risk Findings Queue |
| Weekly | Spot-check zone-coverage quality trends; check in with technicians on friction points |
| At Day 30/60/90 checkpoints | Represent the SPD department's operational perspective in the Executive Sponsor review |

## Escalation

If you can't resolve a question about an AI recommendation, or if you
believe a finding was clinically wrong and the reasoning chain doesn't
explain why, escalate to LumenAI support — a genuine AI reasoning gap is
exactly the kind of signal the Continuous Learning Agent (Phase 22) and
the Knowledge Graph (Phase 21) need real supervisor corrections to
improve.
