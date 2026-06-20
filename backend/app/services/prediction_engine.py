"""P7: Predictive instrument failure risk scoring engine.

Pattern: DB aggregation first → seeded deterministic mock fallback.
All predictions include evidence factors for explainability.
"""
from __future__ import annotations

import hashlib
import json
import random
import re as _re
from datetime import datetime, timezone

from app.schemas.predictions import (
    ContaminationRecurrencePredictionResult,
    EvidenceFactor,
    InstrumentFailurePredictionResult,
    PredictiveDashboard,
    RecallRiskAssessmentResult,
    RepairForecastResult,
    TrayRiskAssessmentResult,
)


def _sanitize(text: str) -> str:
    """Strip characters that could carry injection payloads into exports."""
    return _re.sub(r"[<>{}`$]", "", text)


def _seed(s: str) -> random.Random:
    h = hashlib.md5(s.encode()).hexdigest()[:8]
    return random.Random(int(h, 16))


def _now_str() -> str:
    return datetime.now(timezone.utc).isoformat()


def _risk_category(score: float) -> str:
    if score >= 75:
        return "critical"
    if score >= 50:
        return "high"
    if score >= 25:
        return "medium"
    return "low"


def _urgency_tier(score: float) -> str:
    if score >= 75:
        return "critical"
    if score >= 50:
        return "act"
    if score >= 25:
        return "watch"
    return "low"


# ── Failure Prediction ────────────────────────────────────────────────────────

def predict_instrument_failure(
    tenant_id: str,
    instrument_name: str,
    facility_id: str = "",
    horizon_days: int = 30,
    db=None,
) -> InstrumentFailurePredictionResult:
    """Predict failure probability for a specific instrument."""
    now = _now_str()

    if db is not None:
        try:
            from app.models.cv_inference import CVInferenceRecord
            q = db.query(CVInferenceRecord).filter(
                CVInferenceRecord.tenant_id == tenant_id,
                CVInferenceRecord.instrument_name == instrument_name,
            )
            if facility_id:
                q = q.filter(CVInferenceRecord.facility_id == facility_id)
            records = q.order_by(CVInferenceRecord.id.desc()).limit(20).all()

            if records:
                return _compute_failure_from_records(
                    records, tenant_id, instrument_name, facility_id, horizon_days, now
                )
        except Exception:
            pass

    # Mock fallback
    return _mock_failure_prediction(tenant_id, instrument_name, facility_id, horizon_days, now)


