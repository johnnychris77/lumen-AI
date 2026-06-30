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

# Human-readable KPI labels for findings summaries.
KPI_LABELS = {
    "blood": "blood", "bone": "bone", "tissue": "tissue", "bioburden": "bioburden",
    "debris": "debris", "other_organic_residue": "organic residue",
    "rust": "rust", "discoloration": "discoloration", "corrosion": "corrosion",
    "pitting": "pitting", "crack": "crack", "insulation_damage": "insulation damage",
    "missing_component": "missing component",
}

# Critical KPI thresholds (probability). Exceeding one drives risk up and changes
# the recommendation toward reprocess / supervisor review / remove from service.
_CRITICAL_THRESHOLDS = {
    "blood": 0.30, "bone": 0.30, "tissue": 0.30, "bioburden": 0.30,
    "rust": 0.60, "corrosion": 0.60, "crack": 0.30, "missing_component": 0.30,
}
# KPIs whose critical breach means the instrument should leave service.
_REMOVE_FROM_SERVICE = {"crack", "missing_component"}
# Contamination KPIs whose critical breach means reprocess + re-inspect.
_REPROCESS = {"blood", "bone", "tissue", "bioburden"}


def severity_from_probability(p: float) -> str:
    """0–10% None, 11–30% Low, 31–60% Moderate, 61%+ High (probability 0–1)."""
    pct = p * 100
    if pct <= 10:
        return "none"
    if pct <= 30:
        return "low"
    if pct <= 60:
        return "moderate"
    return "high"


def status_from_probability(p: float) -> str:
    """0–10% Clear, 11–30% Monitor, 31–60% Review, 61%+ Escalate (probability 0–1)."""
    pct = p * 100
    if pct <= 10:
        return "clear"
    if pct <= 30:
        return "monitor"
    if pct <= 60:
        return "review"
    return "escalate"


def _severity_index(p: float) -> int:
    """0–10% → 0, 11–30% → 1, 31–60% → 2, 61%+ → 3."""
    pct = p * 100
    if pct <= 10:
        return 0
    if pct <= 30:
        return 1
    if pct <= 60:
        return 2
    return 3


# KPI-specific severity scales. Findings not listed use the generic scale.
_SEVERITY_SCALES = {
    "blood": ["none", "trace", "visible", "heavy"],
    "rust": ["none", "surface rust", "moderate rust", "heavy rust"],
    "corrosion": ["none", "minor", "moderate", "severe"],
}
_GENERIC_SCALE = ["none", "low", "moderate", "high"]


def kpi_severity(kpi: str, p: float) -> str:
    """Return the severity label for a KPI using its specific scale when defined
    (blood: none/trace/visible/heavy, rust: none/surface/moderate/heavy rust,
    corrosion: none/minor/moderate/severe), else the generic scale."""
    scale = _SEVERITY_SCALES.get(kpi, _GENERIC_SCALE)
    return scale[_severity_index(p)]


def _finding_phrase(label: str, severity_index: int) -> str:
    if severity_index == 0:
        return f"No {label} detected"
    if severity_index == 1:
        return f"Minor {label} detected"
    if severity_index == 2:
        return f"{label.capitalize()} detected"
    return f"Significant {label} detected"

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

# Clinical risk tier per KPI (drives prioritisation + risk-driver explanation).
#   high           — contamination / structural integrity; aggressive score hit
#   severity_based — corrosion/rust: tier rises with severity (heavy → high)
#   low_medium     — bone (low unless organic contamination suspected)
#   low            — cosmetic / wear unless structural integrity affected
_RISK_TIER = {
    "blood": "high", "bioburden": "high", "tissue": "high",
    "other_organic_residue": "high", "crack": "high", "missing_component": "high",
    "insulation_damage": "high",
    "corrosion": "severity_based", "rust": "severity_based",
    "bone": "low_medium",
    "debris": "medium",
    "discoloration": "low", "pitting": "low",
}


def risk_tier(kpi: str, p: float) -> str:
    """Effective risk tier — severity-based KPIs (corrosion/rust) escalate to
    high at severe/heavy severity, medium at moderate, else low."""
    tier = _RISK_TIER.get(kpi, "medium")
    if tier == "severity_based":
        idx = _severity_index(p)
        return "high" if idx >= 3 else "medium" if idx == 2 else "low"
    return tier


