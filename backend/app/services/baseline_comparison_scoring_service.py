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
import logging
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.ai.inference import SUPPORTED_MODEL_CATEGORIES
from app.services.instrument_anatomy import resolve_family
from app.services.instrument_zones import is_high_retention, zone_fields
from app.services.zone_intelligence import typical_findings_for_legacy_zone

logger = logging.getLogger(__name__)

# Version identifier for THIS deterministic-placeholder scoring pipeline —
# distinct from app.ai.inference.LumenAIModel's own model_version, since the
# two are separate placeholder implementations, not the same model.
MODEL_VERSION = "baseline-comparison-placeholder-1.0"

# This entire module is the deterministic placeholder described in the module
# docstring above — every call to analyze_inspection() produces its findings
# from a SHA-256-seeded pseudo-random value, not a trained computer-vision
# model. This constant makes that fact machine-readable (see also
# app.ai.inference.PRODUCTION_INFERENCE_MODE and
# app.ai.inference_status.get_inference_status() for the CV-model pipeline).
PRODUCTION_INFERENCE_MODE = "deterministic_placeholder"

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

# Section 6 (false-PASS remediation) — the contamination safety invariant.
# This deterministic placeholder has no real vision: an UNDECLARED cleaning
# KPI's "probability" is a SHA-256-of-the-image-hash-seeded number, capped at
# 12%, with no relationship to what the image actually shows (see
# _pseudo()/the per-KPI loop in analyze_inspection()). Presenting that as a
# verified "Clean" finding is exactly the false-PASS defect: a technician
# never has to declare visible blood/tissue/organic residue/bone/debris for
# the system to silently call it clean. Declared findings are real,
# human-sourced evidence and are unaffected by this — only the UNDECLARED
# portion of the 5 CLEANING_KPIS is marked unevaluated below, so the
# disposition can honestly say "AI analysis unavailable" instead of
# fabricating either a clean or a contaminated verdict.
CLEANING_ASSESSMENT_UNAVAILABLE = "AI analysis unavailable — manual visual inspection required"
OVERALL_RESULT_AI_UNAVAILABLE = "AI ANALYSIS UNAVAILABLE — MANUAL INSPECTION REQUIRED"

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


# All KPI categories this scoring service knows about, regardless of whether
# the currently-deployed model actually supports them (see SUPPORTED_MODEL_CATEGORIES).
_ALL_KPIS = CONTAMINATION_KPIS + CONDITION_KPIS
_UNSUPPORTED_KPIS = [k for k in _ALL_KPIS if k not in SUPPORTED_MODEL_CATEGORIES]


def _build_model_result(
    predicted_findings: list[dict[str, Any]],
    *,
    baseline_found: bool,
    analysis_status: str,
) -> dict[str, Any]:
    """Honest, scope-limited result contract (Product Truth Reset — Core
    Inspection Workflow Closure). Additive to the broader KPI heuristic above:
    it does not replace predicted_findings/kpi_summary (still used by
    reports, dashboards, and their own existing tests), it narrows what is
    PRESENTED as a model finding to only the categories the deployed model
    (app.ai.inference.LumenAIModel) actually supports today, and it never
    reports a probability for a category the model does not evaluate.
    """
    limitations = [
        "Current model evaluates debris and corrosion only, via a deterministic "
        "placeholder pipeline — no other category is scored by a trained "
        "computer-vision model on this deployment.",
        "Image quality is not automatically assessed by the current model.",
        "Result requires human review.",
    ]
    if not baseline_found:
        limitations.insert(
            0, "No approved baseline found; scoring is withheld pending supervisor review.",
        )
        return {
            "model_status": "experimental",
            "model_version": MODEL_VERSION,
            "supported_categories": list(SUPPORTED_MODEL_CATEGORIES),
            "findings": [],
            "unsupported_categories": list(_UNSUPPORTED_KPIS),
            "limitations": limitations,
            "baseline_status": "no_approved_baseline",
            "image_quality_status": "not_assessed",
            "human_review_required": True,
        }

    if analysis_status != "completed":
        limitations.insert(0, "AI analysis did not complete successfully for this submission.")
        return {
            "model_status": "experimental",
            "model_version": MODEL_VERSION,
            "supported_categories": list(SUPPORTED_MODEL_CATEGORIES),
            "findings": [],
            "unsupported_categories": list(_UNSUPPORTED_KPIS),
            "limitations": limitations,
            "baseline_status": analysis_status,
            "image_quality_status": "not_assessed",
            "human_review_required": True,
        }

    findings = [
        {
            "category": f["type"],
            "confidence": f["confidence"],
            "status": "model_observation",
        }
        for f in predicted_findings
        if f["type"] in SUPPORTED_MODEL_CATEGORIES
    ]
    return {
        "model_status": "experimental",
        "model_version": MODEL_VERSION,
        "supported_categories": list(SUPPORTED_MODEL_CATEGORIES),
        "findings": findings,
        "unsupported_categories": list(_UNSUPPORTED_KPIS),
        "limitations": limitations,
        "baseline_status": "approved_baseline_found",
        "image_quality_status": "not_assessed",
        "human_review_required": True,
    }


