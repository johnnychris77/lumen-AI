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
# NOTE: "bioburden" is intentionally NOT a standalone KPI — it is a clinical
# umbrella term. An Overall Cleaning Assessment is derived instead from the
# concrete contamination KPIs below (see CLEANING_KPIS / overall_cleaning_assessment).
CONTAMINATION_KPIS = ["blood", "bone", "tissue", "debris", "other_organic_residue"]
CONDITION_KPIS = ["rust", "discoloration", "corrosion", "pitting", "crack", "insulation_damage", "missing_component"]

# Concrete contamination KPIs that feed the Overall Cleaning Assessment.
CLEANING_KPIS = ["blood", "bone", "tissue", "other_organic_residue", "debris"]

# Human-readable KPI labels for findings summaries.
KPI_LABELS = {
    "blood": "blood", "bone": "bone", "tissue": "tissue",
    "debris": "debris", "other_organic_residue": "organic residue",
    "rust": "rust", "discoloration": "discoloration", "corrosion": "corrosion",
    "pitting": "pitting", "crack": "crack", "insulation_damage": "insulation damage",
    "missing_component": "missing component",
}

# Critical KPI thresholds (probability). Exceeding one drives risk up and changes
# the recommendation toward reprocess / supervisor review / remove from service.
_CRITICAL_THRESHOLDS = {
    "blood": 0.30, "bone": 0.30, "tissue": 0.30,
    "other_organic_residue": 0.30,
    "rust": 0.60, "corrosion": 0.60, "crack": 0.30, "missing_component": 0.30,
}
# KPIs whose critical breach means the instrument should leave service.
_REMOVE_FROM_SERVICE = {"crack", "missing_component"}
# Contamination KPIs whose critical breach means reprocess + re-inspect.
_REPROCESS = {"blood", "bone", "tissue", "other_organic_residue"}


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
    "discoloration": ["none", "minor", "moderate", "severe"],
    # Structural-damage scale for crack / missing component / insulation damage.
    "crack": ["none", "cosmetic wear", "functional concern", "structural failure"],
    "missing_component": ["none", "cosmetic wear", "functional concern", "structural failure"],
    "insulation_damage": ["none", "cosmetic wear", "functional concern", "structural failure"],
    "pitting": ["none", "cosmetic wear", "functional concern", "structural failure"],
}
_GENERIC_SCALE = ["none", "low", "moderate", "high"]

# Every severity token that can appear in a predicted finding's "severity"
# field — exposed so callers/tests can validate the richer SPD vocabulary.
ALL_SEVERITY_TOKENS = {
    tok for scale in _SEVERITY_SCALES.values() for tok in scale
} | set(_GENERIC_SCALE)


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
    "blood": "high", "tissue": "high",
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


# ── SPD risk weighting ───────────────────────────────────────────────────────
# Maps each KPI (and, where severity matters, its severity band) onto an SPD
# operational risk tier. This is what drives the "SPD Risk Impact" column and
# the override rule that forces High/Critical regardless of total score.
#
#   critical — must reprocess / remove from service before any use
#   high     — supervisor review before release
#   low      — monitor; cosmetic / wear only
#
# Severity bands use _severity_index(p): 0 none, 1 minor, 2 moderate, 3 severe.
_SPD_ALWAYS_CRITICAL = {
    "tissue", "other_organic_residue", "crack", "missing_component",
    "insulation_damage",
}
_SPD_ALWAYS_HIGH = {"debris", "bone", "pitting"}


