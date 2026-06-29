"""Baseline Comparison Scoring Service.

⚠️  THIS IS A DETERMINISTIC PLACEHOLDER — NOT PRODUCTION COMPUTER VISION.

This service produces a structured, explainable inspection analysis using:
  - baseline presence/resolution (manufacturer → vendor → hospital)
  - image metadata (SHA-256 hash as a stable deterministic seed)
  - technician-declared / demo finding indicators
  - safe heuristic scoring rules

It exists so the end-to-end inspection workflow (upload → analyze → score →
display) functions before a real computer-vision model is integrated. The
response shape is intentionally identical to the future real-AI response so
the model can be swapped in without changing the API contract or frontend.

Governance:
  - No causation language; findings are "potential" / "possible".
  - When no approved baseline exists, NO final score is generated and the
    result is flagged supervisor_review_required.
  - human_review_required is always True on every output.
"""
from __future__ import annotations

import hashlib
from typing import Any, Optional

from sqlalchemy.orm import Session

# Baseline resolution order — most authoritative first.
BASELINE_PRIORITY = ["manufacturer", "vendor", "hospital"]

# Human-readable labels + role (manufacturer is the authoritative primary;
# vendor and hospital are fallbacks used only when no manufacturer baseline
# is approved). Surfaced so the UI can state exactly what was compared.
BASELINE_LABELS = {
    "manufacturer": "Manufacturer baseline",
    "vendor": "Vendor baseline",
    "hospital": "Hospital baseline",
}


def _baseline_role(source: str) -> str:
    return "primary" if source == "manufacturer" else "fallback"


def _baseline_comparison_label(source: str) -> str:
    label = BASELINE_LABELS.get(source, source)
    return label if source == "manufacturer" else f"{label} (fallback)"

# KPI categories the analysis reports on.
CONTAMINATION_KPIS = ["blood", "bone", "tissue", "bioburden", "debris", "other_organic_residue"]
CONDITION_KPIS = ["rust", "discoloration", "corrosion", "pitting", "crack", "insulation_damage", "missing_component"]

# Map technician-declared finding_categories onto KPI keys.
_DECLARED_TO_KPI = {
    "blood": "blood",
    "bone": "bone",
    "tissue": "tissue",
    "debris": "debris",
    "corrosion": "corrosion",
    "crack": "crack",
    "insulation_damage": "insulation_damage",
    "other": "other_organic_residue",
}

# Per-KPI risk weight (how much a positive finding deducts from the score).
_KPI_WEIGHT = {
    "blood": 28, "bone": 24, "tissue": 24, "bioburden": 20,
    "debris": 16, "other_organic_residue": 10,
    "rust": 14, "discoloration": 8, "corrosion": 22, "pitting": 16,
    "crack": 30, "insulation_damage": 30, "missing_component": 26,
}


def _seed_from(image_sha256: Optional[str], fallback: str) -> int:
    """Stable integer seed so the same image always scores the same."""
    basis = image_sha256 or hashlib.sha256(fallback.encode()).hexdigest()
    return int(basis[:8], 16)


def _pseudo(seed: int, salt: int) -> float:
    """Deterministic pseudo-value in [0, 1) derived from seed + salt.

    Uses SHA-256 of the combined inputs — stable across runs/machines,
    unlike Python's hash().
    """
    h = hashlib.sha256(f"{seed}:{salt}".encode()).hexdigest()
    return int(h[:8], 16) / 0xFFFFFFFF


def resolve_baseline(db: Session, instrument_type: str, tenant_id: str) -> dict[str, Any]:
    """Resolve the most authoritative approved baseline for an instrument.

    Checks manufacturer → vendor → hospital. Returns the first approved match.
    """
    from app.models.baseline_library import BaselineLibraryEntry

    for source in BASELINE_PRIORITY:
        entry = (
            db.query(BaselineLibraryEntry)
            .filter(
                BaselineLibraryEntry.instrument_category == instrument_type,
                BaselineLibraryEntry.baseline_type == source,
                BaselineLibraryEntry.approval_status == "approved",
            )
            .first()
        )
        if entry is not None:
            return {
                "baseline_found": True,
                "baseline_source": source,
                "baseline_entry_id": entry.id,
                "baseline_version": entry.baseline_version,
            }

    return {
        "baseline_found": False,
        "baseline_source": None,
        "baseline_entry_id": None,
        "baseline_version": None,
    }


def _severity(probability: float) -> str:
    if probability >= 0.6:
        return "high"
    if probability >= 0.3:
        return "medium"
    if probability >= 0.1:
        return "low"
    return "none"


def _risk_level(score: int) -> str:
    if score >= 85:
        return "low"
    if score >= 65:
        return "medium"
    if score >= 40:
        return "high"
    return "critical"


