"""v4.5 — Project Orbit, Section 5: Readiness Alert Engine.

Extends Project Symphony's existing `CaseRiskAlert` table/detection
pipeline (`or_connect_service.detect_operational_risks`) rather than
building a second alert table for the same case. Five risk types are
genuinely new (missing instrument, missing implant, high-risk Digital
Twin, equipment unavailable, knowledge advisory — the other four named
in the brief already exist as `RISK_VENDOR_TRAY_NOT_RECEIVED`/
`RISK_INSPECTION_OVERDUE`/`RISK_REPAIR_INCOMPLETE`/
`RISK_SUPERVISOR_REVIEW_PENDING`), detected here from real Orbit tables
and real Digital Twin/knowledge data — never fabricated.

"Every alert includes recommended next actions" (Section 5): every risk
type, old and new, is mapped to a recommended action string. New alerts
persist it on the row (`CaseRiskAlert.recommended_action`, an additive
column); existing Symphony-generated alerts (created before this column
had a value) are enriched with the same lookup at read time rather than
requiring a backfill migration.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.or_connect import (
    RISK_EQUIPMENT_UNAVAILABLE,
    RISK_HIGH_RISK_DIGITAL_TWIN,
    RISK_KNOWLEDGE_ADVISORY,
    RISK_MISSING_IMPLANT,
    RISK_MISSING_INSTRUMENT,
    TRAY_RECEIVED,
    TRAY_RETURNED,
    CaseRiskAlert,
)
from app.models.orbit_readiness import IMPLANT_MISSING, LoanerEquipment
from app.services import digital_twin_engine, knowledge_repository_service, or_connect_service

_TRAY_AT_RISK_HOURS = 24

_RECOMMENDED_ACTIONS = {
    "vendor_tray_not_received": "Contact the vendor rep to confirm shipment and expedite delivery.",
    "inspection_overdue": "Assign the pending inspection to an available technician now.",
    "baseline_missing": "Request baseline approval from SPD leadership before the case.",
    "repair_incomplete": "Escalate to Clinical Engineering for repair status and confirm a loaner is available.",
    "critical_finding_unresolved": "Route to a supervisor for immediate review before packaging.",
    "supervisor_review_pending": "Notify the on-duty supervisor to complete the pending review.",
    RISK_MISSING_INSTRUMENT: "Confirm tray contents against the case pick list and log any missing instrument for inspection.",
    RISK_MISSING_IMPLANT: "Contact the implant vendor/rep to confirm availability or identify a substitute.",
    RISK_HIGH_RISK_DIGITAL_TWIN: "Review the Digital Twin's open alerts before releasing the instrument for this case.",
    RISK_EQUIPMENT_UNAVAILABLE: "Follow up with the loaner equipment vendor and identify a backup unit.",
    RISK_KNOWLEDGE_ADVISORY: "Review the linked knowledge article's guidance before the case.",
}


def _recommended_action(risk_type: str) -> str:
    return _RECOMMENDED_ACTIONS.get(risk_type, "Review this alert with the responsible department.")


def _already_alerted(db: Session, tenant_id: str, case_id: int, risk_type: str) -> bool:
    return (
        db.query(CaseRiskAlert.id)
        .filter(
            CaseRiskAlert.tenant_id == tenant_id, CaseRiskAlert.case_id == case_id,
            CaseRiskAlert.risk_type == risk_type, CaseRiskAlert.resolved_at.is_(None),
        )
        .first()
        is not None
    )


def _row_to_dict(obj) -> dict:
    result: dict = {}
    for col in obj.__table__.columns:
        val = getattr(obj, col.name)
        if hasattr(val, "isoformat"):
            val = val.isoformat()
        result[col.name] = val
    return result


def _detect_orbit_specific_risks(db: Session, tenant_id: str, case_id: int, *, facility_id: str = "") -> list[CaseRiskAlert]:
    from app.db import models
    from app.models.or_connect import VendorTray
    from app.models.orbit_readiness import ImplantRecord

    case = or_connect_service.get_case_or_404(db, tenant_id, case_id)
    inspections = db.query(models.Inspection).filter(models.Inspection.tenant_id == tenant_id, models.Inspection.case_id == case_id).all()
    trays = db.query(VendorTray).filter(VendorTray.tenant_id == tenant_id, VendorTray.case_id == case_id).all()
    implants = db.query(ImplantRecord).filter(ImplantRecord.tenant_id == tenant_id, ImplantRecord.case_id == case_id).all()
    equipment = db.query(LoanerEquipment).filter(LoanerEquipment.tenant_id == tenant_id, LoanerEquipment.case_id == case_id).all()

    now = datetime.now(timezone.utc)
    scheduled_start = case.scheduled_start if case.scheduled_start.tzinfo else case.scheduled_start.replace(tzinfo=timezone.utc)
    hours_to_case = (scheduled_start - now).total_seconds() / 3600.0
    severity = "critical" if hours_to_case <= 6 else "high" if hours_to_case <= _TRAY_AT_RISK_HOURS else "medium"

    created: list[CaseRiskAlert] = []

    def _emit(risk_type: str, sev: str, message: str) -> None:
        if not _already_alerted(db, tenant_id, case_id, risk_type):
            row = CaseRiskAlert(
                tenant_id=tenant_id, case_id=case_id, risk_type=risk_type, severity=sev, message=message,
                recommended_action=_recommended_action(risk_type),
            )
            db.add(row)
            created.append(row)

    if trays and all(t.status in (TRAY_RECEIVED, TRAY_RETURNED) for t in trays) and not inspections:
        _emit(
            RISK_MISSING_INSTRUMENT, severity,
            f"All trays for {case.case_ref} have arrived but no instrument has been logged for inspection yet.",
        )

    if any(i.status == IMPLANT_MISSING for i in implants):
        missing = [i for i in implants if i.status == IMPLANT_MISSING]
        _emit(
            RISK_MISSING_IMPLANT, severity,
            f"{len(missing)} implant(s) marked missing for {case.case_ref}: " + ", ".join(i.implant_name for i in missing[:5]) + ".",
        )

    if any(e.status in ("requested", "shipped") for e in equipment) and hours_to_case <= _TRAY_AT_RISK_HOURS:
        pending = [e for e in equipment if e.status in ("requested", "shipped")]
        _emit(
            RISK_EQUIPMENT_UNAVAILABLE, severity,
            f"{len(pending)} loaner equipment item(s) not yet received for {case.case_ref}.",
        )

    twin_dashboard = digital_twin_engine.compute_twin_dashboard(tenant_id, facility_id, db)
    high_risk_alerts = [a for a in twin_dashboard.open_alerts if a.severity in ("high", "critical")]
    if high_risk_alerts:
        _emit(
            RISK_HIGH_RISK_DIGITAL_TWIN, "high",
            f"{len(high_risk_alerts)} high/critical Digital Twin alert(s) open for this facility ahead of {case.case_ref}.",
        )

    articles = knowledge_repository_service.list_articles(db, tenant_id, procedure=case.procedure, approval_status="approved")
    advisories = [a for a in articles if a.get("common_mistake") or a.get("prevention_tip")]
    if advisories:
        _emit(
            RISK_KNOWLEDGE_ADVISORY, "low",
            f"{len(advisories)} knowledge advisory note(s) apply to {case.procedure} for {case.case_ref}.",
        )

    db.commit()
    for row in created:
        db.refresh(row)
    return created


def generate_readiness_alerts(db: Session, tenant_id: str, case_id: int, *, facility_id: str = "") -> list[dict]:
    or_connect_service.detect_operational_risks(db, tenant_id, case_id)
    _detect_orbit_specific_risks(db, tenant_id, case_id, facility_id=facility_id)

    all_open = (
        db.query(CaseRiskAlert)
        .filter(CaseRiskAlert.tenant_id == tenant_id, CaseRiskAlert.case_id == case_id, CaseRiskAlert.resolved_at.is_(None))
        .order_by(CaseRiskAlert.id.desc())
        .all()
    )
    result = []
    for r in all_open:
        d = _row_to_dict(r)
        d["recommended_action"] = d["recommended_action"] or _recommended_action(d["risk_type"])
        result.append(d)
    return result