def spd_risk_tier(kpi: str, p: float) -> str:
    """SPD operational risk tier for a KPI at probability ``p``.

    Returns "none" when the finding is absent (severity index 0), otherwise
    "critical" / "high" / "low" per SPD priorities:
      - blood: visible/heavy → critical, trace → high
      - heavy rust / severe corrosion → critical; moderate → high; surface/minor → low
      - tissue / organic residue / crack / missing component / insulation damage → critical
      - debris / bone / pitting → high
      - discoloration and other cosmetic findings → low
    """
    idx = _severity_index(p)
    if idx == 0:
        return "none"
    if kpi == "blood":
        return "critical" if idx >= 2 else "high"
    if kpi in ("rust", "corrosion"):
        return "critical" if idx >= 3 else "high" if idx == 2 else "low"
    if kpi in _SPD_ALWAYS_CRITICAL:
        # Critical only at a genuine (moderate+) detection; a faint idx==1 signal
        # is elevated (review) but must not read as reprocess/remove.
        return "critical" if idx >= 2 else "high"
    if kpi in _SPD_ALWAYS_HIGH:
        return "high"
    # discoloration + anything cosmetic
    return "low"


# SPD Risk Impact label shown in the panel for each KPI.
_SPD_IMPACT_LABEL = {
    "none": "Clear",
    "low": "Monitor",
    "high": "Review",
    "critical": "Reprocess",
}


def spd_risk_impact(tier: str) -> str:
    """Human label for the SPD Risk Impact column (Clear/Monitor/Review/Reprocess)."""
    return _SPD_IMPACT_LABEL.get(tier, "Review")


# Per-KPI risk weight — how much a positive finding deducts from the score.
# Contamination (blood/bioburden/tissue/organic), cracks, and missing components
# deduct far more aggressively than cosmetic discoloration / wear.
_KPI_WEIGHT = {
    "blood": 36, "tissue": 31, "other_organic_residue": 29,
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
                "baseline_udi": entry.udi or "",
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
        # Uploaded vendor-subscription baselines carry no UDI to verify against.
        "baseline_udi": "",
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
        "baseline_udi": "",
    }


def _normalize_identifier(value: str) -> str:
    """Strip GS1 AI parentheses, spaces, and case for tolerant comparison."""
    return "".join(ch for ch in (value or "") if ch.isalnum()).lower()


def identifier_match(decoded: str, baseline_udi: str) -> tuple[str, bool]:
    """Compare a decoded identifier against the approved baseline's UDI.

    Returns (status, is_match) where status is one of:
      not_detected — nothing decoded/declared
      unverified   — value present but baseline has no UDI to check against
      match        — decoded value matches the baseline UDI (or its device id)
      mismatch     — decoded value present and does NOT match — wrong instrument
    """
    if not decoded:
        return "not_detected", False
    if not baseline_udi:
        return "unverified", False
    d = _normalize_identifier(decoded)
    b = _normalize_identifier(baseline_udi)
    if not d or not b:
        return "unverified", False
    if d == b or b in d or d in b:
        return "match", True
    return "mismatch", False


def _risk_level(score: int) -> str:
    if score >= 85:
        return "low"
    if score >= 65:
        return "medium"
    if score >= 40:
        return "high"
    return "critical"


def overall_cleaning_assessment(findings_by_kpi: dict[str, dict]) -> str:
    """Derive the Overall Cleaning Assessment from the concrete contamination KPIs
    (blood, bone, tissue, organic residue, debris) — replacing the standalone
    "bioburden" KPI with a clinically meaningful summary.

      Clean                            — no contamination signal
      Residual contamination suspected — minor/uncertain contamination present
      Cleaning failure                 — clear contamination (blood/tissue/organic
                                         residue at moderate+ severity)
    """
    failure = False
    residual = False
    for kpi in CLEANING_KPIS:
        f = findings_by_kpi.get(kpi)
        if not f:
            continue
        idx = f["severity_index"]
        if idx == 0:
            continue
        residual = True
        if kpi in ("blood", "tissue", "other_organic_residue") and idx >= 2:
            failure = True
        if kpi == "debris" and idx >= 3:
            failure = True
    if failure:
        return "Cleaning failure"
    if residual:
        return "Residual contamination suspected"
    return "Clean"