def _live_model_result(
    db: Session, *, tenant_id: str, image_bytes: Optional[bytes], instrument_type: str,
) -> dict[str, Any]:
    """Project Lens (Section 15) — additive integration only. Populates a
    NEW top-level key (``live_model_result``) with whatever the real live
    inference adapter reports (a genuine trained-model prediction, or a
    safe, honestly-labeled unavailable state per Section 16) — it never
    modifies ``predicted_findings``/``kpi_summary``/``model_result`` above,
    which the Decision Engine, reports, and dashboards still read
    unchanged. By default, with no promoted model artifact registered
    (this repository's state today — see FIRST_MODEL_SCOPE.md), this
    always returns the honest ``not_promoted`` unavailable contract; it
    never falls back to this module's own deterministic-placeholder
    scoring above to manufacture a result.
    """
    from app.services.ml.live_inference_adapter import predict as live_predict

    return live_predict(db, tenant_id=tenant_id, image_bytes=image_bytes, instrument_family=instrument_type)


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


def _finding_phrase_for(kpi: str, prob: dict, findings_by_kpi: dict) -> str:
    """Same phrasing as _finding_phrase(), except an undeclared cleaning KPI
    (no technician declaration, no eligible model) never claims "No X
    detected" — that would be the same false-assurance defect as the main
    disposition, just leaking through a summary/reason bullet instead."""
    f = findings_by_kpi.get(kpi)
    if f is not None and kpi in CLEANING_KPIS and not f.get("evaluated", True):
        return f"{KPI_LABELS[kpi].capitalize()} not evaluated by AI (not declared)"
    return _finding_phrase(KPI_LABELS[kpi], _severity_index(prob.get(kpi, 0.0)))

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


def _finding_action(kpi: str, spd_tier: str) -> str:
    """Per-finding recommended action from its SPD tier.

    Structural criticals → Remove from service; contamination criticals →
    Reprocess; high → Supervisor review; low → Monitor; none → Clear.
    """
    if spd_tier == "critical":
        return "Remove from service" if kpi in _STRUCTURAL_KPIS_ACTION else "Reprocess"
    if spd_tier == "high":
        return "Supervisor review"
    if spd_tier == "low":
        return "Monitor"
    return "Clear"


# Structural KPIs whose critical breach means the item leaves service.
_STRUCTURAL_KPIS_ACTION = {"crack", "missing_component", "insulation_damage"}


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


def _cleaning_actionable(f: dict) -> bool:
    """True when a cleaning-KPI finding is severe enough to be treated as
    actionable contamination: moderate+ anywhere, or trace+ in a
    high-retention zone (serrations, box locks, lumens, hinges, ...).

    This is the SINGLE predicate shared by overall_cleaning_assessment() and
    _overall_result() — previously each used its own, slightly different
    threshold (severity_index>=1 vs severity_index>=2-or-zone-escalation),
    which produced the reported contradiction: "No Critical Findings" +
    "Residual contamination suspected" + "REPROCESS" appearing together for
    the same finding. Deriving both from one function makes that
    inconsistency structurally impossible.
    """
    idx = f["severity_index"]
    return idx >= 2 or (idx >= 1 and is_high_retention(f.get("instrument_zone", "")))


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
    unevaluated = False
    for kpi in CLEANING_KPIS:
        f = findings_by_kpi.get(kpi)
        if not f:
            continue
        if not f.get("evaluated", True):
            # No technician declaration and no real model backs this KPI —
            # the placeholder's number must not be read as a verified
            # "clean" result (see CLEANING_ASSESSMENT_UNAVAILABLE).
            unevaluated = True
            continue
        if not _cleaning_actionable(f):
            continue
        residual = True
        idx = f["severity_index"]
        if kpi in ("blood", "tissue", "other_organic_residue") and idx >= 2:
            failure = True
        if kpi == "debris" and idx >= 3:
            failure = True
    if failure:
        return "Cleaning failure"
    if residual:
        return "Residual contamination suspected"
    if unevaluated:
        return CLEANING_ASSESSMENT_UNAVAILABLE
    return "Clean"