def _compute_failure_from_records(records, tenant_id, instrument_name, facility_id, horizon_days, now):
    n = len(records)
    avg_damage = sum(r.damage_score for r in records) / n
    avg_cleanliness = sum(r.overall_cleanliness_score for r in records) / n
    avg_baseline = sum((r.baseline_match_pct or 0) for r in records) / n
    total_cracks = sum(r.crack_count for r in records)
    total_corrosion = sum(r.corrosion_count for r in records)

    # Damage trend: compare first half vs second half
    mid = max(1, n // 2)
    recent_damage = sum(r.damage_score for r in records[:mid]) / mid
    older_damage = sum(r.damage_score for r in records[mid:]) / max(1, n - mid)
    damage_trend = older_damage - recent_damage  # positive = worsening (lower score = worse)

    # Score components
    damage_component = max(0, (100 - avg_damage)) * 0.35
    cleanliness_component = max(0, (100 - avg_cleanliness)) * 0.20
    baseline_component = max(0, (100 - avg_baseline)) * 0.20
    structural_component = min(100, (total_cracks * 15 + total_corrosion * 10)) * 0.25

    # Horizon multiplier
    horizon_mult = {30: 0.7, 90: 1.0, 180: 1.3}.get(horizon_days, 1.0)

    risk_score = min(100, (damage_component + cleanliness_component + baseline_component + structural_component) * horizon_mult)
    failure_prob = round(risk_score / 100, 3)
    confidence = min(1.0, 0.3 + (n * 0.1))  # caps at 1.0 after 7+ records

    evidence = [
        EvidenceFactor(factor="avg_damage_score", value=round(avg_damage, 1), weight=0.35,
                       signal="degrading" if avg_damage < 70 else "stable"),
        EvidenceFactor(factor="avg_cleanliness_score", value=round(avg_cleanliness, 1), weight=0.20,
                       signal="below_threshold" if avg_cleanliness < 75 else "stable"),
        EvidenceFactor(factor="avg_baseline_match_pct", value=round(avg_baseline, 1), weight=0.20,
                       signal="below_threshold" if avg_baseline < 80 else "stable"),
        EvidenceFactor(factor="structural_findings", value=total_cracks + total_corrosion, weight=0.25,
                       signal="elevated" if (total_cracks + total_corrosion) > 2 else "stable"),
        EvidenceFactor(factor="damage_score_trend", value=round(damage_trend, 2), weight=0.10,
                       signal="degrading" if damage_trend > 5 else "stable"),
    ]

    action = _failure_action(risk_score)
    cat = records[0].instrument_category if records else ""

    return InstrumentFailurePredictionResult(
        instrument_name=instrument_name,
        instrument_category=cat,
        tenant_id=tenant_id,
        facility_id=facility_id,
        prediction_date=now,
        horizon_days=horizon_days,
        failure_probability=failure_prob,
        risk_score=round(risk_score, 1),
        risk_category=_risk_category(risk_score),
        confidence=round(confidence, 2),
        records_used=n,
        evidence=evidence,
        recommended_action=action,
        data_source="real" if n >= 3 else "insufficient",
    )


def _mock_failure_prediction(tenant_id, instrument_name, facility_id, horizon_days, now):
    rng = _seed(f"fail:{tenant_id}:{instrument_name}:{horizon_days}")
    risk_score = round(rng.uniform(10, 90), 1)
    failure_prob = round(risk_score / 100, 3)
    confidence = round(rng.uniform(0.45, 0.85), 2)
    evidence = [
        EvidenceFactor(factor="avg_damage_score", value=round(rng.uniform(50, 95), 1), weight=0.35,
                       signal=rng.choice(["degrading", "stable"])),
        EvidenceFactor(factor="avg_cleanliness_score", value=round(rng.uniform(60, 98), 1), weight=0.20,
                       signal=rng.choice(["below_threshold", "stable"])),
        EvidenceFactor(factor="avg_baseline_match_pct", value=round(rng.uniform(55, 95), 1), weight=0.20,
                       signal=rng.choice(["below_threshold", "stable"])),
        EvidenceFactor(factor="structural_findings", value=rng.randint(0, 5), weight=0.25,
                       signal=rng.choice(["elevated", "stable"])),
    ]
    return InstrumentFailurePredictionResult(
        instrument_name=instrument_name,
        instrument_category="general_surgery",
        tenant_id=tenant_id,
        facility_id=facility_id,
        prediction_date=now,
        horizon_days=horizon_days,
        failure_probability=failure_prob,
        risk_score=risk_score,
        risk_category=_risk_category(risk_score),
        confidence=confidence,
        records_used=0,
        evidence=evidence,
        recommended_action=_failure_action(risk_score),
        data_source="mock",
    )


def _failure_action(score: float) -> str:
    if score >= 75:
        return _sanitize("Pull from service immediately. Schedule inspection and repair assessment within 24 hours.")
    if score >= 50:
        return _sanitize("Flag for priority inspection at next use. Schedule preventive maintenance within 7 days.")
    if score >= 25:
        return _sanitize("Monitor closely. Include in next scheduled maintenance cycle.")
    return _sanitize("No immediate action required. Continue routine monitoring.")


# ── Contamination Recurrence Prediction ──────────────────────────────────────

def predict_contamination_recurrence(
    tenant_id: str,
    instrument_name: str,
    facility_id: str = "",
    db=None,
) -> ContaminationRecurrencePredictionResult:
    now = _now_str()

    if db is not None:
        try:
            from app.models.cv_inference import CVInferenceRecord
            q = db.query(CVInferenceRecord).filter(
                CVInferenceRecord.tenant_id == tenant_id,
                CVInferenceRecord.instrument_name == instrument_name,
            )
            if facility_id:
                q = q.filter(CVInferenceRecord.facility_id == facility_id)
            records = q.order_by(CVInferenceRecord.id.desc()).limit(20).all()

            if records:
                n = len(records)
                total_blood = sum(r.blood_count for r in records)
                total_bone = sum(r.bone_count for r in records)
                total_tissue = sum(r.tissue_count for r in records)
                total_residue = sum(r.residue_count for r in records)
                total_contamination = total_blood + total_bone + total_tissue + total_residue

                # Contamination rate per inspection
                rate = total_contamination / n

                # Dominant contaminant
                counts = {"blood": total_blood, "bone": total_bone, "tissue": total_tissue, "residue": total_residue}
                dominant = max(counts, key=counts.get)

                risk_score = min(100, rate * 25)  # 4+ findings per inspection = 100
                confidence = min(1.0, 0.3 + n * 0.1)

                evidence = [
                    EvidenceFactor(factor="blood_finding_rate", value=round(total_blood / n, 2), weight=0.35,
                                   signal="elevated" if total_blood / n > 0.5 else "stable"),
                    EvidenceFactor(factor="bone_finding_rate", value=round(total_bone / n, 2), weight=0.25,
                                   signal="elevated" if total_bone / n > 0.3 else "stable"),
                    EvidenceFactor(factor="tissue_finding_rate", value=round(total_tissue / n, 2), weight=0.25,
                                   signal="elevated" if total_tissue / n > 0.3 else "stable"),
                    EvidenceFactor(factor="total_contamination_rate", value=round(rate, 2), weight=0.15,
                                   signal="elevated" if rate > 1.0 else "stable"),
                ]

                action = _contamination_action(risk_score, dominant)
                cat = records[0].instrument_category if records else ""

                return ContaminationRecurrencePredictionResult(
                    instrument_name=instrument_name,
                    instrument_category=cat,
                    tenant_id=tenant_id,
                    facility_id=facility_id,
                    prediction_date=now,
                    recurrence_probability=round(risk_score / 100, 3),
                    risk_score=round(risk_score, 1),
                    risk_category=_risk_category(risk_score),
                    confidence=round(confidence, 2),
                    dominant_contaminant=dominant,
                    records_used=n,
                    evidence=evidence,
                    recommended_action=action,
                    data_source="real" if n >= 3 else "insufficient",
                )
        except Exception:
            pass

    # Mock fallback
    rng = _seed(f"contam:{tenant_id}:{instrument_name}")
    risk_score = round(rng.uniform(5, 85), 1)
    dominant = rng.choice(["blood", "bone", "tissue"])
    evidence = [
        EvidenceFactor(factor="blood_finding_rate", value=round(rng.uniform(0, 1.5), 2), weight=0.35,
                       signal=rng.choice(["elevated", "stable"])),
        EvidenceFactor(factor="bone_finding_rate", value=round(rng.uniform(0, 0.8), 2), weight=0.25,
                       signal=rng.choice(["elevated", "stable"])),
        EvidenceFactor(factor="tissue_finding_rate", value=round(rng.uniform(0, 0.8), 2), weight=0.25,
                       signal=rng.choice(["elevated", "stable"])),
        EvidenceFactor(factor="total_contamination_rate", value=round(rng.uniform(0, 2), 2), weight=0.15,
                       signal=rng.choice(["elevated", "stable"])),
    ]
    return ContaminationRecurrencePredictionResult(
        instrument_name=instrument_name,
        instrument_category="general_surgery",
        tenant_id=tenant_id,
        facility_id=facility_id,
        prediction_date=now,
        recurrence_probability=round(risk_score / 100, 3),
        risk_score=risk_score,
        risk_category=_risk_category(risk_score),
        confidence=round(rng.uniform(0.4, 0.8), 2),
        dominant_contaminant=dominant,
        records_used=0,
        evidence=evidence,
        recommended_action=_contamination_action(risk_score, dominant),
        data_source="mock",
    )


def _contamination_action(score: float, dominant: str) -> str:
    contaminant_map = {"blood": "blood residue", "bone": "bone debris", "tissue": "soft tissue residue"}
    c = contaminant_map.get(dominant, dominant)
    if score >= 75:
        return _sanitize(f"Critical {c} recurrence risk. Escalate decontamination protocol review. Pull instrument for manual inspection.")
    if score >= 50:
        return _sanitize(f"High {c} recurrence detected. Extend enzymatic soak time. Re-validate IFU compliance for this instrument type.")
    if score >= 25:
        return _sanitize(f"Moderate {c} trend. Audit decontamination steps. Increase inspection frequency.")
    return _sanitize("Contamination risk within acceptable range. Continue standard protocol.")


# ── Repair Forecasting ────────────────────────────────────────────────────────

# Estimated repair/replacement costs by category (USD)
REPAIR_COSTS = {
    "laparoscopic": (800, 4500),
    "endoscopic": (1200, 8000),
    "orthopedic": (600, 3500),
    "cardiac": (1500, 12000),
    "general_surgery": (400, 2500),
    "lumened instrument": (900, 5000),
    "rigid scope": (1100, 7000),
}


def forecast_repair(
    tenant_id: str,
    instrument_name: str,
    facility_id: str = "",
    db=None,
) -> RepairForecastResult:
    now = _now_str()
    failure = predict_instrument_failure(tenant_id, instrument_name, facility_id, 90, db)

    # Derive repair/replacement probabilities from failure prediction
    repair_prob = round(failure.failure_probability * 0.7, 3)
    replacement_prob = round(failure.failure_probability * 0.3, 3)

    cat = failure.instrument_category or "general_surgery"
    repair_range, replace_range = REPAIR_COSTS.get(cat, (400, 2500))

    # Scale cost estimate by risk
    risk_factor = failure.risk_score / 100
    repair_cost = round(repair_range * (0.5 + risk_factor * 0.5), 2)
    replace_cost = round(replace_range * (0.5 + risk_factor * 0.5), 2)

    action = _repair_action(failure.risk_score, repair_cost, replace_cost)

    # Enrich evidence with cost signal
    evidence = list(failure.evidence)
    evidence.append(EvidenceFactor(
        factor="repair_vs_replace_ratio",
        value=round(repair_cost / max(replace_cost, 1), 3),
        weight=0.10,
        signal="repair_preferred" if repair_cost < replace_cost * 0.4 else "evaluate_replacement",
    ))

    return RepairForecastResult(
        instrument_name=instrument_name,
        instrument_category=cat,
        tenant_id=tenant_id,
        facility_id=facility_id,
        prediction_date=now,
        repair_probability_90d=repair_prob,
        replacement_probability_180d=replacement_prob,
        risk_score=failure.risk_score,
        risk_category=failure.risk_category,
        confidence=failure.confidence,
        estimated_repair_cost_usd=repair_cost,
        estimated_replacement_cost_usd=replace_cost,
        recommended_action=action,
        records_used=failure.records_used,
        evidence=evidence,
        data_source=failure.data_source,
    )


def _repair_action(score: float, repair_cost: float, replace_cost: float) -> str:
    if score >= 75:
        if repair_cost > replace_cost * 0.5:
            return _sanitize(f"Replacement recommended (est. ${replace_cost:,.0f}). Cost of repeated repair exceeds replacement threshold.")
        return _sanitize(f"Immediate repair required (est. ${repair_cost:,.0f}). Schedule within 48 hours.")
    if score >= 50:
        return _sanitize(f"Preventive repair advised (est. ${repair_cost:,.0f}). Schedule within 30 days to avoid emergency replacement.")
    if score >= 25:
        return _sanitize(f"Budget for potential repair (est. ${repair_cost:,.0f}) in next quarter. Continue monitoring.")
    return _sanitize("No repair action required at this time.")


# ── Recall Risk Assessment ────────────────────────────────────────────────────

def assess_recall_risk(
    tenant_id: str,
    instrument_category: str,
    db=None,
) -> RecallRiskAssessmentResult:
    now = _now_str()
    active_recalls = 0
    critical_recalls = 0

    if db is not None:
        try:
            from app.models.vendor_intelligence import RecallEvent
            recalls = db.query(RecallEvent).filter(
                RecallEvent.tenant_id == tenant_id,
                RecallEvent.status.in_(["active", "monitoring"]),
            ).all()

            for r in recalls:
                cats = json.loads(r.affected_instrument_categories or "[]")
                if instrument_category in cats or not cats:
                    active_recalls += 1
                    if r.severity in ("class_i",):
                        critical_recalls += 1
        except Exception:
            pass

    # Also check SharedDefectSignal for category-level risk
    shared_signal_score = 0.0
    if db is not None:
        try:
            from app.models.vendor_intelligence import SharedDefectSignal
            signals = db.query(SharedDefectSignal).filter(
                SharedDefectSignal.instrument_category == instrument_category,
                SharedDefectSignal.is_active.is_(True),
            ).all()
            if signals:
                max_occ = max(s.occurrence_count for s in signals)
                shared_signal_score = min(30, max_occ / 10)
        except Exception:
            pass

    # Recall exposure score
    exposure_score = min(100, active_recalls * 20 + critical_recalls * 30 + shared_signal_score)
    instruments_est = active_recalls * 3  # rough estimate

    evidence = [
        EvidenceFactor(factor="active_recall_count", value=active_recalls, weight=0.40,
                       signal="elevated" if active_recalls > 1 else "stable"),
        EvidenceFactor(factor="critical_recall_count", value=critical_recalls, weight=0.40,
                       signal="elevated" if critical_recalls > 0 else "stable"),
        EvidenceFactor(factor="shared_defect_signal_score", value=round(shared_signal_score, 1), weight=0.20,
                       signal="elevated" if shared_signal_score > 10 else "stable"),
    ]

    data_source = "real" if (db is not None) else "mock"
    if data_source == "mock" or (active_recalls == 0 and db is not None):
        # Use mock for plausible demo data when no recalls exist
        rng = _seed(f"recall:{tenant_id}:{instrument_category}")
        exposure_score = round(rng.uniform(5, 60), 1)
        active_recalls = rng.randint(0, 3)
        critical_recalls = rng.randint(0, 1)
        instruments_est = rng.randint(0, 15)
        data_source = "mock"

    return RecallRiskAssessmentResult(
        instrument_category=instrument_category,
        tenant_id=tenant_id,
        assessment_date=now,
        exposure_score=round(exposure_score, 1),
        active_recall_count=active_recalls,
        critical_recall_count=critical_recalls,
        instruments_affected_estimate=instruments_est,
        urgency_tier=_urgency_tier(exposure_score),
        evidence=evidence,
        recommended_action=_recall_action(exposure_score, critical_recalls),
        data_source=data_source,
    )


def _recall_action(score: float, critical: int) -> str:
    if critical > 0:
        return _sanitize("URGENT: Active Class I recall affects this category. Immediately identify and quarantine affected lot numbers. Notify clinical leadership.")
    if score >= 50:
        return _sanitize("Active recall monitoring required. Cross-reference lot numbers against instrument inventory within 24 hours.")
    if score >= 25:
        return _sanitize("Watch status: review active advisories for this instrument category at next scheduled audit.")
    return _sanitize("No active recall exposure detected. Continue standard recall monitoring.")


# ── Tray Risk Assessment ──────────────────────────────────────────────────────

def assess_tray_risk(
    tenant_id: str,
    tray_id: str,
    facility_id: str = "",
    db=None,
) -> TrayRiskAssessmentResult:
    now = _now_str()

    if db is not None:
        try:
            from app.models.cv_inference import CVInferenceRecord
            q = db.query(CVInferenceRecord).filter(
                CVInferenceRecord.tenant_id == tenant_id,
            )
            if facility_id:
                q = q.filter(CVInferenceRecord.facility_id == facility_id)
            records = q.all()

            if records:
                # Group by instrument_name as proxy for instruments in tray
                by_instrument: dict[str, list] = {}
                for r in records:
                    by_instrument.setdefault(r.instrument_name, []).append(r)

                instrument_risks = []
                for iname, irecs in list(by_instrument.items())[:20]:
                    pred = _compute_failure_from_records(
                        irecs, tenant_id, iname, facility_id, 90, now
                    )
                    instrument_risks.append((iname, pred.risk_score, pred.failure_probability))

                if instrument_risks:
                    instrument_risks.sort(key=lambda x: x[1], reverse=True)
                    tray_risk = min(100, sum(r[1] for r in instrument_risks) / len(instrument_risks) * 1.2)
                    high_risk = sum(1 for r in instrument_risks if r[1] >= 50)
                    worst = instrument_risks[0]

                    evidence = [
                        EvidenceFactor(factor="instrument_count", value=len(instrument_risks), weight=0.20,
                                       signal="stable"),
                        EvidenceFactor(factor="high_risk_instrument_count", value=high_risk, weight=0.40,
                                       signal="elevated" if high_risk > 1 else "stable"),
                        EvidenceFactor(factor="worst_instrument_risk_score", value=round(worst[1], 1), weight=0.40,
                                       signal=_risk_category(worst[1])),
                    ]

                    return TrayRiskAssessmentResult(
                        tray_id=tray_id,
                        tenant_id=tenant_id,
                        facility_id=facility_id,
                        assessment_date=now,
                        tray_risk_score=round(tray_risk, 1),
                        risk_category=_risk_category(tray_risk),
                        instrument_count=len(instrument_risks),
                        high_risk_instrument_count=high_risk,
                        highest_risk_instrument=worst[0],
                        worst_failure_probability=round(worst[2], 3),
                        recommended_action=_tray_action(tray_risk, worst[0]),
                        evidence=evidence,
                        data_source="real",
                    )
        except Exception:
            pass

    # Mock fallback
    rng = _seed(f"tray:{tenant_id}:{tray_id}")
    tray_risk = round(rng.uniform(10, 80), 1)
    n_instruments = rng.randint(8, 24)
    high_risk = rng.randint(0, max(1, n_instruments // 4))
    mock_instruments = ["Laparoscopic Trocar", "Needle Driver", "Curved Scissors", "Clip Applier"]
    worst = rng.choice(mock_instruments)
    worst_prob = round(rng.uniform(0.1, 0.8), 3)

    evidence = [
        EvidenceFactor(factor="instrument_count", value=n_instruments, weight=0.20, signal="stable"),
        EvidenceFactor(factor="high_risk_instrument_count", value=high_risk, weight=0.40,
                       signal="elevated" if high_risk > 2 else "stable"),
        EvidenceFactor(factor="worst_instrument_risk_score", value=round(tray_risk * 1.1, 1), weight=0.40,
                       signal=_risk_category(tray_risk)),
    ]

    return TrayRiskAssessmentResult(
        tray_id=tray_id,
        tenant_id=tenant_id,
        facility_id=facility_id,
        assessment_date=now,
        tray_risk_score=tray_risk,
        risk_category=_risk_category(tray_risk),
        instrument_count=n_instruments,
        high_risk_instrument_count=high_risk,
        highest_risk_instrument=worst,
        worst_failure_probability=worst_prob,
        recommended_action=_tray_action(tray_risk, worst),
        evidence=evidence,
        data_source="mock",
    )


def _tray_action(score: float, worst_instrument: str) -> str:
    if score >= 75:
        return _sanitize(f"Tray at critical risk. Pull '{worst_instrument}' from service. Full tray inspection required before next surgical use.")
    if score >= 50:
        return _sanitize(f"Tray at high risk. Priority inspection of '{worst_instrument}' before next use. Review remaining instruments.")
    if score >= 25:
        return _sanitize(f"Tray at moderate risk. Schedule '{worst_instrument}' for next maintenance cycle.")
    return _sanitize("Tray risk within acceptable range. Continue standard inspection protocol.")


# ── Batch / List functions ────────────────────────────────────────────────────

def predict_failures_for_tenant(
    tenant_id: str,
    facility_id: str = "",
    horizon_days: int = 30,
    limit: int = 20,
    db=None,
) -> list[InstrumentFailurePredictionResult]:
    """Return failure predictions for top instruments in a tenant."""
    instrument_names = _get_instrument_names(tenant_id, facility_id, limit, db)
    return [
        predict_instrument_failure(tenant_id, name, facility_id, horizon_days, db)
        for name in instrument_names
    ]


def predict_contamination_for_tenant(
    tenant_id: str,
    facility_id: str = "",
    limit: int = 20,
    db=None,
) -> list[ContaminationRecurrencePredictionResult]:
    instrument_names = _get_instrument_names(tenant_id, facility_id, limit, db)
    return [
        predict_contamination_recurrence(tenant_id, name, facility_id, db)
        for name in instrument_names
    ]


def forecast_repairs_for_tenant(
    tenant_id: str,
    facility_id: str = "",
    limit: int = 20,
    db=None,
) -> list[RepairForecastResult]:
    instrument_names = _get_instrument_names(tenant_id, facility_id, limit, db)
    return [forecast_repair(tenant_id, name, facility_id, db) for name in instrument_names]


def assess_recall_risk_all_categories(
    tenant_id: str,
    db=None,
) -> list[RecallRiskAssessmentResult]:
    categories = ["laparoscopic", "endoscopic", "orthopedic", "cardiac", "general_surgery"]
    return [assess_recall_risk(tenant_id, cat, db) for cat in categories]


def _get_instrument_by_id(tenant_id: str, instrument_id: str, db) -> list:
    """Get CVInferenceRecord rows for a specific instrument_id (barcode/QR)."""
    if db is not None and instrument_id:
        try:
            from app.models.cv_inference import CVInferenceRecord
            return db.query(CVInferenceRecord).filter(
                CVInferenceRecord.tenant_id == tenant_id,
                CVInferenceRecord.barcode_value == instrument_id,
            ).order_by(CVInferenceRecord.id.desc()).limit(20).all()
        except Exception:
            pass
    return []


def _get_instrument_names(tenant_id: str, facility_id: str, limit: int, db) -> list[str]:
    if db is not None:
        try:
            from app.models.cv_inference import CVInferenceRecord
            q = db.query(CVInferenceRecord.instrument_name).filter(
                CVInferenceRecord.tenant_id == tenant_id,
                CVInferenceRecord.instrument_name != "",
            )
            if facility_id:
                q = q.filter(CVInferenceRecord.facility_id == facility_id)
            rows = q.distinct().limit(limit).all()
            if rows:
                return [r[0] for r in rows]
        except Exception:
            pass
    # Mock instrument list
    return [
        "Laparoscopic Trocar 5mm", "Laparoscopic Trocar 10mm", "Needle Driver",
        "Curved Scissors", "Clip Applier", "Lumen Suction Tube", "Endoscope OE-300",
        "Orthopedic Drill Bit Set", "Cardiac Retractor", "Bipolar Forceps",
    ][:limit]


# ── Predictive Dashboard ──────────────────────────────────────────────────────

def compute_predictive_dashboard(
    tenant_id: str,
    facility_id: str = "",
    db=None,
) -> PredictiveDashboard:
    now = _now_str()

    failures_30 = predict_failures_for_tenant(tenant_id, facility_id, 30, 20, db)
    failures_90 = predict_failures_for_tenant(tenant_id, facility_id, 90, 20, db)
    contamination = predict_contamination_for_tenant(tenant_id, facility_id, 20, db)
    repairs = forecast_repairs_for_tenant(tenant_id, facility_id, 20, db)
    recall_risks = assess_recall_risk_all_categories(tenant_id, db)

    # KPI rollups
    predicted_failures_30d = sum(1 for f in failures_30 if f.risk_score >= 50)
    predicted_failures_90d = sum(1 for f in failures_90 if f.risk_score >= 50)
    high_risk = sum(1 for f in failures_30 if f.risk_category in ("high",))
    critical_risk = sum(1 for f in failures_30 if f.risk_category == "critical")
    projected_repair = sum(r.estimated_repair_cost_usd for r in repairs if r.risk_score >= 25)
    projected_replace = sum(r.estimated_replacement_cost_usd for r in repairs if r.risk_score >= 75)

    # Contamination recurrence rate
    contam_high = sum(1 for c in contamination if c.risk_score >= 50)
    contam_rate = round(contam_high / max(1, len(contamination)) * 100, 1)

    # Max recall exposure
    recall_exposure = max((r.exposure_score for r in recall_risks), default=0.0)

    # Leaderboards
    highest_risk_instruments = sorted(
        [{"instrument_name": f.instrument_name, "risk_score": f.risk_score,
          "risk_category": f.risk_category, "failure_probability": f.failure_probability,
          "recommended_action": f.recommended_action}
         for f in failures_30], key=lambda x: x["risk_score"], reverse=True
    )[:5]

    top_contamination = sorted(
        [{"instrument_name": c.instrument_name, "risk_score": c.risk_score,
          "dominant_contaminant": c.dominant_contaminant, "recurrence_probability": c.recurrence_probability}
         for c in contamination], key=lambda x: x["risk_score"], reverse=True
    )[:5]

    recall_by_cat = sorted(
        [{"instrument_category": r.instrument_category, "exposure_score": r.exposure_score,
          "urgency_tier": r.urgency_tier, "active_recall_count": r.active_recall_count}
         for r in recall_risks], key=lambda x: x["exposure_score"], reverse=True
    )

    # Top risk factors (from highest-risk instruments)
    factor_counts: dict[str, int] = {}
    for f in failures_30:
        for ev in f.evidence:
            if ev.signal in ("degrading", "elevated", "below_threshold"):
                factor_counts[ev.factor] = factor_counts.get(ev.factor, 0) + 1
    top_factors = [f for f, _ in sorted(factor_counts.items(), key=lambda x: x[1], reverse=True)][:5]
    top_factors_display = [f.replace("_", " ").title() for f in top_factors]

    recommended_actions = []
    if critical_risk > 0:
        recommended_actions.append(f"Pull {critical_risk} critical-risk instrument(s) from service for immediate inspection.")
    if contam_rate > 30:
        recommended_actions.append("Contamination recurrence rate elevated. Audit decontamination protocols.")
    if recall_exposure > 50:
        recommended_actions.append("High recall exposure detected. Cross-reference lot numbers against active recalls.")
    if projected_repair > 5000:
        recommended_actions.append(f"Budget ${projected_repair:,.0f} for repair costs in next 90 days.")

    # ROI = cost difference between catching at medium risk (preventive) vs critical (emergency)
    # Emergency repair costs ~2.5x preventive maintenance cost
    # Count instruments currently at medium risk (25-49) — catching them now avoids emergency cost
    medium_risk_repairs = [r for r in repairs if 25 <= r.risk_score < 50]
    repair_avoidance = sum(r.estimated_repair_cost_usd * 1.5 for r in medium_risk_repairs)
    repair_avoidance_roi_usd = round(repair_avoidance, 2)

    data_sources = {f.data_source for f in failures_30}
    data_source = "real" if "real" in data_sources else "mock"

    return PredictiveDashboard(
        tenant_id=tenant_id,
        facility_id=facility_id,
        generated_at=now,
        data_source=data_source,
        predicted_failures_30d=predicted_failures_30d,
        predicted_failures_90d=predicted_failures_90d,
        high_risk_instrument_count=high_risk,
        critical_risk_instrument_count=critical_risk,
        projected_repair_cost_usd=round(projected_repair, 2),
        projected_replacement_cost_usd=round(projected_replace, 2),
        contamination_recurrence_rate_pct=contam_rate,
        recall_exposure_score=round(recall_exposure, 1),
        highest_risk_instruments=highest_risk_instruments,
        top_contamination_risks=top_contamination,
        recall_risk_by_category=recall_by_cat,
        repair_avoidance_roi_usd=repair_avoidance_roi_usd,
        top_risk_factors=top_factors_display,
        recommended_actions=recommended_actions,
    )