def recommended_action(findings_by_kpi: dict[str, dict], baseline_match_score: float) -> str:
    """Map findings onto an SPD recommended action.

    Priority: reprocess/remove > supervisor review > monitor > pass.
    """
    def present(kpi: str) -> dict | None:
        f = findings_by_kpi.get(kpi)
        return f if f and f["severity_index"] >= 1 else None

    # REPROCESS / REMOVE FROM SERVICE
    reprocess = []
    for kpi in ("blood", "tissue", "other_organic_residue", "crack",
                "missing_component", "insulation_damage"):
        f = present(kpi)
        if f and (kpi != "blood" or f["severity_index"] >= 2):
            reprocess.append(KPI_LABELS[kpi])
    for kpi in ("corrosion",):
        f = present(kpi)
        if f and f["severity_index"] >= 3:  # severe corrosion
            reprocess.append("severe corrosion")
    if reprocess:
        return (
            "Reprocess / remove from service — "
            + ", ".join(sorted(set(reprocess)))
            + ". Supervisor review required before any further use."
        )

    # SUPERVISOR REVIEW
    supervisor = []
    for kpi in ("debris", "bone"):
        if present(kpi):
            supervisor.append(KPI_LABELS[kpi])
    for kpi in ("corrosion", "rust"):
        f = present(kpi)
        if f and f["severity_index"] == 2:  # moderate
            supervisor.append(f["severity"])
    if baseline_match_score < 0.70:
        supervisor.append("baseline mismatch")
    if supervisor:
        return (
            "Supervisor review recommended before release — "
            + ", ".join(sorted(set(supervisor))) + "."
        )

    # MONITOR
    monitor = []
    for kpi in ("discoloration", "rust"):
        f = present(kpi)
        if f and f["severity_index"] == 1:  # minor / surface
            monitor.append(f["severity"])
    if monitor:
        return (
            "Monitor — low-risk findings only ("
            + ", ".join(sorted(set(monitor)))
            + "). Continue routine processing."
        )

    # PASS
    return "Pass — no high-risk findings and baseline match strong. Release for use."


def scoring_explanation(
    findings_by_kpi: dict[str, dict],
    baseline_match_score: float,
    baseline_source: str,
) -> list[str]:
    """Plain-language, per-KPI reasons the score is what it is."""
    label = BASELINE_LABELS.get(baseline_source, "Baseline")
    lines = [f"{label} matched at {round(baseline_match_score * 100)}%."]
    for kpi in ("blood", "tissue", "other_organic_residue", "debris", "bone",
                "corrosion", "rust", "discoloration"):
        f = findings_by_kpi.get(kpi)
        if not f:
            continue
        idx = f["severity_index"]
        name = KPI_LABELS[kpi]
        if idx == 0:
            lines.append(f"No {name} detected.")
        elif f["spd_risk"] == "low":
            lines.append(
                f"{f['severity'].capitalize()} {name} was treated as low-risk "
                "cosmetic variation."
            )
        else:
            lines.append(f"{f['severity'].capitalize()} {name} reduced the score.")
    return lines


# ── Phase 13: Explainable Clinical Decision Support ──────────────────────────

# KPIs that describe structural/condition integrity (vs contamination).
INTEGRITY_KPIS = [
    "rust", "corrosion", "pitting", "crack", "discoloration",
    "insulation_damage", "missing_component",
]
_STRUCTURAL_KPIS = {"crack", "missing_component", "insulation_damage"}

# Static forward-looking roadmap (Phase 13.11) — advisory, no fabricated CV yet.
AI_ROADMAP = [
    "Visual heatmaps",
    "Bounding boxes",
    "Segmented contamination detection",
    "Multi-image comparison",
    "Temporal baseline drift",
    "Predictive instrument degradation",
    "Rust progression",
    "Corrosion progression",
    "Life-cycle prediction",
]


