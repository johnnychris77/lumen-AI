"""Project Sage, Sections 13 & 14: Integration With Aegis and Vulcan.

Aegis remains responsible for process analysis; Vulcan remains responsible
for instrument reliability; Sage remains responsible only for education and
competency support. Each integration point *reads* the other agent's real
conclusion (`vulcan_aegis_integration_service.compute_process_variation_signal`,
`VulcanReliabilityAssessment`) and returns a Sage-specific recommendation --
it never mutates or overwrites the source conclusion, and the two remain
separately traceable via `source_vulcan_assessment_id`/`source_aegis_signal`
in the returned evidence, never merged into a single blended field.
"""
from __future__ import annotations

from app.models.vulcan_reliability import VulcanReliabilityAssessment
from app.services.vulcan_aegis_integration_service import compute_process_variation_signal

# Vulcan failure leaves easily confused with a benign cosmetic finding --
# Sage should recommend differentiation education specifically for these.
_AMBIGUOUS_CONDITION_PAIRS = {
    "corrosion": "cosmetic discoloration",
    "rust": "cosmetic discoloration",
    "pitting": "cosmetic surface wear",
}


def sage_recommendation_from_aegis(db, tenant_id: str, instrument_identity: str, zone: str | None = None) -> dict:
    """Section 13 example: Aegis finds a process-concentration pattern;
    Sage recommends focused brushing/inspection education for the affected
    anatomy -- Aegis's own signal is included by reference, never edited."""
    aegis_signal = compute_process_variation_signal(db, tenant_id, instrument_identity, zone=zone)
    if not aegis_signal["process_variation_detected"]:
        return {
            "has_recommendation": False,
            "source_aegis_signal": aegis_signal,
            "recommendation": "",
        }
    zone_text = f" for {zone}" if zone else ""
    return {
        "has_recommendation": True,
        "source_aegis_signal": aegis_signal,
        "recommendation": (
            f"Aegis evidence shows a process-concentration pattern ({aegis_signal['narrative']}). "
            f"Recommend focused brushing and inspection education{zone_text} for the affected workflow."
        ),
    }


def sage_recommendation_from_vulcan(assessment: VulcanReliabilityAssessment) -> dict:
    """Section 14 example: Vulcan finds repeated corrosion at an anatomy
    zone; Sage recommends differentiation education (corrosion vs cosmetic
    discoloration) plus focused inspection of that zone. Vulcan's own
    `reasoning_narrative`/`recommended_disposition` are referenced by ID,
    never copied into or overwritten by Sage's recommendation."""
    confusable_with = _AMBIGUOUS_CONDITION_PAIRS.get(assessment.failure_category)
    zone_text = assessment.anatomy_zone.replace("_", " ") if assessment.anatomy_zone else "the affected anatomy zone"

    if confusable_with:
        recommendation = (
            f"Vulcan evidence shows recurring {assessment.failure_category} at {zone_text}. "
            f"Recommend education on differentiating {assessment.failure_category} from {confusable_with} "
            f"and focused {zone_text} inspection."
        )
    else:
        recommendation = (
            f"Vulcan evidence shows a reliability pattern ({assessment.failure_category or 'unspecified'}) "
            f"at {zone_text}. Recommend focused inspection education for {zone_text}."
        )

    return {
        "has_recommendation": True,
        "source_vulcan_assessment_id": assessment.id,
        "source_vulcan_reliability_category": assessment.reliability_category,
        "recommendation": recommendation,
    }
