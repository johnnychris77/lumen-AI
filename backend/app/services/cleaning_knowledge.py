"""Phase 21 §4 — Cleaning Knowledge Library.

Per-anatomy-zone cleaning guidance: recommended cleaning method, brush type,
flushing requirement, ultrasonic guidance, visual inspection guidance, and
manual verification guidance.

This is a clinical knowledge layer for the reasoning engine — advisory,
paraphrased SPD practice. It is explicitly NOT a substitute for the
device's manufacturer Instructions For Use (IFU); the IFU always governs
when the two differ.
"""
from __future__ import annotations

CLEANING_KNOWLEDGE: dict[str, dict] = {
    "serrations": {
        "cleaning_method": "Manual brushing under running water, then enzymatic soak.",
        "brush_type": "Soft nylon serration brush matching the tooth pitch.",
        "flushing_requirement": "Not applicable — surface zone, no lumen.",
        "ultrasonic_guidance": "Ultrasonic cleaning recommended for residue lodged between teeth.",
        "visual_inspection_guidance": "Inspect under magnification with the jaw fully open.",
        "manual_verification_guidance": "Run a gloved finger/swab across the serrations to confirm no residue remains.",
    },
    "grooves": {
        "cleaning_method": "Manual brushing followed by enzymatic soak.",
        "brush_type": "Fine-bristle brush sized to the groove width.",
        "flushing_requirement": "Not applicable — surface zone, no lumen.",
        "ultrasonic_guidance": "Ultrasonic cleaning recommended for deep or narrow grooves.",
        "visual_inspection_guidance": "Inspect the full groove length under magnification.",
        "manual_verification_guidance": "Swab test along the groove to confirm no residue.",
    },
    "box lock": {
        "cleaning_method": "Open fully, brush the pivot, then enzymatic soak with the joint actuated.",
        "brush_type": "Small stiff-bristle brush that reaches the pivot recess.",
        "flushing_requirement": "Flush the pivot recess if the design allows water ingress.",
        "ultrasonic_guidance": "Ultrasonic cleaning with the box lock open to expose the pivot.",
        "visual_inspection_guidance": "Inspect the open pivot under magnification for retained soil.",
        "manual_verification_guidance": "Actuate the joint through full range and re-inspect after cleaning.",
    },
    "hinge": {
        "cleaning_method": "Actuate through full range while brushing; enzymatic soak.",
        "brush_type": "Small stiff-bristle brush.",
        "flushing_requirement": "Flush the hinge recess if accessible.",
        "ultrasonic_guidance": "Ultrasonic cleaning with the hinge actuated to expose all surfaces.",
        "visual_inspection_guidance": "Inspect with the hinge open and closed.",
        "manual_verification_guidance": "Confirm free, unrestricted movement after cleaning.",
    },
    "ratchet": {
        "cleaning_method": "Brush the engagement teeth through the full ratchet range; enzymatic soak.",
        "brush_type": "Small stiff-bristle brush that fits between ratchet teeth.",
        "flushing_requirement": "Not applicable — surface zone, no lumen.",
        "ultrasonic_guidance": "Ultrasonic cleaning recommended for residue between ratchet teeth.",
        "visual_inspection_guidance": "Inspect each ratchet position under magnification.",
        "manual_verification_guidance": "Engage and release the ratchet fully to confirm clean, positive engagement.",
    },
    "drill-bit flute": {
        "cleaning_method": "Brush along the flute spiral in the direction of the flute; enzymatic soak.",
        "brush_type": "Narrow twisted-wire or nylon flute brush matching the flute diameter.",
        "flushing_requirement": "Flush the flute channel to clear bone debris.",
        "ultrasonic_guidance": "Ultrasonic cleaning strongly recommended — flutes are a critical retention point.",
        "visual_inspection_guidance": "Inspect the full flute length under magnification.",
        "manual_verification_guidance": "Confirm no bone/tissue debris remains between spirals by touch or swab.",
    },
    "threaded region": {
        "cleaning_method": "Brush along the thread direction; enzymatic soak.",
        "brush_type": "Narrow brush sized to the thread pitch.",
        "flushing_requirement": "Flush between threads.",
        "ultrasonic_guidance": "Ultrasonic cleaning recommended — threads retain residue between crests.",
        "visual_inspection_guidance": "Inspect under magnification along the full threaded length.",
        "manual_verification_guidance": "Swab between threads to confirm no residue.",
    },
    "lumen opening": {
        "cleaning_method": "Flush and brush end-to-end before enzymatic soak.",
        "brush_type": "Lumen brush sized to the internal diameter.",
        "flushing_requirement": "Mandatory — flush the full lumen length before and after brushing.",
        "ultrasonic_guidance": "Ultrasonic cleaning with lumen adapter if the device supports one.",
        "visual_inspection_guidance": "Borescope the lumen if available; otherwise inspect both openings.",
        "manual_verification_guidance": "Confirm clear flush return (no visible soil in effluent).",
    },
    "inner channel": {
        "cleaning_method": "Flush and brush the full channel length before enzymatic soak.",
        "brush_type": "Channel brush matching the internal diameter.",
        "flushing_requirement": "Mandatory — flush before and after brushing.",
        "ultrasonic_guidance": "Ultrasonic cleaning with channel adapter where available.",
        "visual_inspection_guidance": "Borescope if available.",
        "manual_verification_guidance": "Confirm clear flush return.",
    },
    "biopsy channel": {
        "cleaning_method": "Flush and brush end-to-end immediately at point of use, repeated in reprocessing.",
        "brush_type": "Single-use channel brush sized to the biopsy channel diameter.",
        "flushing_requirement": "Mandatory — leak test, then flush before and after brushing.",
        "ultrasonic_guidance": "Not typically applicable to flexible-scope internal channels — follow the device IFU.",
        "visual_inspection_guidance": "Borescope the channel end-to-end if available.",
        "manual_verification_guidance": "Confirm brush emerges clean and flush return is clear at both ports.",
    },
    "suction channel": {
        "cleaning_method": "Flush and brush the full suction channel length; verify flow after cleaning.",
        "brush_type": "Single-use channel brush sized to the suction channel diameter.",
        "flushing_requirement": "Mandatory — flush before and after brushing.",
        "ultrasonic_guidance": "Not typically applicable to flexible-scope internal channels — follow the device IFU.",
        "visual_inspection_guidance": "Borescope if available; check suction port for residue.",
        "manual_verification_guidance": "Confirm unobstructed suction flow after cleaning.",
    },
    "air/water nozzle": {
        "cleaning_method": "Flush the air/water channel and clean the nozzle opening.",
        "brush_type": "Fine nozzle-cleaning brush or single-use cleaning adapter per IFU.",
        "flushing_requirement": "Mandatory — flush air and water channels separately if the device has both.",
        "ultrasonic_guidance": "Not typically applicable — follow the device IFU.",
        "visual_inspection_guidance": "Inspect the nozzle opening for blockage or residue.",
        "manual_verification_guidance": "Confirm patency of both air and water channels.",
    },
    "o-ring area": {
        "cleaning_method": "Clean around the o-ring/port area; remove and inspect the o-ring if removable.",
        "brush_type": "Soft brush; avoid abrasive tools that could damage the o-ring seal.",
        "flushing_requirement": "Rinse the port area to remove residue near the seal.",
        "ultrasonic_guidance": "Ultrasonic cleaning acceptable if the o-ring is removed per IFU.",
        "visual_inspection_guidance": "Inspect the o-ring for wear, nicks, or missing segments.",
        "manual_verification_guidance": "Re-seat the o-ring and confirm a clean, undamaged seal before use.",
    },
    "rigid scope port": {
        "cleaning_method": "Clean the port and sheath connection; verify no residue at the connection point.",
        "brush_type": "Soft brush sized to the port opening.",
        "flushing_requirement": "Rinse the port and connection point.",
        "ultrasonic_guidance": "Ultrasonic cleaning acceptable for the port assembly if removable.",
        "visual_inspection_guidance": "Inspect the port and sheath connection under magnification.",
        "manual_verification_guidance": "Confirm secure, clean connection before reassembly.",
    },
    "insulation edge": {
        "cleaning_method": "Wipe and brush the insulation edge; do not use abrasive tools on the insulation.",
        "brush_type": "Soft brush only — abrasive brushes can create or widen insulation breaches.",
        "flushing_requirement": "Not applicable — surface zone.",
        "ultrasonic_guidance": "Ultrasonic cleaning acceptable; avoid prolonged exposure that could degrade insulation.",
        "visual_inspection_guidance": "Inspect the full insulation length for soil, nicks, or breaches.",
        "manual_verification_guidance": "Run an insulation integrity test (per facility protocol) after cleaning.",
    },
    "cutting edge": {
        "cleaning_method": "Wipe/brush the cutting edge; enzymatic soak.",
        "brush_type": "Soft brush to avoid dulling the edge.",
        "flushing_requirement": "Not applicable — surface zone.",
        "ultrasonic_guidance": "Ultrasonic cleaning acceptable.",
        "visual_inspection_guidance": "Inspect the edge for residue, nicks, or dulling.",
        "manual_verification_guidance": "Confirm the edge is clean and, where applicable, still sharp.",
    },
    "surface discoloration area": {
        "cleaning_method": "Standard surface wipe and enzymatic soak.",
        "brush_type": "Soft general-purpose brush.",
        "flushing_requirement": "Not applicable.",
        "ultrasonic_guidance": "Standard ultrasonic cycle is sufficient.",
        "visual_inspection_guidance": "Monitor for progression at the next inspection.",
        "manual_verification_guidance": "Confirm the surface is clean; discoloration itself is a cosmetic, lower-retention finding.",
    },
    "unspecified region": {
        "cleaning_method": "Standard manual cleaning per facility protocol.",
        "brush_type": "General-purpose brush appropriate to the instrument surface.",
        "flushing_requirement": "Follow the device IFU for any lumens or channels.",
        "ultrasonic_guidance": "Standard ultrasonic cycle per facility protocol.",
        "visual_inspection_guidance": "Standard visual re-inspection.",
        "manual_verification_guidance": "Confirm no residue is visible or palpable.",
    },
}

_DEFAULT_CLEANING = CLEANING_KNOWLEDGE["unspecified region"]

# v2.0 — the Anatomy Zone Engine (app/services/zone_intelligence.py) calls
# this with the per-family anatomy zone's own name (instrument_anatomy.py),
# which occasionally differs from this dict's key for the exact same real
# zone (e.g. drill_bit declares "flutes"; this dict's matching entry
# predates it as "drill-bit flute"). Alias the zone name onto the existing,
# already-written entry rather than falling back to the generic default for
# a zone real, specific guidance already exists for.
_ZONE_ALIASES: dict[str, str] = {
    "flutes": "drill-bit flute",
}


def get_cleaning_knowledge(zone: str) -> dict:
    """Cleaning knowledge for a zone — never a substitute for the device IFU."""
    key = (zone or "").strip().lower()
    key = _ZONE_ALIASES.get(key, key)
    return {
        "zone": zone,
        **CLEANING_KNOWLEDGE.get(key, _DEFAULT_CLEANING),
        "note": "Advisory clinical knowledge, not an IFU replacement — the device IFU governs when the two differ.",
    }