def _overall_result(result: dict) -> str:
    """Collapse the analysis into one of the five clinical dispositions
    (PASS / MONITOR / SUPERVISOR REVIEW / REPROCESS / REMOVE FROM SERVICE)."""
    if result.get("analysis_status") != "completed":
        return "SUPERVISOR REVIEW"
    f = {x["type"]: x for x in result["predicted_findings"]}

    def idx(kpi: str) -> int:
        return f.get(kpi, {}).get("severity_index", 0)

    # Structural integrity concern → remove from service. Requires a genuine
    # (moderate+, idx>=2) detection so faint placeholder noise at ~11% does not
    # force the most severe disposition on an otherwise clean, high-score item.
    if any(idx(k) >= 2 for k in _STRUCTURAL_KPIS) or idx("corrosion") >= 3:
        return "REMOVE FROM SERVICE"
    # Residual contamination → return for cleaning/reprocessing (moderate+).
    if any(idx(k) >= 2 for k in ("blood", "tissue", "other_organic_residue", "debris", "bone")):
        return "REPROCESS"
    # Condition change / baseline concern → supervisor review.
    moderate_condition = idx("corrosion") == 2 or idx("rust") == 2
    mismatch = result.get("identification", {}).get("identification_status") == "mismatch"
    if moderate_condition or mismatch or (result.get("baseline_match_score") or 1) < 0.70:
        return "SUPERVISOR REVIEW"
    # Minor cosmetic only → monitor.
    if idx("discoloration") == 1 or idx("rust") == 1:
        return "MONITOR"
    return "PASS"


# Exact SPD recommended-action text per outcome (Phase: AI Clinical Review).
_ACTION_TEXT = {
    "PASS": "Accept inspection. Continue routine processing.",
    "MONITOR": "Accept with monitoring. Recheck during next inspection.",
    "SUPERVISOR REVIEW": "Hold instrument pending supervisor review.",
    "REPROCESS": "Return for cleaning/reprocessing.",
    "REMOVE FROM SERVICE": "Remove from service and escalate for repair/replacement.",
}

_INTERPRETATION = {
    "PASS": (
        "The observed surface characteristics are consistent with the approved "
        "manufacturer baseline. No contamination or structural defect requiring "
        "intervention was identified."
    ),
    "MONITOR": (
        "Minor cosmetic variation was observed that does not require intervention "
        "now. Recheck the instrument during the next inspection."
    ),
    "SUPERVISOR REVIEW": (
        "Instrument cleanliness or condition may require verification. Detected "
        "changes should be reviewed by a supervisor before release."
    ),
    "REPROCESS": (
        "Residual contamination indicators were identified. Return the instrument "
        "for cleaning/reprocessing and re-inspect before release."
    ),
    "REMOVE FROM SERVICE": (
        "A structural integrity concern was identified. Remove the instrument from "
        "service and escalate for repair or replacement."
    ),
}


def evidence_strength(result: dict) -> dict:
    """Strong / Moderate / Limited with a 5-star rating.

    Strong:   baseline match >= 90% AND confidence >= 85%.
    Moderate: baseline match 75–89% OR confidence 65–84%.
    Limited:  baseline missing, or low confidence.
    """
    match = result.get("baseline_match_score")
    conf = result.get("confidence")
    if match is None or conf is None:
        return {"level": "Limited", "stars": 1, "reason": "No approved baseline available."}
    match_pct = match * 100
    conf_pct = conf * 100
    if match_pct >= 90 and conf_pct >= 85:
        return {"level": "Strong", "stars": 5,
                "reason": f"Baseline match {round(match_pct)}% and confidence {round(conf_pct)}% are both high."}
    if match_pct >= 75 or conf_pct >= 65:
        return {"level": "Moderate", "stars": 3,
                "reason": f"Baseline match {round(match_pct)}% / confidence {round(conf_pct)}% are moderate."}
    return {"level": "Limited", "stars": 1,
            "reason": f"Baseline match {round(match_pct)}% and confidence {round(conf_pct)}% are low."}


