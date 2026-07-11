"""Project Vulcan, Section 12: Integration With Aegis.

There is no pre-existing "Aegis" platform anywhere in this codebase (verified
via `grep -rn "aegis" app/` before writing this file). Rather than fabricate
one, this computes an honest, minimal process-variation signal from real
`Inspection.technician` concentration among the findings behind a Vulcan
assessment -- the closest real, already-captured field to "process/workflow
pattern." This is deliberately narrower than the brief's illustrative
"evening shift" example, which this codebase has no data to support; the
signal is always described in terms of what was actually measured.

"No agent may overwrite the other's conclusion": `combine_conclusions` only
ever concatenates both sides' text into a new `combined_conclusion` string --
it never mutates or replaces Vulcan's own `reasoning_narrative` or an Aegis
conclusion already stored in `aegis_conclusion_json`.
"""
from __future__ import annotations

from collections import Counter

from app.models.inspection_finding import InspectionFinding


def compute_process_variation_signal(db, tenant_id: str, instrument_identity: str, zone: str | None = None) -> dict:
    """Section 12: Aegis's evidence -- real technician concentration, never fabricated."""
    from app.services.vulcan_progression_service import _inspections_for_identity

    inspections = _inspections_for_identity(db, tenant_id, instrument_identity)
    if zone:
        ids = [i.id for i in inspections]
        zoned_ids = {
            f.inspection_id
            for f in db.query(InspectionFinding).filter(InspectionFinding.inspection_id.in_(ids), InspectionFinding.zone == zone)
        } if ids else set()
        inspections = [i for i in inspections if i.id in zoned_ids]

    technicians = [i.technician for i in inspections if i.technician]
    sample_size = len(technicians)
    if sample_size < 2:
        return {
            "process_variation_detected": False,
            "sample_size": sample_size,
            "concentrated_on": "",
            "concentration_pct": 0.0,
            "narrative": "Insufficient technician-attributed inspection history to assess process variation.",
        }

    counts = Counter(technicians)
    top_technician, top_count = counts.most_common(1)[0]
    concentration_pct = round(100.0 * top_count / sample_size, 1)
    detected = concentration_pct >= 60.0

    narrative = (
        f"{concentration_pct}% of the relevant inspections were performed by the same technician "
        f"({top_count} of {sample_size}), a possible contributing process-variation pattern."
        if detected
        else "No single technician accounts for a majority of the relevant inspections; "
        "no clear process-variation concentration detected."
    )

    return {
        "process_variation_detected": detected,
        "sample_size": sample_size,
        "concentrated_on": top_technician if detected else "",
        "concentration_pct": concentration_pct,
        "narrative": narrative,
    }


def combine_conclusions(vulcan_narrative: str, aegis_conclusion: dict) -> str:
    """Combine both agents' evidence without overwriting either side."""
    if not aegis_conclusion.get("process_variation_detected"):
        return vulcan_narrative
    return (
        f"{vulcan_narrative} Instrument failures may involve both repeated process exposure "
        f"({aegis_conclusion['narrative']}) and progressive material degradation. Human review required "
        "to confirm either contributor before action."
    )