# Per-KPI risk weight — how much a positive finding deducts from the score.
# Contamination (blood/bioburden/tissue/organic), cracks, and missing components
# deduct far more aggressively than cosmetic discoloration / wear.
_KPI_WEIGHT = {
    "blood": 36, "bioburden": 33, "tissue": 31, "other_organic_residue": 29,
    "crack": 38, "missing_component": 35, "insulation_damage": 30,
    "corrosion": 24, "rust": 18,            # severity scales via probability
    "bone": 16, "debris": 16,               # low–medium
    "discoloration": 5, "pitting": 10,      # cosmetic / wear
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


# Approval-status values that mean a baseline is cleared for scoring use.
_APPROVED_VALUES = {"approved", "active", "vendor_approved", "hospital_approved"}


def _resolve_from_library(db: Session, instrument_type: str) -> dict[str, Any] | None:
    """Check the network BaselineLibraryEntry table (manufacturer → vendor → hospital)."""
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
    return None


def _resolve_from_uploaded(db: Session, instrument_type: str) -> dict[str, Any] | None:
    """Check the baselines users actually upload/approve through the UI.

    The baseline upload + review workflow writes to
    EnterpriseVendorBaselineSubscription (keyed by instrument_category /
    instrument_name, with a per-record baseline_source of manufacturer /
    vendor / hospital). Without this bridge, uploaded baselines are invisible
    to the scoring engine and every image inspection falls through to
    supervisor review.

    Matches case-insensitively on instrument_category OR instrument_name and
    only accepts records whose approval/baseline status is cleared for scoring.
    Honours the manufacturer → vendor → hospital priority by source.
    """
    from sqlalchemy import func, or_
    from app.models.enterprise_quality import EnterpriseVendorBaselineSubscription as Sub

    needle = instrument_type.replace("_", " ").lower()

    rows = (
        db.query(Sub)
        .filter(
            or_(
                func.lower(Sub.instrument_category) == instrument_type.lower(),
                func.lower(Sub.instrument_category) == needle,
                func.lower(Sub.instrument_name) == needle,
            )
        )
        .all()
    )

    approved = [
        r for r in rows
        if (r.approval_status or "").lower() in _APPROVED_VALUES
        or (r.baseline_status or "").lower() in _APPROVED_VALUES
    ]
    if not approved:
        return None

    # Pick by source priority: manufacturer first, then vendor, then hospital.
    def _priority(r) -> int:
        src = (r.baseline_source or "vendor").lower()
        return BASELINE_PRIORITY.index(src) if src in BASELINE_PRIORITY else len(BASELINE_PRIORITY)

    best = min(approved, key=_priority)
    source = (best.baseline_source or "vendor").lower()
    if source not in BASELINE_PRIORITY:
        source = "vendor"
    return {
        "baseline_found": True,
        "baseline_source": source,
        "baseline_entry_id": best.id,
        "baseline_version": best.baseline_version,
    }


def resolve_baseline(db: Session, instrument_type: str, tenant_id: str) -> dict[str, Any]:
    """Resolve the most authoritative approved baseline for an instrument.

    Looks in two places so the engine sees baselines wherever they live:
      1. The network BaselineLibraryEntry table.
      2. The EnterpriseVendorBaselineSubscription table that the baseline
         upload + review UI actually populates.
    Both honour manufacturer → vendor → hospital priority. Returns the first
    approved match.
    """
    resolution = _resolve_from_library(db, instrument_type)
    if resolution is not None:
        return resolution

    resolution = _resolve_from_uploaded(db, instrument_type)
    if resolution is not None:
        return resolution

    return {
        "baseline_found": False,
        "baseline_source": None,
        "baseline_entry_id": None,
        "baseline_version": None,
    }


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
            "label": KPI_LABELS.get(kpi, kpi),
            "probability": probability,
            "confidence": confidence,
            # KPI-specific severity scale (blood: trace/visible/heavy,
            # rust: surface/moderate/heavy, corrosion: minor/moderate/severe).
            "severity": kpi_severity(kpi, probability),
            "severity_index": _severity_index(probability),
            "status": status_from_probability(probability),
            "risk_tier": risk_tier(kpi, probability),
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
    score_adjustments: list[dict[str, Any]] = []
    for kpi, present in kpi_summary.items():
        if present:
            finding = next(f for f in predicted_findings if f["type"] == kpi)
            deduction = round(_KPI_WEIGHT.get(kpi, 10) * finding["probability"], 1)
            score -= deduction
            score_adjustments.append({
                "kpi": kpi,
                "label": KPI_LABELS.get(kpi, kpi),
                "points": -deduction,
                "severity": finding["severity"],
                "risk_tier": finding["risk_tier"],
            })
    score_adjustments.sort(key=lambda a: a["points"])  # largest deduction first

    id_matches = sum(
        1 for k in ("barcode_match", "qr_udi_match", "keydot_match") if identification[k]
    )
    score += id_matches * 2.0
    inspection_score = max(0, min(100, round(score)))

    # ── Per-finding probability map for downstream logic ────────────────────
    prob = {f["type"]: f["probability"] for f in predicted_findings}

    # ── Critical KPI breaches drive risk + recommendation ───────────────────
    critical_flags = [
        kpi for kpi, thresh in _CRITICAL_THRESHOLDS.items()
        if prob.get(kpi, 0.0) > thresh
    ]
    remove_flags = [k for k in critical_flags if k in _REMOVE_FROM_SERVICE]
    reprocess_flags = [k for k in critical_flags if k in _REPROCESS]

    if remove_flags:
        risk_level = "critical"
    elif critical_flags:
        risk_level = "high"
    else:
        risk_level = _risk_level(inspection_score)

    pass_fail = "FAIL" if critical_flags else "PASS"

    # ── Findings summary (one line per key KPI) ─────────────────────────────
    summary_kpis = ["blood", "bone", "tissue", "bioburden", "corrosion", "rust", "discoloration", "crack"]
    findings_summary: list[str] = []
    if not critical_flags:
        findings_summary.append("No critical contamination detected")
    for kpi in summary_kpis:
        findings_summary.append(_finding_phrase(KPI_LABELS[kpi], _severity_index(prob.get(kpi, 0.0))))

    # ── Recommendation (no causation language) ──────────────────────────────
    if remove_flags:
        names = ", ".join(KPI_LABELS[k] for k in remove_flags)
        recommendation = (
            f"Remove from service — possible {names} indicates a structural integrity concern. "
            "Supervisor review required before any further use."
        )
    elif reprocess_flags:
        names = ", ".join(KPI_LABELS[k] for k in reprocess_flags)
        recommendation = (
            f"Reprocess and re-inspect — possible {names} above the contamination threshold. "
            "Supervisor review required before release."
        )
    elif critical_flags:
        names = ", ".join(KPI_LABELS[k] for k in critical_flags)
        recommendation = (
            f"Supervisor review recommended — possible {names} above threshold. "
            "Hold instrument until reviewed."
        )
    else:
        recommendation = "Accept inspection. Continue routine processing."

    # ── PASS/FAIL reason bullets ────────────────────────────────────────────
    reason: list[str] = [
        f"Manufacturer baseline matched at {round(baseline_match_score * 100)}%."
        if resolution["baseline_source"] == "manufacturer"
        else f"{BASELINE_LABELS.get(resolution['baseline_source'], 'Baseline')} matched at "
             f"{round(baseline_match_score * 100)}%."
    ]
    for kpi in ["blood", "bone", "tissue", "corrosion", "crack"]:
        reason.append(_finding_phrase(KPI_LABELS[kpi], _severity_index(prob.get(kpi, 0.0))) + ".")
    if critical_flags:
        reason.append(
            "One or more findings exceeded the escalation threshold: "
            + ", ".join(KPI_LABELS[k] for k in critical_flags) + "."
        )
    else:
        reason.append("All findings below escalation thresholds.")

    # ── Overall confidence ──────────────────────────────────────────────────
    confidences = [f["confidence"] for f in predicted_findings] or [0.8]
    overall_conf = round(sum(confidences) / len(confidences), 2)
    if overall_conf >= 0.85:
        confidence_level = "High"
    elif overall_conf >= 0.70:
        confidence_level = "Medium"
    else:
        confidence_level = "Low"

    # ── Explainability ──────────────────────────────────────────────────────
    top_findings = sorted(predicted_findings, key=lambda f: f["probability"], reverse=True)[:3]
    # Risk drivers: prefer critical breaches, else the largest score deductions.
    if critical_flags:
        risk_drivers = [KPI_LABELS.get(k, k) for k in critical_flags]
    elif score_adjustments:
        risk_drivers = [a["label"] for a in score_adjustments[:3]]
    else:
        risk_drivers = ["No KPI above escalation threshold"]
    primary_risk_driver = risk_drivers[0] if risk_drivers else None

    explainability = {
        "baseline_source": resolution["baseline_source"],
        "baseline_match_score": baseline_match_score,
        "highest_findings": [
            {"type": f["type"], "label": KPI_LABELS.get(f["type"], f["type"]),
             "probability": f["probability"], "severity": f["severity"],
             "risk_tier": f["risk_tier"]}
            for f in top_findings
        ],
        "primary_risk_driver": primary_risk_driver,
        "risk_drivers": risk_drivers,
        "score_adjustments": score_adjustments,
        "confidence_level": confidence_level,
        "rationale": (
            "Score starts from the approved baseline match, then each KPI finding deducts "
            "points weighted by its clinical risk tier (contamination, cracks, and missing "
            "components deduct most; cosmetic discoloration and wear deduct least). Risk and "
            "recommendation are driven by whether any KPI exceeds its escalation threshold."
        ),
    }

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
        "pass_fail": pass_fail,
        "predicted_findings": predicted_findings,
        "kpi_summary": kpi_summary,
        "identification": identification,
        "findings_summary": findings_summary,
        "confidence": overall_conf,
        "confidence_level": confidence_level,
        "recommendation": recommendation,
        "reason": reason,
        "critical_flags": critical_flags,
        "score_adjustments": score_adjustments,
        "primary_risk_driver": explainability["primary_risk_driver"],
        "explainability": explainability,
        "human_review_required": True,
        "placeholder_scoring": True,
        "model_label": "Baseline Comparison Scoring Model (pilot)",
        "production_validated": False,
    }