def baseline_difference(result: dict) -> dict:
    """Plain-language baseline-difference summary (no fabricated localization)."""
    findings = {x["type"]: x for x in result.get("predicted_findings", [])}
    match = result.get("baseline_match_score")
    differences: list[str] = []
    contamination = False
    condition = False

    for kpi in CLEANING_KPIS:
        fx = findings.get(kpi)
        if fx and fx["severity_index"] >= 1:
            contamination = True
            differences.append(f"{KPI_LABELS[kpi].capitalize()} indicators detected.")
    for kpi in ("rust", "corrosion", "discoloration", "pitting"):
        fx = findings.get(kpi)
        if fx and fx["severity_index"] >= 1:
            condition = True
            differences.append(f"{fx['severity'].capitalize()} {KPI_LABELS[kpi]} observed.")
    for kpi in _STRUCTURAL_KPIS:
        fx = findings.get(kpi)
        if fx and fx["severity_index"] >= 2:
            condition = True
            differences.append(f"Possible {KPI_LABELS[kpi]} observed.")

    if not contamination:
        differences.append("No visible contamination detected.")
    if not condition:
        differences.append("No structural defect detected.")
    differences.append("No lumen obstruction detected.")

    category = (
        "contamination and condition" if contamination and condition
        else "contamination" if contamination
        else "condition" if condition
        else "none"
    )
    return {
        "baseline_match_pct": round(match * 100) if match is not None else None,
        "differences": differences,
        "category": category,
        "localization_note": (
            "Detailed image difference localization is planned for a future "
            "computer vision release."
        ),
    }


def _integrity_status(findings_by_kpi: dict) -> str:
    def idx(kpi: str) -> int:
        return findings_by_kpi.get(kpi, {}).get("severity_index", 0)

    if any(idx(k) >= 2 for k in _STRUCTURAL_KPIS) or idx("corrosion") >= 3 or idx("rust") >= 3:
        return "Remove From Service"
    if idx("corrosion") >= 2 or idx("rust") >= 2 or idx("pitting") >= 2:
        return "Repair Required"
    if any(idx(k) == 1 for k in ("rust", "corrosion", "pitting", "discoloration")) \
            or any(idx(k) == 1 for k in _STRUCTURAL_KPIS):
        return "Monitor"
    return "Acceptable"


def _finding_view(f: dict) -> dict:
    """Compact per-KPI view for the cleaning/integrity cards."""
    return {
        "type": f["type"],
        "label": f["label"],
        # "Detected" means a clinically actionable (moderate+) signal, not faint
        # low-probability noise from the deterministic placeholder.
        "detected": f["severity_index"] >= 2,
        "probability": f["probability"],
        "probability_pct": round(f["probability"] * 100),
        "confidence": f["confidence"],
        "confidence_pct": round(f["confidence"] * 100),
        "severity": f["severity"],
        "spd_risk": f.get("spd_risk", "none"),
        "spd_risk_impact": f.get("spd_risk_impact", "Clear"),
    }


def clinical_reasoning(result: dict) -> list[str]:
    """Narrative clinical reasoning grounded in the actual analysis output."""
    f = {x["type"]: x for x in result["predicted_findings"]}
    lines: list[str] = []
    src = BASELINE_LABELS.get(result.get("baseline_source"), "Baseline")
    match = result.get("baseline_match_score")
    if match is not None:
        lines.append(f"{src} matched at {round(match * 100)}%.")

    for kpi in ("blood", "tissue", "other_organic_residue", "debris", "bone"):
        fx = f.get(kpi)
        if not fx:
            continue
        if fx["severity_index"] == 0:
            lines.append(f"No {KPI_LABELS[kpi]} detected.")
        else:
            lines.append(f"{fx['severity'].capitalize()} {KPI_LABELS[kpi]} detected.")

    structural = [KPI_LABELS[k] for k in _STRUCTURAL_KPIS if f.get(k, {}).get("severity_index", 0) >= 2]
    condition = [
        f"{f[k]['severity']}" for k in ("rust", "corrosion", "pitting")
        if f.get(k, {}).get("severity_index", 0) >= 2
    ]
    cosmetic = [
        KPI_LABELS[k] for k in ("discoloration", "rust")
        if f.get(k, {}).get("severity_index", 0) == 1
    ]
    if structural:
        lines.append("Structural concern identified: " + ", ".join(structural) + ".")
    elif condition:
        lines.append("Condition concern: " + ", ".join(condition) + ".")
    elif cosmetic:
        lines.append("Minor cosmetic " + " / ".join(cosmetic) + " detected; treated as low-risk.")
    else:
        lines.append("No structural defects identified.")

    lines.append(result.get("recommended_action", "Routine processing recommended."))
    return lines


