# Instrument Zone Detection — Training Dataset Plan

**Status:** Draft for review
**Purpose:** Train the model to localize *where* on an instrument contamination or
damage is likely to hide — not just *what* was detected — so explanations name
the actual high-retention zone (serrations, box lock, lumen, drill-bit flute,
o-ring area, hinge, …) and disposition escalates accordingly.

> ⚠️ Advisory pilot. The current zone assignment is a deterministic heuristic
> from instrument type, not pixel-level localization. No FDA/diagnostic claims;
> `human_review_required` remains true.

---

## 1. Labels captured per image

- **instrument_type** (e.g. serrated forceps, orthopedic drill, rigid scope)
- **finding_type** (blood, tissue, bone, debris, organic residue, rust, corrosion, discoloration, pitting, crack, insulation damage, missing component)
- **severity** (per published scales)
- **zone_type** (from the zone taxonomy)
- **zone_risk** (high / medium / low)
- **image_angle** (e.g. jaw-on, side, distal, port-on)
- **lighting_quality** (good / acceptable / poor)
- **supervisor_confirmed_zone** (adjudicated ground-truth zone)
- **recommended_cleaning_response** (zone-specific manual check)

## 2. Zone taxonomy (label set)

- **Cutting / working surface:** serrations, grooves, teeth, jaws, cutting edge
- **Rotary / orthopedic:** drill-bit flute, threaded region, cutting channel, burr surface
- **Lumen / scope:** lumen opening, inner channel, o-ring area, rigid scope port, lens edge, sheath connection
- **Mechanical:** hinge, box lock, joint, ratchet, spring area
- **Handle / external:** handle seam, insulation edge, outer sheath, surface discoloration area
- **Unknown:** unspecified region, image quality insufficient

High-retention zones (escalate contamination): serrations, grooves, teeth,
cutting edge, drill-bit flute, threaded region, cutting channel, burr surface,
lumen opening, inner channel, o-ring area, rigid scope port, hinge, box lock,
joint, ratchet, insulation edge.

## 3. Instrument coverage (examples required)

Collect labeled examples across:
- **Drill bits / reamers / burrs** — flutes, threaded regions
- **Rigid scopes** — o-ring/port, lumen, lens edge
- **Cannulated instruments** — inner channel, lumen opening
- **Serrated forceps / graspers** — serrations, box lock
- **Laparoscopic instruments** — insulation edge, jaws, shaft lumen
- **Hinged instruments (scissors)** — hinge, cutting edge
- **Box-lock instruments (hemostats, needle holders)** — box lock, serrations
- **Insulated electrosurgical instruments** — insulation edge

Include clean/known-good examples of each zone so the model learns normal
machining/weld appearance per zone.

## 4. Labeling rules

- Multi-label per image; each finding tagged with its **zone** and severity.
- Region annotation (box/mask) on the zone once CV localization is trained.
- **Zone is adjudicated** for critical findings (blood/crack/missing component)
  by two reviewers; disagreements resolved before promotion to `gold`.
- Uncertain zone → `unspecified region` / `image quality insufficient`; excluded
  from the positive zone set until resolved.
- No PHI in frame; EXIF stripped; de-identified filenames.

## 5. Supervisor validation (feedback loop)

The supervisor review captures, per inspection:
- **AI finding correct?** (finding_correct)
- **AI zone correct?** (zone_correct)
- **Corrected zone** (corrected_zone)
- **Corrected severity** (corrected_severity)
- **Final disposition** (final_disposition)

These are stored (`supervisor_reviews`) as labeled training data — the primary
source of zone ground truth and of false-positive/false-negative zone signal.

## 6. Model evaluation

- Per-zone precision/recall (did the model name the right zone?) alongside the
  existing finding-type metrics (`app/analytics/model_evaluation.py`).
- Critical-zone recall (lumen, serrations, box lock, flute) reported separately.
- Shadow-mode only until per-zone thresholds are met; output stays advisory.

## 7. Governance / rights

- Retention is opt-in with recorded consent; instrument-only imagery.
- Web images (research/prototyping only) tagged `source=web`, excluded from
  validation/test, never treated as ground truth.
