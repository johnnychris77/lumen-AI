# Instrument Zone Taxonomy (Phase 15)

## Zone categories
- **Cutting / working surface:** serrations, grooves, teeth, jaws, cutting edge
- **Rotary / orthopedic:** drill-bit flute, threaded region, cutting channel, burr surface
- **Lumen / scope:** lumen opening, inner channel, o-ring area, rigid scope port, lens edge, sheath connection
- **Mechanical:** hinge, box lock, joint, ratchet, spring area
- **Handle / external:** handle seam, insulation edge, outer sheath, surface discoloration area
- **Unknown:** unspecified region, image quality insufficient

## Zone risk model (per zone)
`zone_name · zone_category · zone_risk_level (low/medium/high/critical) ·
retention_risk (low/medium/high) · contamination_risks[] · condition_risks[]`

## High-retention zones (escalate contamination)
grooves, serrations, threaded regions, drill-bit flutes, o-ring areas, rigid scope
ports, lumens, cannulated channels, box locks, hinges, joints, ratchets, handle
seams, insulation edges, crevices.

## Escalation rules
- Blood 35% on a flat surface → Review.
- Blood 35% in serrations / groove / lumen / o-ring / threaded region / flute /
  box lock / hinge → High risk → Reprocess.
- Debris in a drill-bit flute → High risk → Reprocess / supervisor review.
- Organic residue in an o-ring area → High risk → Supervisor review.
- Crack in a working surface → Remove from service.
- Insulation damage on a laparoscopic instrument → Remove from service.

Anything that escalates the disposition is also surfaced in the explanation.

## Instrument-specific zone examples
- **Rigid scope:** distal tip, lens edge, o-ring area, light post, eyepiece, working channel, sheath connection, seal.
- **Drill bit:** tip, flutes, threaded region, cutting edge, shank, hub.
- **Kerrison / rongeur:** jaw, serrations, box lock, hinge, spring, ratchet, handle.
- **Scissors:** tip, blade, cutting edge, serration, box lock, handle.
- **Needle holder:** jaw inserts, serrations, box lock, ratchet, tungsten carbide inserts, handle.
- **Laparoscopic:** distal jaws, hinge, insulation edge, shaft, handle seam, rotation knob, lumen/cannulated channel.