def recommended_action(findings_by_kpi: dict[str, dict], baseline_match_score: float) -> str:
    """Map findings onto an SPD recommended action.

    Priority: reprocess/remove > supervisor review > monitor > pass.
    """
    def present(kpi: str) -> dict | None:
        f = findings_by_kpi.get(kpi)
        return f if f and f["severity_index"] >= 1 else None

    def contamination_actionable(kpi: str) -> dict | None:
        """Moderate+ anywhere, OR trace+ in a high-retention zone (zone-aware).

        Only a declared/evaluated finding can drive this — an unevaluated
        placeholder number must not be read as real evidence of
        contamination any more than it may be read as evidence of
        cleanliness (see CLEANING_ASSESSMENT_UNAVAILABLE).
        """
        f = findings_by_kpi.get(kpi)
        if not f or not f.get("evaluated", True):
            return None
        if _cleaning_actionable(f):
            return f
        return None

    # REMOVE FROM SERVICE — structural defects (moderate+), severe corrosion.
    remove = []
    for kpi in ("crack", "missing_component", "insulation_damage"):
        f = findings_by_kpi.get(kpi)
        if f and f["severity_index"] >= 2:
            remove.append(KPI_LABELS[kpi])
    corr = findings_by_kpi.get("corrosion")
    if corr and corr["severity_index"] >= 3:
        remove.append("severe corrosion")
    if remove:
        return (
            "Remove from service — " + ", ".join(sorted(set(remove)))
            + ". Supervisor review required before any further use."
        )

    # REPROCESS — residual contamination (zone-aware).
    reprocess = [
        KPI_LABELS[kpi]
        for kpi in ("blood", "tissue", "other_organic_residue", "debris", "bone")
        if contamination_actionable(kpi)
    ]
    if reprocess:
        drivers = ", ".join(sorted(set(reprocess)))
        return (
            f"Reprocess — {drivers}. Return the instrument for complete cleaning "
            "and re-inspect before release."
        )

    # SUPERVISOR REVIEW
    supervisor = []
    for kpi in ("debris", "bone"):
        # debris/bone are cleaning KPIs — an undeclared (unevaluated)
        # placeholder number must not leak into this recommendation text
        # either, for the same reason it must not assert "Clean" above.
        f = present(kpi)
        if f and f.get("evaluated", True):
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

    # AI ANALYSIS UNAVAILABLE — no technician declaration and no eligible
    # trained model backs any of the 5 cleaning KPIs; the absence of a
    # placeholder-generated finding is not evidence of cleanliness.
    if any(
        not (findings_by_kpi.get(kpi) or {}).get("evaluated", True)
        for kpi in CLEANING_KPIS
    ):
        return (
            "AI analysis unavailable for non-declared contamination findings — "
            "manual visual inspection required before release."
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
            if f.get("evaluated", True):
                lines.append(f"No {name} detected.")
            else:
                # Undeclared cleaning KPI, no eligible model — do not claim
                # a verified negative for something that was never evaluated.
                lines.append(f"AI analysis unavailable for {name} — not declared by technician.")
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
    """Collapse the analysis into one of the six clinical dispositions
    (PASS / MONITOR / SUPERVISOR REVIEW / REPROCESS / REMOVE FROM SERVICE /
    AI ANALYSIS UNAVAILABLE — MANUAL INSPECTION REQUIRED)."""
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

    # Residual contamination → return for cleaning/reprocessing. Read
    # straight from result["overall_cleaning_assessment"] (computed once, in
    # analyze_inspection(), by overall_cleaning_assessment()) rather than
    # re-deriving a second, slightly different threshold here — that
    # divergence (idx>=2 here vs idx>=1 there) is exactly what previously
    # produced the reported contradiction ("No Critical Findings" shown
    # alongside "REPROCESS — residual contamination suspected"). A single
    # source of truth makes that combination structurally impossible.
    # Direct callers (and tests) that hand-build a result dict from raw
    # predicted_findings, rather than going through analyze_inspection(),
    # won't have this key set yet — derive it the same way in that case so
    # the single-source-of-truth guarantee holds regardless of caller.
    if "overall_cleaning_assessment" in result:
        cleaning = result["overall_cleaning_assessment"]
    else:
        cleaning = overall_cleaning_assessment(f)
    if cleaning in ("Cleaning failure", "Residual contamination suspected"):
        return "REPROCESS"
    if cleaning == CLEANING_ASSESSMENT_UNAVAILABLE:
        # No technician declaration and no eligible trained model back any of
        # the 5 cleaning KPIs — the absence of a placeholder-generated
        # finding is not evidence of cleanliness (Section 8). Structural/
        # identification findings above still take priority; this is the
        # honest floor for everything else.
        return OVERALL_RESULT_AI_UNAVAILABLE
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
    OVERALL_RESULT_AI_UNAVAILABLE: (
        "Perform full manual visual inspection — AI contamination screening is "
        "not available for this result."
    ),
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
    OVERALL_RESULT_AI_UNAVAILABLE: (
        "No technician-declared finding and no eligible trained model are available "
        "to evaluate contamination for this instrument. This is not a clean result — "
        "it means AI could not evaluate it. A full manual visual inspection is "
        "required before release."
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


def build_clinical_decision(result: dict, training_mode: bool = False) -> dict:
    """Assemble the full Explainable-AI Clinical Decision Support payload
    (Phases 13.1–13.11) from an already-computed analysis result."""
    from app.services.clinical_mentor import build_mentor  # lazy: avoid cycle
    from app.services.spd_mentor_engine import build_spd_mentor  # lazy: avoid cycle

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
        # Phase 14 — Clinical Mentor: interpretation, why-this-matters, expanded
        # actions, standards guidance, learning mode, risk separation, mentor.
        **build_mentor(result, overall),
        # v1.4 — SPD Mentor Engine: corrective action chains, anatomy coaching,
        # confidence coaching, clinical decision summary, education cards.
        "spd_mentor": build_spd_mentor(result, overall, training_mode=training_mode),
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
    inspected_zones: Optional[list[str]] = None,
    training_mode: bool = False,
    image_view_tags: Optional[list[dict]] = None,
    image_bytes: Optional[bytes] = None,
) -> dict[str, Any]:
    """Run the deterministic baseline-comparison analysis.

    Returns the explainable analysis payload. When no approved baseline is
    found, returns analysis_status="supervisor_review_required" with NO final
    score, per governance rules.
    """
    logger.info("INFERENCE MODE: deterministic placeholder active — not a trained CV model")
    declared = {
        _DECLARED_TO_KPI[c]
        for c in (declared_findings or [])
        if c in _DECLARED_TO_KPI
    }

    resolution = resolve_baseline(db, instrument_type, tenant_id)

    # ── Governance gate: no approved baseline → no final score ──────────────
    if not resolution["baseline_found"]:
        from app.services.instrument_anatomy import get_anatomy

        no_baseline = {
            "analysis_status": "supervisor_review_required",
            "instrument_type": instrument_type,
            "instrument_anatomy": get_anatomy(instrument_type),
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
        no_baseline["model_result"] = _build_model_result(
            [], baseline_found=False, analysis_status="supervisor_review_required",
        )
        no_baseline["live_model_result"] = _live_model_result(
            db, tenant_id=tenant_id, image_bytes=image_bytes, instrument_type=instrument_type,
        )
        no_baseline["clinical_decision"] = build_clinical_decision(no_baseline, training_mode=training_mode)
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
        # A CLEANING_KPI the technician did not declare has no real evidence
        # behind it — the placeholder's low pseudo-random number must not be
        # read as a verified "clean" result (see CLEANING_ASSESSMENT_UNAVAILABLE
        # above). Declared findings, and every non-cleaning (condition) KPI,
        # keep the pre-existing placeholder-scored behavior unchanged.
        evaluated = (kpi in declared) or (kpi not in CLEANING_KPIS)
        finding = {
            "type": kpi,
            "label": KPI_LABELS.get(kpi, kpi),
            "probability": probability,
            "confidence": confidence,
            "evaluated": evaluated,
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
        }
        # Instrument-zone taxonomy: where this finding is likely to hide, its
        # retention risk, and the recommended manual check for that zone.
        finding.update(zone_fields(instrument_type, kpi))
        # v2.0 — Zone-Based AI Context: which anatomy family this instrument
        # resolved to, and the zone-specific (not generic) findings expected
        # at this zone — the reasoning engine reasons differently for a
        # Kerrison serration than a rigid-scope o-ring from this point on.
        finding["instrument_family"] = resolve_family(instrument_type)
        finding["expected_findings_for_zone"] = typical_findings_for_legacy_zone(finding["instrument_zone"])
        # Per-finding recommended action (Reprocess / Remove / Supervisor review /
        # Monitor / Clear) from its SPD tier + structural vs contamination.
        finding["recommended_action"] = _finding_action(kpi, spd_tier)
        predicted_findings.append(finding)

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
    findings_by_kpi = {f["type"]: f for f in predicted_findings}
    # Single source of truth for the cleaning/contamination verdict — computed
    # once here so pass_fail, findings_summary, and (later) _overall_result()
    # can never disagree about it (Section 7 — result consistency).
    cleaning_assessment = overall_cleaning_assessment(findings_by_kpi)

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

    if critical_flags or cleaning_assessment in ("Cleaning failure", "Residual contamination suspected"):
        pass_fail = "FAIL"
    elif cleaning_assessment == CLEANING_ASSESSMENT_UNAVAILABLE:
        pass_fail = "AI_ANALYSIS_UNAVAILABLE"
    else:
        pass_fail = "PASS"

    # ── Findings summary (one line per key KPI) ─────────────────────────────
    summary_kpis = ["blood", "bone", "tissue", "corrosion", "rust", "discoloration", "crack"]
    findings_summary: list[str] = []
    if cleaning_assessment == CLEANING_ASSESSMENT_UNAVAILABLE:
        findings_summary.append(
            "AI analysis unavailable for non-declared contamination findings — "
            "manual visual inspection required"
        )
    elif not critical_flags and cleaning_assessment not in ("Cleaning failure", "Residual contamination suspected"):
        findings_summary.append("No critical contamination detected")
    for kpi in summary_kpis:
        findings_summary.append(_finding_phrase_for(kpi, prob, findings_by_kpi))

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
        reason.append(_finding_phrase_for(kpi, prob, findings_by_kpi) + ".")
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
    severity_by_kpi = {
        f["type"]: {
            "severity": f["severity"],
            "probability": f["probability"],
            "spd_risk": f["spd_risk"],
            "spd_risk_impact": f["spd_risk_impact"],
        }
        for f in predicted_findings
    }
    # Phase 15 — anatomy-aware coverage, missing-image guidance, risk map.
    from app.services.instrument_anatomy import get_anatomy
    from app.services.inspection_coverage import (
        build_risk_map, compute_coverage, missing_image_guidance,
    )
    anatomy = get_anatomy(instrument_type)
    coverage = compute_coverage(instrument_type, inspected_zones)
    guidance = missing_image_guidance(instrument_type, inspected_zones)
    # Map detected findings onto their assigned zone for the risk map.
    findings_by_zone: dict[str, list[str]] = {}
    for f in predicted_findings:
        if f["severity_index"] >= 2:
            findings_by_zone.setdefault(f["instrument_zone"], []).append(f["label"])
    risk_map = build_risk_map(instrument_type, findings_by_zone, inspected_zones)

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
        "instrument_type": instrument_type,
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
        # Phase 15 — anatomy-aware intelligence.
        "instrument_anatomy": anatomy,
        "inspection_coverage": coverage,
        "missing_image_guidance": guidance,
        "risk_map": risk_map,
        # v1.2 — per-image view tags (family/zone/view/quality/notes), passed
        # straight through so the AI context reflects exactly what was tagged.
        "image_view_tags": image_view_tags or [],
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
    result["model_result"] = _build_model_result(
        predicted_findings, baseline_found=True, analysis_status="completed",
    )
    result["live_model_result"] = _live_model_result(
        db, tenant_id=tenant_id, image_bytes=image_bytes, instrument_type=instrument_type,
    )
    # Phase 13: Explainable Clinical Decision Support payload.
    result["clinical_decision"] = build_clinical_decision(result, training_mode=training_mode)
    return result