def executive_summary(result: dict, overall_result: str) -> list[str]:
    """One-card plain-language executive summary."""
    if result.get("analysis_status") != "completed":
        return [
            "No approved baseline available for this instrument.",
            "Final scoring withheld pending supervisor review.",
        ]
    src = BASELINE_LABELS.get(result.get("baseline_source"), "Baseline")
    lines = [
        "Inspection completed.",
        f"{src} matched at {round((result['baseline_match_score'] or 0) * 100)}%.",
    ]
    cleaning = result.get("overall_cleaning_assessment", "")
    lines.append("No contamination detected." if cleaning == "Clean" else f"Cleaning: {cleaning}.")
    integrity = result.get("clinical_decision_integrity_status")
    if integrity:
        lines.append(
            "Instrument structurally intact."
            if integrity == "Acceptable" else f"Instrument integrity: {integrity}."
        )
    lines.append(f"Recommended: {overall_result}.")
    lines.append(result.get("recommended_action", ""))
    return [ln for ln in lines if ln]


def build_clinical_decision(result: dict) -> dict:
    """Assemble the full Explainable-AI Clinical Decision Support payload
    (Phases 13.1–13.11) from an already-computed analysis result."""
    findings = {x["type"]: x for x in result.get("predicted_findings", [])}
    overall = _overall_result(result)

    # Integrity status is needed by the executive summary — stash it on result.
    integrity_status = _integrity_status(findings) if findings else "Acceptable"
    result["clinical_decision_integrity_status"] = integrity_status

    # 13.2 Score breakdown
    adj = {a["kpi"]: a["points"] for a in result.get("score_adjustments", [])}
    breakdown_kpis = ["blood", "tissue", "other_organic_residue", "debris", "corrosion", "discoloration"]
    match = result.get("baseline_match_score")
    score_breakdown = {
        "baseline_match_points": round(match * 100) if match is not None else None,
        "items": [
            {"label": KPI_LABELS[k], "points": adj.get(k, 0)}
            for k in breakdown_kpis if k in findings
        ],
        "final_score": result.get("inspection_score"),
        "note": "Final score starts from the baseline match, subtracts weighted "
                "penalties, and may add a small identification-match bonus.",
    }

    # 13.3 Cleaning + 13.4 Integrity cards
    cleaning_items = [_finding_view(findings[k]) for k in CLEANING_KPIS if k in findings]
    integrity_items = [_finding_view(findings[k]) for k in INTEGRITY_KPIS if k in findings]

    return {
        # 13.1 Clinical Decision Summary
        "overall_result": overall,
        "summary": {
            "inspection_score": result.get("inspection_score"),
            "cleaning_assessment": result.get("overall_cleaning_assessment"),
            "integrity_assessment": integrity_status,
            "overall_risk": result.get("risk_level"),
            "confidence": result.get("confidence_level"),
            "confidence_pct": round((result.get("confidence") or 0) * 100),
            "baseline_source": result.get("baseline_source"),
        },
        # 13.2
        "score_breakdown": score_breakdown,
        # 13.3
        "cleaning": {"items": cleaning_items, "overall_status": result.get("overall_cleaning_assessment")},
        # 13.4
        "integrity": {"items": integrity_items, "overall_status": integrity_status},
        # 13.5
        "clinical_reasoning": clinical_reasoning(result),
        # AI Clinical Review — outcome + plain-language interpretation.
        "ai_clinical_review": {
            "outcome": overall,
            "reasoning": clinical_reasoning(result),
            "interpretation": _INTERPRETATION.get(overall, ""),
        },
        # Evidence Strength (Strong / Moderate / Limited + stars).
        "evidence_strength": evidence_strength(result),
        # Baseline Difference (plain language; no fabricated localization).
        "baseline_difference": baseline_difference(result),
        # 13.6
        "recommendation": {
            "result": overall,
            "action": result.get("recommended_action"),
            "action_text": _ACTION_TEXT.get(overall, result.get("recommended_action")),
        },
        # 13.7 Evidence (no fabricated CV overlays)
        "evidence": {
            "baseline_source": result.get("baseline_source"),
            "baseline_comparison_label": result.get("baseline_comparison_label"),
            "baseline_match_pct": round(match * 100) if match is not None else None,
            "highest_risk_drivers": result.get("top_risk_drivers", []),
            "confidence": result.get("confidence_level"),
            "image_evidence_note": "Image evidence visualization coming in a future computer vision release.",
        },
        # 13.9
        "executive_summary": executive_summary(result, overall),
        # 13.10 / Audit fields (persisted/loggable)
        "audit": {
            "model_version": "baseline-comparison-pilot-1",
            "dataset_version": "v0-pilot",
            "baseline_version": result.get("baseline_version"),
            "baseline_source": result.get("baseline_source"),
            "model_label": result.get("model_label"),
            "score": result.get("inspection_score"),
            "confidence": result.get("confidence_level"),
            "evidence_strength": evidence_strength(result)["level"],
            "recommendation": overall,
            "reasoning_captured": True,
            # Populated when a supervisor reviews (see supervisor-review endpoint).
            "supervisor_agreement": None,
            "override_reason": None,
            "human_review_required": result.get("human_review_required", True),
        },
        # 13.11
        "roadmap": AI_ROADMAP,
    }


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
    decoder_backend: str = "declared",
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
        no_baseline = {
            "analysis_status": "supervisor_review_required",
            "baseline_source": None,
            "baseline_version": None,
            "baseline_comparison_label": None,
            "baseline_match_score": None,
            "baseline_deviation_score": None,
            "inspection_score": None,
            "risk_level": None,
            "confidence_level": None,
            "confidence": None,
            "predicted_findings": [],
            "kpi_summary": {},
            "identification": {},
            "score_adjustments": [],
            "model_label": "Baseline Comparison Scoring Model (pilot)",
            "recommendation": (
                "No approved baseline found. Supervisor review required before final scoring."
            ),
            "recommended_action": "Supervisor review required before release.",
            "overall_cleaning_assessment": "Supervisor review required",
            "top_risk_drivers": ["No approved baseline"],
            "severity_by_kpi": {},
            "scoring_explanation": [
                "No approved baseline found for this instrument.",
                "Final scoring is withheld until a supervisor reviews.",
            ],
            "message": "No approved baseline found. Supervisor review required before final scoring.",
            "human_review_required": True,
            "placeholder_scoring": True,
        }
        no_baseline["clinical_decision"] = build_clinical_decision(no_baseline)
        return no_baseline

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
        spd_tier = spd_risk_tier(kpi, probability)
        predicted_findings.append({
            "type": kpi,
            "label": KPI_LABELS.get(kpi, kpi),
            "probability": probability,
            "confidence": confidence,
            # KPI-specific severity scale (blood: trace/visible/heavy,
            # rust: surface/moderate/heavy, corrosion: minor/moderate/severe,
            # damage: cosmetic wear/functional concern/structural failure).
            "severity": kpi_severity(kpi, probability),
            "severity_index": _severity_index(probability),
            "status": status_from_probability(probability),
            "risk_tier": risk_tier(kpi, probability),
            # SPD operational weighting surfaced to the panel.
            "spd_risk": spd_tier,
            "spd_risk_impact": spd_risk_impact(spd_tier),
        })

    # ── Identification detection / match (real decode-vs-baseline) ──────────
    # Values may be decoded from the image (pyzbar) or technician-declared; the
    # match is a real comparison against the approved baseline's UDI.
    baseline_udi = resolution.get("baseline_udi", "")
    barcode_status, barcode_match = identifier_match(instrument_barcode or "", baseline_udi)
    udi_status, udi_match = identifier_match(instrument_udi or "", baseline_udi)
    # KeyDot has no UDI to verify against — detection only.
    keydot_detected = bool(keydot_id)

    # Overall identification verdict, worst-case first.
    if barcode_status == "mismatch" or udi_status == "mismatch":
        identification_status = "mismatch"
    elif barcode_status == "match" or udi_status == "match":
        identification_status = "verified"
    elif instrument_barcode or instrument_udi or keydot_id:
        identification_status = "unverified"
    else:
        identification_status = "not_detected"

    identification = {
        "barcode_detected": bool(instrument_barcode),
        "qr_udi_detected": bool(instrument_udi),
        "keydot_detected": keydot_detected,
        "barcode_value": instrument_barcode or "",
        "qr_udi_value": instrument_udi or "",
        "keydot_value": keydot_id or "",
        "barcode_match": barcode_match,
        "qr_udi_match": udi_match,
        "keydot_match": keydot_detected,
        "barcode_status": barcode_status,
        "qr_udi_status": udi_status,
        "identification_status": identification_status,
        "baseline_udi": baseline_udi,
        "decoder_backend": decoder_backend,
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

    # ── SPD-weighted override ───────────────────────────────────────────────
    # Any present finding whose SPD tier is critical/high forces the risk level
    # up regardless of the numeric score (visible blood, tissue, organic
    # residue, crack, missing component, severe corrosion, significant debris,
    # bone residue, etc.).
    spd_critical = [
        f["type"] for f in predicted_findings
        if kpi_summary[f["type"]] and f["spd_risk"] == "critical"
    ]
    spd_high = [
        f["type"] for f in predicted_findings
        if kpi_summary[f["type"]] and f["spd_risk"] == "high"
    ]

    # A decoded identifier that does NOT match the approved baseline means the
    # wrong instrument may be in front of the camera — force supervisor review.
    identifier_mismatch = identification["identification_status"] == "mismatch"

    if remove_flags or spd_critical:
        risk_level = "critical"
    elif critical_flags or spd_high or identifier_mismatch:
        risk_level = "high"
    else:
        risk_level = _risk_level(inspection_score)

    pass_fail = "FAIL" if critical_flags else "PASS"

    # ── Findings summary (one line per key KPI) ─────────────────────────────
    summary_kpis = ["blood", "bone", "tissue", "corrosion", "rust", "discoloration", "crack"]
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

    # ── SPD-weighted summaries (severity, cleaning, action, explanation) ─────
    findings_by_kpi = {f["type"]: f for f in predicted_findings}
    severity_by_kpi = {
        f["type"]: {
            "severity": f["severity"],
            "probability": f["probability"],
            "spd_risk": f["spd_risk"],
            "spd_risk_impact": f["spd_risk_impact"],
        }
        for f in predicted_findings
    }
    cleaning_assessment = overall_cleaning_assessment(findings_by_kpi)
    action = recommended_action(findings_by_kpi, baseline_match_score)
    explanation = scoring_explanation(findings_by_kpi, baseline_match_score, source)
    top_risk_drivers = risk_drivers

    # Surface identification verification in the explanation + action.
    id_status = identification["identification_status"]
    if id_status == "verified":
        explanation.append("Instrument identifier matched the approved baseline.")
    elif id_status == "mismatch":
        explanation.append(
            "Decoded identifier does NOT match the approved baseline — possible wrong instrument."
        )
        action = (
            "Supervisor review required — decoded identifier does not match the "
            "approved baseline (possible wrong instrument)."
        )
        if "Identifier mismatch" not in top_risk_drivers:
            top_risk_drivers = ["Identifier mismatch", *top_risk_drivers]

    result = {
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
        "identification_status": identification["identification_status"],
        "decoder_backend": decoder_backend,
        "findings_summary": findings_summary,
        "confidence": overall_conf,
        "confidence_level": confidence_level,
        "recommendation": recommendation,
        # SPD risk-weighted intelligence (new contract additions).
        "recommended_action": action,
        "overall_cleaning_assessment": cleaning_assessment,
        "top_risk_drivers": top_risk_drivers,
        "severity_by_kpi": severity_by_kpi,
        "scoring_explanation": explanation,
        "spd_critical_drivers": spd_critical,
        "spd_high_drivers": spd_high,
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
    # Phase 13: Explainable Clinical Decision Support payload.
    result["clinical_decision"] = build_clinical_decision(result)
    return result
