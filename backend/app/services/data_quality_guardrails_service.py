"""v1.9 — Inspection Data Quality Guardrails (Deliverable 5).

Evaluates a persisted inspection for real, actionable data-quality gaps
against the pilot site's own configured thresholds — never a duplicate
hard gate on top of the existing coverage-gate/baseline-governance logic
(`guided_capture.py`, `baseline_comparison_scoring_service.py`), just a
clear, human-readable summary of what's missing for the technician and the
Pilot Data Collection Dashboard.
"""
from __future__ import annotations

_LOW_CONFIDENCE_THRESHOLD = 0.5


def evaluate_data_quality(insp, *, pilot_config) -> dict:
    """Deliverable 5 — clear-message data-quality issues for one
    inspection. `is_dataset_ready` is true only when every check passes."""
    issues: list[dict] = []

    if not insp.instrument_type or insp.instrument_type == "unknown":
        issues.append({
            "code": "missing_instrument",
            "message": "No instrument type was recorded for this inspection.",
        })

    if not insp.has_image:
        issues.append({
            "code": "missing_image",
            "message": "No image was captured — this inspection was scored from manual entry only.",
        })
    else:
        if insp.coverage_pct is None:
            issues.append({
                "code": "missing_anatomy_zone",
                "message": "No anatomy zones were tagged for this inspection.",
            })
        elif insp.coverage_pct < pilot_config.minimum_coverage_pct:
            issues.append({
                "code": "incomplete_coverage",
                "message": f"Coverage is {insp.coverage_pct}%, below the site's {pilot_config.minimum_coverage_pct}% minimum.",
            })

        if insp.ai_confidence is not None and insp.ai_confidence < _LOW_CONFIDENCE_THRESHOLD:
            issues.append({
                "code": "poor_image_quality",
                "message": f"AI confidence is only {round(insp.ai_confidence * 100)}% — image quality may be insufficient.",
            })

        if pilot_config.baseline_required and insp.baseline_status != "approved_baseline_found":
            issues.append({
                "code": "missing_baseline",
                "message": "No approved baseline is on file for this instrument type.",
            })

    if not insp.technician:
        issues.append({
            "code": "missing_technician_identity",
            "message": "No technician identity was recorded for this inspection.",
        })

    return {
        "inspection_id": insp.id,
        "issues": issues,
        "is_dataset_ready": len(issues) == 0,
    }
