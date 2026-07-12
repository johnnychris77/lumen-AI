"""Project Veritas, Section 4: Instrument-to-Baseline Matching.

Neither real baseline table (`BaselineLibraryEntry`,
`EnterpriseVendorBaselineSubscription`) tracks anatomy zone or a resolved
anatomy family directly -- only a free-text `instrument_category`/
`instrument_name` and manufacturer/model. Matching therefore compares real,
already-resolved anatomy families (`instrument_anatomy.resolve_family`)
rather than a fabricated zone-level comparison the underlying data can't
support. A rigid-scope image is never compared against a flexible-endoscope
baseline (different families) -- exactly the brief's example.
"""
from __future__ import annotations

from app.models.veritas_evidence import (
    MATCH_COMPATIBLE,
    MATCH_EXACT,
    MATCH_MISMATCH,
    MATCH_PARTIAL,
    MATCH_UNAVAILABLE,
    MATCH_UNCERTAIN,
)
from app.services.instrument_anatomy import resolve_family


def classify_match(
    *, instrument_type: str, baseline_instrument_category: str = "", baseline_manufacturer: str = "",
    instrument_manufacturer: str = "", baseline_model: str = "", instrument_model: str = "",
) -> dict:
    """Section 4: classify baseline compatibility from real, resolved
    anatomy families -- never a fabricated per-zone comparison."""
    if not baseline_instrument_category:
        return {
            "match_classification": MATCH_UNAVAILABLE,
            "reason": "No baseline instrument category available to compare against.",
        }

    instrument_family = resolve_family(instrument_type)
    baseline_family = resolve_family(baseline_instrument_category)

    if instrument_family == "unknown" or baseline_family == "unknown":
        return {
            "match_classification": MATCH_UNCERTAIN,
            "reason": "Instrument or baseline family could not be confidently resolved.",
        }

    if instrument_family != baseline_family:
        return {
            "match_classification": MATCH_MISMATCH,
            "reason": (
                f"Instrument family '{instrument_family}' does not match baseline family '{baseline_family}' -- "
                "these anatomy profiles must not be compared."
            ),
        }

    manufacturer_match = (
        bool(instrument_manufacturer) and bool(baseline_manufacturer)
        and instrument_manufacturer.strip().lower() == baseline_manufacturer.strip().lower()
    )
    model_match = (
        bool(instrument_model) and bool(baseline_model)
        and instrument_model.strip().lower() == baseline_model.strip().lower()
    )

    if manufacturer_match and (model_match or not (instrument_model and baseline_model)):
        return {"match_classification": MATCH_EXACT, "reason": "Family and manufacturer/model match."}
    if manufacturer_match or not (instrument_manufacturer or baseline_manufacturer):
        return {"match_classification": MATCH_COMPATIBLE, "reason": "Same anatomy family; manufacturer/model not fully confirmed."}
    return {
        "match_classification": MATCH_PARTIAL,
        "reason": "Same anatomy family, but manufacturer differs -- compatible profile, reduced confidence.",
    }
