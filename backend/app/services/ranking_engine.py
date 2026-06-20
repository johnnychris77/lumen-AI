"""Inspection Ranking Engine — deterministic, explainable, 0-100 score."""
from __future__ import annotations

from typing import Any

from app.core.baseline_ranking_contract import resolve_baseline_ranking_contract
from app.schemas.ranking import AuditEvidence, FindingDetail, RankingRequest, RankingResult

# ── Category weights (deduction from 100) ─────────────────────────────────────
CATEGORY_DEDUCTIONS: dict[str, int] = {
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

# Severity multipliers on top of category deduction
SEVERITY_MULTIPLIERS: dict[str, float] = {
    "critical": 1.5,
    "high": 1.2,
    "medium": 1.0,
    "low": 0.6,
}

# Baseline alignment bonus
BASELINE_BONUS_BY_STATUS: dict[str, int] = {
    "approved_baseline_found": 10,
    "pending_baseline_review": 3,
    "no_approved_baseline": 0,
    "baseline_not_available": 0,
}

# Identifier match bonus (cumulative, capped at 5)
IDENTIFIER_MATCH_BONUS_EACH = 2

# Risk tiers mapped from final score
RISK_TIER_MAP: list[tuple[int, str]] = [
    (80, "Low"),
    (60, "Medium"),
    (40, "High"),
    (0, "Critical"),
]


def _normalize_category(raw: str) -> str:
    return raw.strip().lower()


def _category_deduction(category: str) -> int:
    norm = _normalize_category(category)
    for key, val in CATEGORY_DEDUCTIONS.items():
        if norm == key or norm.startswith(key.split("/")[0].strip()):
            return val
    return CATEGORY_DEDUCTIONS["other"]


def _severity_multiplier(severity: str) -> float:
    return SEVERITY_MULTIPLIERS.get(severity.strip().lower(), 1.0)


def _confidence_penalty(confidence_score: float) -> int:
    """Low confidence adds up to 15 extra points of deduction."""
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


def _recommended_action(risk_level: str, category: str) -> str:
    cat_low = category.lower()
    if risk_level == "Critical":
        if "blood" in cat_low or "bone" in cat_low or "tissue" in cat_low:
            return "Immediate quarantine, notify infection control, initiate CAPA"
        if "insulation" in cat_low or "crack" in cat_low:
            return "Remove from service immediately, return to manufacturer"
        return "Immediate quarantine, escalate to SPD supervisor and quality team"
    if risk_level == "High":
        return "Quarantine, reclean with enhanced protocol, second inspection required"
    if risk_level == "Medium":
        return "Flag for additional inspection, document findings, monitor trend"
    return "Document and monitor; re-inspect at next scheduled maintenance"


def _baseline_match_pct(contract: dict[str, Any], confidence_score: float) -> float:
    mode = contract.get("ranking_mode", "")
    if "confirmed" in mode.lower():
        return round(min(confidence_score * 100, 100.0), 1)
    if "provisional" in mode.lower():
        return round(min(confidence_score * 60, 60.0), 1)
    return 0.0


def score_inspection(req: RankingRequest) -> RankingResult:
    """Compute 0-100 inspection score from finding inputs."""
    base = 100

    cat_deduction = _category_deduction(req.finding_category)
    severity_mult = _severity_multiplier(req.severity)
    weighted_deduction = int(cat_deduction * severity_mult)

    conf_penalty = _confidence_penalty(req.confidence_score)

    id_bonus, id_matched = _identifier_bonus(
        req.barcode_value, req.qr_code_value, req.key_dot_value
    )

    bl_bonus = _baseline_bonus(req.baseline_status)

    raw_score = base - weighted_deduction - conf_penalty + id_bonus + bl_bonus
    final_score = max(0, min(100, raw_score))

    risk = _risk_level(final_score)
    recommended = _recommended_action(risk, req.finding_category)

    # Baseline contract
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

    # Build audit evidence using contract helper + local details
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
    )
