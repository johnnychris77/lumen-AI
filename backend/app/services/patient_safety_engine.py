"""
Patient Safety Correlation Engine.

IMPORTANT DISCLAIMER: This engine identifies POTENTIAL ASSOCIATIONS between
instrument quality signals and patient safety events for human review purposes.
It does NOT establish, imply, or claim causation. All outputs require human
clinical and quality review before any action is taken.
"""
from __future__ import annotations

import hashlib
import random
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.models.external_connector import ExternalEventImport
from app.models.patient_safety import (
    CAPAEffectivenessSignal,
    ExecutiveRiskSignal,
    InfectionPreventionSignal,
    InstrumentQualitySignal,
    NearMissCorrelation,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

DISCLAIMER = (
    "These signals represent potential associations for human review. "
    "They do not establish causation."
)

_RISK_TIER_MAP: dict[str, str] = {
    "contamination_release": "critical",
    "recall_exposure": "critical",
    "repeat_blood_finding": "critical",
    "baseline_deviation": "high",
    "repeat_failure": "high",
    "unresolved_capa": "high",
    "vendor_scorecard_decline": "medium",
    "predictive_failure_alert": "medium",
    "minor_finding": "low",
    "single_override": "low",
}

_CONFIDENCE_MAP: dict[str, float] = {
    "critical": 0.85,
    "high": 0.70,
    "medium": 0.50,
    "low": 0.30,
}

_ASSOCIATION_REASON_MAP: dict[str, str] = {
    "contamination_release": (
        "Instrument flagged as a review candidate due to a potential association with a "
        "contamination release event; human clinical and quality review required before any determination."
    ),
    "recall_exposure": (
        "Instrument may be associated with a recalled product or lot; flagged for human review "
        "as a potential safety signal — no causation is implied."
    ),
    "repeat_blood_finding": (
        "Recurrent blood residue findings on this instrument represent a potential association "
        "with inadequate reprocessing; flagged for investigation review."
    ),
    "baseline_deviation": (
        "Instrument processing parameters deviated from validated baseline; flagged as a "
        "potential association with quality risk for human review."
    ),
    "repeat_failure": (
        "Pattern of repeated failures on this instrument is linked for investigation as a "
        "potential association with systemic reprocessing issues."
    ),
    "unresolved_capa": (
        "Unresolved corrective action may be associated with ongoing quality risk; "
        "flagged for quality team review."
    ),
    "vendor_scorecard_decline": (
        "Vendor quality scorecard decline represents a potential association with instrument "
        "supply quality risk; flagged for procurement and quality review."
    ),
    "predictive_failure_alert": (
        "Predictive analytics flagged this instrument as a potential failure candidate; "
        "review recommended — no confirmed defect established."
    ),
    "minor_finding": (
        "Minor inspection finding flagged as a review candidate; human review required "
        "to assess whether further action is warranted."
    ),
    "single_override": (
        "Single process override logged; flagged for quality review as a potential "
        "association with non-compliant reprocessing."
    ),
}

_REVIEW_ACTION_MAP: dict[str, str] = {
    "contamination_release": (
        "Quarantine instrument and initiate contamination review. Flagged for human review — "
        "do not return to service until clinical and quality determination is complete."
    ),
    "recall_exposure": (
        "Cross-reference instrument lot against recall database. Flagged for human review; "
        "consult manufacturer guidance before returning to service."
    ),
    "repeat_blood_finding": (
        "Conduct immediate reprocessing audit for this instrument. Flagged for human review; "
        "consider removing from rotation pending investigation."
    ),
    "baseline_deviation": (
        "Review cycle documentation and validate reprocessing parameters. "
        "Flagged for human review — quality team assessment required."
    ),
    "repeat_failure": (
        "Initiate formal investigation into instrument failure pattern. Flagged for human review; "
        "consider service or replacement evaluation."
    ),
    "unresolved_capa": (
        "Escalate CAPA to quality leadership. Flagged for human review; confirm corrective "
        "action effectiveness before closing."
    ),
    "vendor_scorecard_decline": (
        "Review vendor quality metrics and recent deliveries. Flagged for human review; "
        "consider enhanced incoming inspection."
    ),
    "predictive_failure_alert": (
        "Schedule preventive maintenance or inspection. Flagged for human review — "
        "predictive signal only, no confirmed defect."
    ),
    "minor_finding": (
        "Document and monitor. Flagged for human review; assess whether pattern warrants escalation."
    ),
    "single_override": (
        "Review override justification and retrain if needed. Flagged for human review."
    ),
}


def _seed(s: str) -> random.Random:
    h = hashlib.md5(s.encode()).hexdigest()[:8]
    return random.Random(int(h, 16))


def _risk_tier_for(event_type: str) -> str:
    return _RISK_TIER_MAP.get(event_type, "low")


def _confidence_for(risk_tier: str) -> float:
    return _CONFIDENCE_MAP.get(risk_tier, 0.30)


# ---------------------------------------------------------------------------
# Core engine functions
# ---------------------------------------------------------------------------


def compute_quality_signal(
    db: Session,
    tenant_id: str,
    facility_id: str,
    event_source: str,
    event_type: str,
    instrument_id: str | None = None,
    vendor_id: str | None = None,
) -> InstrumentQualitySignal:
    """
    Create an InstrumentQualitySignal for the given event.

    Assigns risk tier, confidence score, association reason, and recommended
    review action based on event type. All outputs use potential-association
    language; no causation is implied.
    """
    risk_tier = _risk_tier_for(event_type)
    confidence_score = _confidence_for(risk_tier)
    association_reason = _ASSOCIATION_REASON_MAP.get(
        event_type,
        (
            f"Instrument flagged as a review candidate due to a potential association with "
            f"a '{event_type}' event; human review required before any determination."
        ),
    )
    recommended_review_action = _REVIEW_ACTION_MAP.get(
        event_type,
        "Flagged for human review — quality team assessment required before any action.",
    )

    signal = InstrumentQualitySignal(
        tenant_id=tenant_id,
        facility_id=facility_id or None,
        instrument_id=instrument_id,
        vendor_id=vendor_id,
        event_source=event_source,
        event_type=event_type,
        event_date=datetime.utcnow(),
        confidence_score=confidence_score,
        association_reason=association_reason,
        recommended_review_action=recommended_review_action,
        human_review_required=True,
        human_review_status="pending",
        risk_tier=risk_tier,
    )
    db.add(signal)
    db.commit()
    db.refresh(signal)
    return signal


def correlate_signals(
    db: Session,
    tenant_id: str,
    facility_id: str = "",
    days_back: int = 90,
) -> dict[str, Any]:
    """
    Pull quality signals for the tenant within the look-back window,
    group by (instrument_id, event_type), and produce:
    - NearMissCorrelation for each group with count >= 2
    - ExecutiveRiskSignal for each critical/high tier signal

    Returns dict with correlation summary.
    """
    cutoff = datetime.utcnow() - timedelta(days=days_back)
    query = db.query(InstrumentQualitySignal).filter(
        InstrumentQualitySignal.tenant_id == tenant_id,
        InstrumentQualitySignal.created_at >= cutoff,
    )
    if facility_id:
        query = query.filter(InstrumentQualitySignal.facility_id == facility_id)

    signals = query.all()

    if not signals:
        # Seeded mock fallback
        rng = _seed(f"{tenant_id}:{facility_id}:{days_back}:correlate")
        signals_analyzed = rng.randint(12, 48)
        correlations_found = rng.randint(2, 8)
        near_misses = rng.randint(1, 4)
        executive_risks = rng.randint(1, 3)
        return {
            "signals_analyzed": signals_analyzed,
            "correlations_found": correlations_found,
            "near_misses": near_misses,
            "executive_risks": executive_risks,
            "human_review_required": True,
            "data_source": "mock",
            "disclaimer": DISCLAIMER,
        }

    # Group by (instrument_id, event_type)
    groups: dict[tuple, list[InstrumentQualitySignal]] = {}
    for sig in signals:
        key = (sig.instrument_id, sig.event_type)
        groups.setdefault(key, []).append(sig)

    near_miss_count = 0
    exec_risk_count = 0

    for (instrument_id, event_type), group in groups.items():
        if len(group) >= 2:
            confidence = min(0.95, _confidence_for(_risk_tier_for(event_type)) + 0.1 * len(group))
            nm = NearMissCorrelation(
                tenant_id=tenant_id,
                facility_id=facility_id or None,
                instrument_id=instrument_id,
                event_source=group[0].event_source,
                event_type=event_type,
                event_date=datetime.utcnow(),
                confidence_score=confidence,
                association_reason=(
                    f"Recurrence of '{event_type}' events on instrument linked for investigation "
                    f"as a potential association pattern ({len(group)} occurrences in {days_back} days); "
                    "human review required — no causation implied."
                ),
                recommended_review_action=(
                    "Review recurrence pattern and initiate quality investigation. "
                    "Flagged for human review."
                ),
                human_review_required=True,
                human_review_status="pending",
                near_miss_category="recurrence_pattern",
            )
            db.add(nm)
            near_miss_count += 1

    for sig in signals:
        if sig.risk_tier in ("critical", "high"):
            er = ExecutiveRiskSignal(
                tenant_id=tenant_id,
                facility_id=facility_id or None,
                instrument_id=sig.instrument_id,
                vendor_id=sig.vendor_id,
                event_source=sig.event_source,
                event_type=sig.event_type,
                event_date=datetime.utcnow(),
                confidence_score=sig.confidence_score,
                association_reason=(
                    f"Signal of type '{sig.event_type}' (risk tier: {sig.risk_tier}) "
                    "flagged for executive review as a potential association with elevated quality risk; "
                    "no causation is established."
                ),
                recommended_review_action=(
                    "Escalate to quality leadership for executive review. "
                    "Flagged for human review — no action without clinical/quality determination."
                ),
                human_review_required=True,
                human_review_status="pending",
                risk_tier=sig.risk_tier,
            )
            db.add(er)
            exec_risk_count += 1

    db.commit()

    return {
        "signals_analyzed": len(signals),
        "correlations_found": len(groups),
        "near_misses": near_miss_count,
        "executive_risks": exec_risk_count,
        "human_review_required": True,
        "data_source": "real",
        "disclaimer": DISCLAIMER,
    }


def score_infection_prevention_signal(
    db: Session,
    tenant_id: str,
    event_source: str,
    facility_id: str = "",
    pathogen: str | None = None,
    procedure_type: str | None = None,
) -> InfectionPreventionSignal:
    """
    Create an InfectionPreventionSignal.

    Confidence is elevated for high-concern pathogens (MRSA, C. diff).
    All outputs use potential-association language.
    """
    high_concern = {"mrsa", "c.diff", "cdiff", "c. difficile", "clostridium difficile"}
    confidence = 0.75 if (pathogen or "").lower() in high_concern else 0.50

    sig = InfectionPreventionSignal(
        tenant_id=tenant_id,
        facility_id=facility_id or None,
        event_source=event_source,
        event_type="hai_review_candidate",
        event_date=datetime.utcnow(),
        confidence_score=confidence,
        association_reason=(
            "This signal is flagged for infection prevention review as a potential association "
            "with instrument processing; clinical determination required."
        ),
        recommended_review_action=(
            "Refer to infection prevention team for clinical review. "
            "Flagged for human review — no causation is implied."
        ),
        human_review_required=True,
        human_review_status="pending",
        pathogen=pathogen,
        procedure_type=procedure_type,
    )
    db.add(sig)
    db.commit()
    db.refresh(sig)
    return sig


def get_dashboard_rollup(
    db: Session,
    tenant_id: str,
    facility_id: str = "",
    period_days: int = 30,
) -> dict[str, Any]:
    """
    Return KPI rollup for the patient safety dashboard.

    DB-first: queries real tables; falls back to seeded mock if all counts are zero.
    """
    from app.models.patient_safety import (
        ExecutiveRiskSignal,
        InfectionPreventionSignal,
        InstrumentQualitySignal,
        NearMissCorrelation,
    )

    cutoff = datetime.utcnow() - timedelta(days=period_days)

    def _fq(model):
        q = db.query(model).filter(
            model.tenant_id == tenant_id,
            model.created_at >= cutoff,
        )
        if facility_id and hasattr(model, "facility_id"):
            q = q.filter(model.facility_id == facility_id)
        return q

    total_quality_signals = _fq(InstrumentQualitySignal).count()
    high_critical_signals = (
        _fq(InstrumentQualitySignal)
        .filter(InstrumentQualitySignal.risk_tier.in_(["high", "critical"]))
        .count()
    )
    near_misses_flagged = _fq(NearMissCorrelation).count()
    executive_risks_open = (
        _fq(ExecutiveRiskSignal)
        .filter(ExecutiveRiskSignal.human_review_status == "pending")
        .count()
    )
    ip_signals_pending_review = (
        _fq(InfectionPreventionSignal)
        .filter(InfectionPreventionSignal.human_review_status == "pending")
        .count()
    )
    capa_recurrences_detected = (
        _fq(CAPAEffectivenessSignal)
        .filter(CAPAEffectivenessSignal.event_type == "recurrence_detected")
        .count()
    )

    # Unique instruments/vendors
    from sqlalchemy import func as sqlfunc

    instruments_with_signals = (
        db.query(sqlfunc.count(sqlfunc.distinct(InstrumentQualitySignal.instrument_id)))
        .filter(
            InstrumentQualitySignal.tenant_id == tenant_id,
            InstrumentQualitySignal.created_at >= cutoff,
            InstrumentQualitySignal.instrument_id.isnot(None),
        )
        .scalar()
        or 0
    )
    vendors_with_signals = (
        db.query(sqlfunc.count(sqlfunc.distinct(InstrumentQualitySignal.vendor_id)))
        .filter(
            InstrumentQualitySignal.tenant_id == tenant_id,
            InstrumentQualitySignal.created_at >= cutoff,
            InstrumentQualitySignal.vendor_id.isnot(None),
        )
        .scalar()
        or 0
    )

    human_review_required_count = (
        _fq(InstrumentQualitySignal)
        .filter(InstrumentQualitySignal.human_review_required == True)  # noqa: E712
        .count()
    )

    data_source = "real"

    if (
        total_quality_signals == 0
        and near_misses_flagged == 0
        and executive_risks_open == 0
    ):
        rng = _seed(f"{tenant_id}:{facility_id}:{period_days}:dashboard")
        total_quality_signals = rng.randint(15, 60)
        high_critical_signals = rng.randint(2, 12)
        near_misses_flagged = rng.randint(1, 8)
        executive_risks_open = rng.randint(1, 5)
        ip_signals_pending_review = rng.randint(0, 6)
        capa_recurrences_detected = rng.randint(0, 4)
        instruments_with_signals = rng.randint(3, 20)
        vendors_with_signals = rng.randint(1, 6)
        human_review_required_count = total_quality_signals
        data_source = "mock"

    return {
        "total_quality_signals": total_quality_signals,
        "high_critical_signals": high_critical_signals,
        "near_misses_flagged": near_misses_flagged,
        "executive_risks_open": executive_risks_open,
        "ip_signals_pending_review": ip_signals_pending_review,
        "capa_recurrences_detected": capa_recurrences_detected,
        "instruments_with_signals": instruments_with_signals,
        "vendors_with_signals": vendors_with_signals,
        "human_review_required_count": human_review_required_count,
        "human_review_required": True,
        "data_source": data_source,
        "disclaimer": DISCLAIMER,
    }


def import_external_events(
    db: Session,
    tenant_id: str,
    facility_id: str,
    events: list[dict],
) -> dict[str, Any]:
    """
    Import a list of external events, creating ExternalEventImport records and
    triggering compute_quality_signal for each importable event.
    """
    import hashlib as _hashlib
    import json as _json

    imported = 0
    signals_generated = 0
    errors: list[str] = []

    for ev in events:
        try:
            raw_hash = _hashlib.sha256(
                _json.dumps(ev, sort_keys=True, default=str).encode()
            ).hexdigest()

            event_date_raw = ev.get("event_date") or ev.get("date")
            if isinstance(event_date_raw, str):
                try:
                    event_date = datetime.fromisoformat(event_date_raw)
                except ValueError:
                    event_date = datetime.utcnow()
            elif isinstance(event_date_raw, datetime):
                event_date = event_date_raw
            else:
                event_date = datetime.utcnow()

            imp = ExternalEventImport(
                tenant_id=tenant_id,
                facility_id=facility_id or None,
                external_event_id=str(ev.get("id") or ev.get("external_id") or ""),
                event_type=ev.get("event_type", "adverse_event"),
                event_date=event_date,
                instrument_reference=ev.get("instrument_id") or ev.get("instrument_reference"),
                de_identified=ev.get("de_identified", True),
                raw_payload_hash=raw_hash,
            )
            db.add(imp)
            imported += 1

            # Generate quality signal
            compute_quality_signal(
                db=db,
                tenant_id=tenant_id,
                facility_id=facility_id,
                event_source=ev.get("source_system", "external"),
                event_type=ev.get("event_type", "minor_finding"),
                instrument_id=ev.get("instrument_id") or ev.get("instrument_reference"),
                vendor_id=ev.get("vendor_id"),
            )
            signals_generated += 1

        except Exception as exc:  # noqa: BLE001
            errors.append(str(exc))

    db.commit()
    return {"imported": imported, "signals_generated": signals_generated, "errors": errors}