def analyze_inspection(
    db: Session,
    *,
    instrument_type: str,
    tenant_id: str,
    has_image: bool,
    image_sha256: Optional[str] = None,
    declared_findings: Optional[list[str]] = None,
    instrument_barcode: Optional[str] = None,
    instrument_udi: Optional[str] = None,
    keydot_id: Optional[str] = None,
) -> dict[str, Any]:
    """Run the deterministic baseline-comparison analysis.

    Returns the explainable analysis payload. When no approved baseline is
    found, returns analysis_status="supervisor_review_required" with NO final
    score, per governance rules.
    """
    declared = {
        _DECLARED_TO_KPI[c]
        for c in (declared_findings or [])
        if c in _DECLARED_TO_KPI
    }

    resolution = resolve_baseline(db, instrument_type, tenant_id)

    # ── Governance gate: no approved baseline → no final score ──────────────
    if not resolution["baseline_found"]:
        return {
            "analysis_status": "supervisor_review_required",
            "baseline_source": None,
            "baseline_match_score": None,
            "baseline_deviation_score": None,
            "inspection_score": None,
            "risk_level": None,
            "predicted_findings": [],
            "kpi_summary": {},
            "identification": {},
            "recommendation": (
                "No approved baseline found. Supervisor review required before final scoring."
            ),
            "message": "No approved baseline found. Supervisor review required before final scoring.",
            "human_review_required": True,
            "placeholder_scoring": True,
        }

    seed = _seed_from(image_sha256, f"{instrument_type}:{instrument_barcode or ''}")

    # ── KPI detection (contamination + condition) ───────────────────────────
    kpi_summary: dict[str, bool] = {}
    predicted_findings: list[dict[str, Any]] = []

    for idx, kpi in enumerate(CONTAMINATION_KPIS + CONDITION_KPIS):
        base = _pseudo(seed, idx)
        if kpi in declared:
            # Technician declared this finding — high probability.
            probability = round(0.55 + base * 0.40, 2)
            confidence = round(0.80 + base * 0.18, 2)
        else:
            # Low baseline probability from deterministic heuristic.
            probability = round(base * 0.12, 2)
            confidence = round(0.70 + base * 0.25, 2)

        present = probability >= 0.5
        kpi_summary[kpi] = present
        predicted_findings.append({
            "type": kpi,
            "probability": probability,
            "confidence": confidence,
            "severity": _severity(probability),
        })

    # ── Identification detection / match ────────────────────────────────────
    identification = {
        "barcode_detected": bool(instrument_barcode),
        "qr_udi_detected": bool(instrument_udi),
        "keydot_detected": bool(keydot_id),
        # Placeholder: a detected identifier is treated as a match against the
        # resolved baseline. Real CV will compare decoded values.
        "barcode_match": bool(instrument_barcode),
        "qr_udi_match": bool(instrument_udi),
        "keydot_match": bool(keydot_id),
    }

    # ── Baseline match / deviation ──────────────────────────────────────────
    # Deviation grows with declared/positive findings; match is its complement.
    deviation_seed = _pseudo(seed, 999)
    positive_count = sum(1 for v in kpi_summary.values() if v)
    deviation = min(0.04 + deviation_seed * 0.06 + positive_count * 0.08, 0.95)
    baseline_match_score = round(1.0 - deviation, 2)
    baseline_deviation_score = round(deviation, 2)

    # ── Inspection score ────────────────────────────────────────────────────
    # Start from baseline match, deduct weighted KPI penalties, add a small
    # identification-match bonus.
    score = baseline_match_score * 100.0
    for kpi, present in kpi_summary.items():
        if present:
            finding = next(f for f in predicted_findings if f["type"] == kpi)
            score -= _KPI_WEIGHT.get(kpi, 10) * finding["probability"]

    id_matches = sum(
        1 for k in ("barcode_match", "qr_udi_match", "keydot_match") if identification[k]
    )
    score += id_matches * 2.0
    inspection_score = max(0, min(100, round(score)))
    risk_level = _risk_level(inspection_score)

    # ── Recommendation (no causation language) ──────────────────────────────
    flagged = [k.replace("_", " ") for k, v in kpi_summary.items() if v]
    if not flagged:
        recommendation = "Accept inspection. No findings above threshold; routine processing recommended."
    elif risk_level in ("high", "critical"):
        recommendation = (
            f"Quality review recommended. Possible {', '.join(flagged)} — "
            "hold instrument for supervisor review before release."
        )
    else:
        recommendation = (
            f"Accept inspection with supervisor review of {', '.join(flagged)} finding(s)."
        )

    source = resolution["baseline_source"]
    return {
        "analysis_status": "completed",
        "baseline_source": source,
        "baseline_role": _baseline_role(source),
        "baseline_comparison_label": _baseline_comparison_label(source),
        "baseline_version": resolution["baseline_version"],
        "baseline_match_score": baseline_match_score,
        "baseline_deviation_score": baseline_deviation_score,
        "inspection_score": inspection_score,
        "risk_level": risk_level,
        "predicted_findings": predicted_findings,
        "kpi_summary": kpi_summary,
        "identification": identification,
        "recommendation": recommendation,
        "human_review_required": True,
        "placeholder_scoring": True,
    }
