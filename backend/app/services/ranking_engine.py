"""Inspection Ranking Engine — deterministic, explainable, 0-100 score."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any

from app.core.baseline_ranking_contract import resolve_baseline_ranking_contract
from app.schemas.ranking import (
    AuditEvidence,
    CompositeRankingRequest,
    CompositeRankingResult,
    FindingDetail,
    RankingRequest,
    RankingResult,
)

# ── Default category weights (deduction from 100) ─────────────────────────────
DEFAULT_CATEGORY_DEDUCTIONS: dict[str, int] = {
    "blood / retained blood residue": 30,
    "bone / bone fragment": 28,
    "tissue / retained tissue": 26,
    "insulation damage": 25,
    "crack / hairline fracture": 22,
    "corrosion / surface rust": 18,
    "pitting": 15,
    "missing component": 20,
    "debris / retained debris": 12,
    "bioburden / retained debris": 14,
    "lumen blockage": 16,
    "seal integrity failure": 18,
    "mechanical damage": 16,
    "discoloration": 8,
    "baseline mismatch": 20,
    "other": 10,
}

# Keep public alias for tests that import the constant directly
CATEGORY_DEDUCTIONS = DEFAULT_CATEGORY_DEDUCTIONS

DEFAULT_SEVERITY_MULTIPLIERS: dict[str, float] = {
    "critical": 1.5,
    "high": 1.2,
    "medium": 1.0,
    "low": 0.6,
}

BASELINE_BONUS_BY_STATUS: dict[str, int] = {
    "approved_baseline_found": 10,
    "pending_baseline_review": 3,
    "no_approved_baseline": 0,
    "baseline_not_available": 0,
}

IDENTIFIER_MATCH_BONUS_EACH = 2

RISK_TIER_MAP: list[tuple[int, str]] = [
    (80, "Low"),
    (60, "Medium"),
    (40, "High"),
    (0, "Critical"),
]


def _resolve_weights(profile: dict[str, Any] | None) -> dict[str, int]:
    if profile and profile.get("category_weights"):
        merged = dict(DEFAULT_CATEGORY_DEDUCTIONS)
        merged.update(profile["category_weights"])
        return merged
    return DEFAULT_CATEGORY_DEDUCTIONS


def _resolve_multipliers(profile: dict[str, Any] | None) -> dict[str, float]:
    if profile and profile.get("severity_multipliers"):
        merged = dict(DEFAULT_SEVERITY_MULTIPLIERS)
        merged.update(profile["severity_multipliers"])
        return merged
    return DEFAULT_SEVERITY_MULTIPLIERS


def _normalize_category(raw: str) -> str:
    return raw.strip().lower()


def _category_deduction(category: str, weights: dict[str, int]) -> int:
    norm = _normalize_category(category)
    for key, val in weights.items():
        if norm == key or norm.startswith(key.split("/")[0].strip()):
            return val
    return weights.get("other", DEFAULT_CATEGORY_DEDUCTIONS["other"])


def _severity_multiplier(severity: str, multipliers: dict[str, float]) -> float:
    return multipliers.get(severity.strip().lower(), 1.0)


def _confidence_penalty(confidence_score: float) -> int:
    if confidence_score >= 0.85:
        return 0
    if confidence_score >= 0.70:
        return 5
    if confidence_score >= 0.50:
        return 10
    return 15


def _identifier_bonus(barcode: str, qr: str, key_dot: str) -> tuple[int, dict[str, str]]:
    matched: dict[str, str] = {}
    if barcode.strip():
        matched["barcode"] = "matched"
    if qr.strip():
        matched["qr_code"] = "matched"
    if key_dot.strip():
        matched["key_dot"] = "matched"
    bonus = min(len(matched) * IDENTIFIER_MATCH_BONUS_EACH, 5)
    return bonus, matched


def _baseline_bonus(baseline_status: str) -> int:
    norm = baseline_status.strip().lower().replace(" ", "_")
    return BASELINE_BONUS_BY_STATUS.get(norm, 0)


def _risk_level(score: int) -> str:
    for threshold, label in RISK_TIER_MAP:
        if score >= threshold:
            return label
    return "Critical"


def _recommended_action(risk_level: str, category: str, compound: bool = False) -> str:
    cat_low = category.lower()
    prefix = "COMPOUND RISK — " if compound else ""
    if risk_level == "Critical":
        if "blood" in cat_low or "bone" in cat_low or "tissue" in cat_low:
            return f"{prefix}Immediate quarantine, notify infection control, initiate CAPA"
        if "insulation" in cat_low or "crack" in cat_low:
            return f"{prefix}Remove from service immediately, return to manufacturer"
        return f"{prefix}Immediate quarantine, escalate to SPD supervisor and quality team"
    if risk_level == "High":
        return f"{prefix}Quarantine, reclean with enhanced protocol, second inspection required"
    if risk_level == "Medium":
        return f"{prefix}Flag for additional inspection, document findings, monitor trend"
    return f"{prefix}Document and monitor; re-inspect at next scheduled maintenance"


def _baseline_match_pct(contract: dict[str, Any], confidence_score: float) -> float:
    mode = contract.get("ranking_mode", "")
    if "confirmed" in mode.lower():
        return round(min(confidence_score * 100, 100.0), 1)
    if "provisional" in mode.lower():
        return round(min(confidence_score * 60, 60.0), 1)
    return 0.0


def _check_instrument_history(
    instrument_id: int | None,
    db: Any,
    window_days: int = 90,
) -> int:
    """Return count of high/critical findings on this instrument in the window."""
    if instrument_id is None or db is None:
        return 0
    try:
        from app.models.enterprise_quality import EnterpriseFinding
        cutoff = datetime.now(timezone.utc) - timedelta(days=window_days)
        count = (
            db.query(EnterpriseFinding)
            .filter(
                EnterpriseFinding.instrument_id == instrument_id,
                EnterpriseFinding.severity.in_(["high", "critical"]),
                EnterpriseFinding.created_at >= cutoff,
            )
            .count()
        )
        return count
    except Exception:
        return 0


def _load_profile(tenant_id: str, db: Any) -> dict[str, Any] | None:
    """Load the active scoring profile for a tenant from DB."""
    if db is None:
        return None
    try:
        from app.models.enterprise_quality import EnterpriseScoringProfile
        row = (
            db.query(EnterpriseScoringProfile)
            .filter(
                EnterpriseScoringProfile.tenant_id == tenant_id,
                EnterpriseScoringProfile.is_active.is_(True),
            )
            .order_by(EnterpriseScoringProfile.id.desc())
            .first()
        )
        if not row:
            return None
        profile: dict[str, Any] = {
            "compound_escalation_threshold": row.compound_escalation_threshold,
            "compound_escalation_window_days": row.compound_escalation_window_days,
        }
        if row.category_weights_json:
            profile["category_weights"] = json.loads(row.category_weights_json)
        if row.severity_multipliers_json:
            profile["severity_multipliers"] = json.loads(row.severity_multipliers_json)
        return profile
    except Exception:
        return None


def score_inspection(
    req: RankingRequest,
    db: Any = None,
    profile: dict[str, Any] | None = None,
) -> RankingResult:
    """Compute 0-100 inspection score from finding inputs."""
    if profile is None and db is not None:
        profile = _load_profile(req.tenant_id, db)

    weights = _resolve_weights(profile)
    multipliers = _resolve_multipliers(profile)

    base = 100
    cat_deduction = _category_deduction(req.finding_category, weights)
    severity_mult = _severity_multiplier(req.severity, multipliers)
    weighted_deduction = int(cat_deduction * severity_mult)
    conf_penalty = _confidence_penalty(req.confidence_score)
    id_bonus, id_matched = _identifier_bonus(req.barcode_value, req.qr_code_value, req.key_dot_value)
    bl_bonus = _baseline_bonus(req.baseline_status)

    raw_score = base - weighted_deduction - conf_penalty + id_bonus + bl_bonus
    final_score = max(0, min(100, raw_score))

    # Instrument history elevation — prior high/critical findings in window
    history_elevation = False
    if req.instrument_id and db:
        window = profile.get("compound_escalation_window_days", 90) if profile else 90
        prior_count = _check_instrument_history(req.instrument_id, db, window_days=window)
        if prior_count >= 2:
            final_score = max(0, final_score - 15)
            history_elevation = True

    risk = _risk_level(final_score)
    recommended = _recommended_action(risk, req.finding_category)

    contract = resolve_baseline_ranking_contract(
        instrument_match_status=req.instrument_match_status or "unknown",
        baseline_status=req.baseline_status or "baseline_not_available",
        baseline_confidence=str(req.confidence_score),
    )
    bl_match_pct = _baseline_match_pct(contract, req.confidence_score)

    findings = [
        FindingDetail(
            category=req.finding_category,
            severity=req.severity,
            score_deduction=weighted_deduction,
            rationale=f"Category weight {cat_deduction} × severity multiplier {severity_mult:.1f}",
        )
    ]

    audit = AuditEvidence(
        ranking_mode=contract["ranking_mode"],
        baseline_review_required=contract["baseline_review_required"],
        final_ranking_allowed=contract["final_ranking_allowed"],
        baseline_review_reason=contract["review_reason"],
        identifier_match=id_matched,
        scoring_breakdown={
            "base_score": base,
            "category_deduction": weighted_deduction,
            "confidence_penalty": conf_penalty,
            "identifier_bonus": id_bonus,
            "baseline_bonus": bl_bonus,
            "history_elevation": -15 if history_elevation else 0,
            "final_score": final_score,
        },
    )

    return RankingResult(
        finding_id=req.finding_id,
        inspection_score=final_score,
        risk_level=risk,
        baseline_match_pct=bl_match_pct,
        findings=findings,
        recommended_action=recommended,
        audit_evidence=audit,
        ranking_mode=contract["ranking_mode"],
        final_ranking_allowed=contract["final_ranking_allowed"],
        compound_escalation_applied=False,
        history_elevation_applied=history_elevation,
    )


def score_composite(req: CompositeRankingRequest, db: Any = None) -> CompositeRankingResult:
    """Score multiple findings on the same instrument; apply compound escalation."""
    profile = _load_profile(req.tenant_id, db) if db else None
    threshold = profile.get("compound_escalation_threshold", 2) if profile else 2

    individual: list[RankingResult] = []
    for f in req.findings:
        r = RankingRequest(
            finding_category=f.finding_category,
            severity=f.severity,
            confidence_score=f.confidence_score,
            instrument_id=req.instrument_id,
            barcode_value=f.barcode_value,
            qr_code_value=f.qr_code_value,
            key_dot_value=f.key_dot_value,
            baseline_status=f.baseline_status,
            instrument_match_status=f.instrument_match_status,
            tenant_id=req.tenant_id,
        )
        individual.append(score_inspection(r, db=db, profile=profile))

    # Composite score = weighted average, floored by worst finding
    scores = [r.inspection_score for r in individual]
    avg_score = int(sum(scores) / len(scores))
    min_score = min(scores)
    composite_score = min(avg_score, min_score + 10)  # bias toward worst case

    # Compound escalation: N+ critical-severity findings → floor to Critical band max (39)
    # Use input severity label (not computed score) — clinical severity declared by the operator.
    critical_findings = [
        (f, r) for f, r in zip(req.findings, individual)
        if f.severity.lower() == "critical"
    ]
    compound_applied = len(critical_findings) >= threshold
    if compound_applied:
        composite_score = min(composite_score, 39)

    risk = _risk_level(composite_score)
    worst_category = req.findings[scores.index(min_score)].finding_category
    recommended = _recommended_action(risk, worst_category, compound=compound_applied)

    return CompositeRankingResult(
        instrument_id=req.instrument_id,
        instrument_name=req.instrument_name,
        composite_score=composite_score,
        risk_level=risk,
        compound_escalation_applied=compound_applied,
        finding_results=individual,
        recommended_action=recommended,
        total_findings=len(individual),
        critical_findings=len(critical_findings),
    )

