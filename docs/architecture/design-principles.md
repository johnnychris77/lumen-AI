# LumenAI Design Principles

These four principles are non-negotiable. Any feature, model, or API that
violates one needs a documented exception approved before merge, not a
silent workaround.

## 1. Instrument-first, not image-first

An image is only meaningful once it is attached to a resolved instrument
(family, manufacturer, model where known). LumenAI does not run generic
image classification against an anonymous photo — it always asks "what
instrument is this?" (Layer 3) before asking "what do I see?" (Layer 5).

*Why it matters:* the same visual pattern means something completely
different on a Kerrison rongeur's box lock than on a flexible endoscope's
biopsy channel. Skipping instrument identification produces findings that
can't be zone-weighted, baseline-compared, or clinically interpreted.

## 2. Anatomy-first reasoning

Every finding is reasoned about through the resolved instrument's anatomy
profile — its zones, its high-retention areas, its required inspection
views — never through the raw pixel location alone.
*Implemented by:* `app/services/instrument_anatomy.py`,
`app/services/instrument_zones.py`.

*Why it matters:* "residue near a joint" is only actionable once you know
whether that joint is a low-risk handle seam or a high-retention box lock
that traps blood between uses.

## 3. Clinical reasoning before prediction

A raw detection ("blood: 0.83 confidence") is not a LumenAI output. Every
finding must pass through the clinical reasoning engine (Layer 6) — zone
risk, baseline comparison, evidence strength — before it becomes a
recommendation. LumenAI never presents a bare model score as an answer.

## 4. Human expertise is the final authority

The AI never disposes of an instrument on its own. Every recommendation is
advisory; the supervisor's review and, where applicable, override is what
actually determines what happens to the instrument (Layer 8). This is
enforced structurally, not just by policy: the model registry's deployment
gate (`app/models/model_registry.py`) requires a human-approved promotion
before any model stage can drive or advise a decision beyond shadow mode.

## Examples

**Bad:**
> "Blood detected."

This is a raw detection. It has no instrument, no zone, no clinical
framing, and gives a supervisor nothing to act on beyond re-looking at the
whole instrument.

**Good:**
> "Blood indicators detected in Kerrison jaw serrations, a high-retention
> zone requiring brushing and reprocessing."

This names the instrument context (Kerrison), the zone (jaw serrations),
why the zone matters (high-retention), and the concrete next action
(brushing and reprocessing) — the output of Layers 3 through 7 working
together, not a bare Layer 5 detection.

## Applying the principles

Before shipping any new finding type, model, or dashboard metric, ask:

1. Does it know what instrument it's looking at? (Principle 1)
2. Does it know where on the instrument, and why that location matters?
   (Principle 2)
3. Does it explain clinical significance before recommending an action?
   (Principle 3)
4. Can a supervisor see it, disagree with it, and override it? (Principle 4)

If the answer to any of these is no, the feature is not finished — see
`docs/architecture/architecture-enforcement-checklist.md` for the full
gate.
