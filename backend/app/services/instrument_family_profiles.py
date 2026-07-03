"""Phase 21 §3 — Instrument Family Intelligence.

Knowledge profiles (typical contamination, typical damage, typical repair
issues, inspection priorities, cleaning priorities, supervisor focus areas)
for the ten instrument families SPD sees most often. Each profile links to
a real anatomy family in `app/services/instrument_anatomy.py` so "typical
anatomy" is always the live zone data, never a duplicated copy.

Three families (Cannulated Instruments, Orthopedic Instruments, Micro
Instruments) do not yet have a dedicated anatomy-zone taxonomy split out —
they honestly borrow the closest existing anatomy family (flagged via
`anatomy_family_note`) rather than fabricating zones that were never
defined. See docs/knowledge-graph/instrument-intelligence.md.
"""
from __future__ import annotations

from app.services.instrument_anatomy import anatomy_profile

INSTRUMENT_FAMILY_PROFILES: dict[str, dict] = {
    "rigid_scope": {
        "display_name": "Rigid Scope",
        "anatomy_family_key": "rigid_scope",
        "typical_contamination": ["blood", "tissue", "other_organic_residue"],
        "typical_damage": ["lens scratching", "o-ring wear", "seal failure"],
        "typical_repair_issues": ["cracked lens", "bent shaft", "damaged seal"],
        "inspection_priorities": ["o-ring area", "working channel", "distal tip", "lens edge"],
        "cleaning_priorities": ["working channel flush and brush", "o-ring/seal inspection"],
        "supervisor_focus_areas": ["baseline lens clarity match", "working channel patency"],
    },
    "flexible_endoscope": {
        "display_name": "Flexible Endoscope",
        "anatomy_family_key": "flexible_endoscope",
        "typical_contamination": ["blood", "tissue", "other_organic_residue", "debris"],
        "typical_damage": ["bending section stiffness", "insertion tube abrasion", "channel damage"],
        "typical_repair_issues": ["biopsy channel leak", "bending section failure", "insulation breach"],
        "inspection_priorities": ["biopsy channel", "suction channel", "distal end", "bending section"],
        "cleaning_priorities": ["channel flush/brush end-to-end", "leak testing", "borescope internal channels"],
        "supervisor_focus_areas": ["channel patency", "leak test result", "bending section function"],
    },
    "kerrison": {
        "display_name": "Kerrison",
        "anatomy_family_key": "kerrison_rongeur",
        "typical_contamination": ["blood", "bone", "other_organic_residue"],
        "typical_damage": ["dulled jaw", "worn serrations", "loose box lock"],
        "typical_repair_issues": ["jaw misalignment", "footplate wear", "spring fatigue"],
        "inspection_priorities": ["jaw", "serrations", "box lock", "hinge"],
        "cleaning_priorities": ["open box lock and brush pivot", "brush jaw serrations under magnification"],
        "supervisor_focus_areas": ["serration residue", "box lock cleanliness", "jaw alignment"],
    },
    "needle_holder": {
        "display_name": "Needle Holder",
        "anatomy_family_key": "needle_holder",
        "typical_contamination": ["blood", "tissue"],
        "typical_damage": ["worn tungsten carbide inserts", "misaligned jaws", "worn ratchet teeth"],
        "typical_repair_issues": ["jaw insert replacement", "ratchet realignment"],
        "inspection_priorities": ["jaw inserts", "serrations", "box lock", "ratchet"],
        "cleaning_priorities": ["brush jaw inserts and serrations", "brush ratchet teeth"],
        "supervisor_focus_areas": ["jaw insert grip integrity", "ratchet engagement"],
    },
    "scissors": {
        "display_name": "Scissors",
        "anatomy_family_key": "scissors",
        "typical_contamination": ["blood", "tissue", "debris"],
        "typical_damage": ["dulled cutting edge", "nicked blade", "loose box lock"],
        "typical_repair_issues": ["blade sharpening", "box lock tightening"],
        "inspection_priorities": ["blade", "cutting edge", "box lock"],
        "cleaning_priorities": ["inspect and brush cutting edge", "open and brush box lock"],
        "supervisor_focus_areas": ["blade sharpness/alignment", "cut test where applicable"],
    },
    "drill_bit": {
        "display_name": "Drill Bit",
        "anatomy_family_key": "drill_bit",
        "typical_contamination": ["bone", "other_organic_residue", "debris"],
        "typical_damage": ["dulled flutes", "corroded threads", "bent shank"],
        "typical_repair_issues": ["flute resharpening", "shank straightening"],
        "inspection_priorities": ["flutes", "threaded region", "tip"],
        "cleaning_priorities": ["brush flutes and threaded region", "confirm no residue between spirals"],
        "supervisor_focus_areas": ["flute residue", "cutting tip wear"],
    },
    "laparoscopic_instruments": {
        "display_name": "Laparoscopic Instruments",
        "anatomy_family_key": "laparoscopic",
        "typical_contamination": ["blood", "tissue", "debris"],
        "typical_damage": ["insulation breach", "bent shaft", "worn hinge"],
        "typical_repair_issues": ["insulation replacement", "hinge repair"],
        "inspection_priorities": ["insulation edge", "distal jaws", "hinge", "handle seam"],
        "cleaning_priorities": ["flush lumen/cannulated channel if present", "test insulation integrity end-to-end"],
        "supervisor_focus_areas": ["insulation integrity test result", "distal jaw alignment"],
    },
    "cannulated_instruments": {
        "display_name": "Cannulated Instruments",
        "anatomy_family_key": "laparoscopic",
        "anatomy_family_note": (
            "Cannulated instruments do not yet have a dedicated anatomy-zone taxonomy split out; "
            "typical anatomy is borrowed from the laparoscopic family's lumen/cannulated channel zone."
        ),
        "typical_contamination": ["blood", "tissue", "debris", "other_organic_residue"],
        "typical_damage": ["lumen obstruction", "channel scoring"],
        "typical_repair_issues": ["channel reaming", "cannula replacement"],
        "inspection_priorities": ["lumen/cannulated channel", "distal opening"],
        "cleaning_priorities": ["flush the full length of the cannulation", "brush with correct-diameter brush"],
        "supervisor_focus_areas": ["channel patency", "flush return clarity"],
    },
    "orthopedic_instruments": {
        "display_name": "Orthopedic Instruments",
        "anatomy_family_key": "drill_bit",
        "anatomy_family_note": (
            "Broader orthopedic instruments (saws, awls, broaches) share the drill_bit anatomy "
            "family pending a dedicated split; drill/reamer/burr zones are the closest real match."
        ),
        "typical_contamination": ["bone", "other_organic_residue", "debris"],
        "typical_damage": ["worn cutting surfaces", "corroded threads", "bent components"],
        "typical_repair_issues": ["resharpening", "component straightening"],
        "inspection_priorities": ["cutting/working surface", "threaded/cannulated regions", "hub/connection"],
        "cleaning_priorities": ["brush cannulations and threaded regions", "confirm no bone debris in channels"],
        "supervisor_focus_areas": ["cannulation patency", "cutting surface wear"],
    },
    "micro_instruments": {
        "display_name": "Micro Instruments",
        "anatomy_family_key": "default",
        "anatomy_family_note": (
            "No micro-instrument-specific anatomy zones exist yet; falls back to the generic "
            "instrument profile. Flagged as a future anatomy-taxonomy expansion."
        ),
        "typical_contamination": ["blood", "tissue"],
        "typical_damage": ["bent tips", "misaligned jaws", "loss of tip precision"],
        "typical_repair_issues": ["tip realignment", "spring tension adjustment"],
        "inspection_priorities": ["working tip", "hinge/joint"],
        "cleaning_priorities": ["inspect under magnification", "gentle brushing to avoid further tip damage"],
        "supervisor_focus_areas": ["tip alignment under magnification", "fine-motion function test"],
    },
}


def get_family_profile(family_key: str) -> dict | None:
    """Full knowledge profile for a family key, with live anatomy attached."""
    profile = INSTRUMENT_FAMILY_PROFILES.get(family_key)
    if profile is None:
        return None
    # Resolve via a space-separated hint (not the raw underscore key) so the
    # keyword matcher in instrument_anatomy.py sees real words, e.g.
    # "kerrison_rongeur" -> "kerrison rongeur".
    anatomy = anatomy_profile(profile["anatomy_family_key"].replace("_", " "))
    return {
        "family_key": family_key,
        **profile,
        "typical_anatomy": anatomy["anatomy_zones"],
        "high_risk_zones": anatomy["high_risk_zones"],
    }


def list_family_profiles() -> list[dict]:
    return [get_family_profile(key) for key in INSTRUMENT_FAMILY_PROFILES]
