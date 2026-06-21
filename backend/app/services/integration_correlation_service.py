"""
Integration Correlation Service.

DISCLAIMER: This service identifies POTENTIAL ASSOCIATIONS between
external healthcare system events and LumenAI instrument quality signals
for human review purposes. It does NOT establish, imply, or claim causation.
All correlation candidates require human quality review.
"""
from __future__ import annotations

import hashlib
import random
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.models.integrations import (
    ExternalSystemConnection,
    InfectionPreventionEventRecord,
    IntegrationImportRun,
    InstrumentTrackingRecord,
    PatientImpactCorrelationCandidate,
    QualitySafetyEventRecord,
    SterilizationCycleRecord,
    TrayTrackingRecord,
)

DISCLAIMER = (
    "Correlation candidates represent potential associations identified for human quality review. "
    "They do not establish a direct causal link and require clinical and quality determination."
)

_ASSOCIATION_REASONS = {
    "udi": (
        "Instrument tracking record and quality safety event share UDI identifier — "
        "flagged as investigation candidate for quality review"
    ),
    "instrument_id": (
        "Instrument tracking record and quality safety event share instrument identifier — "
        "flagged as investigation candidate for quality review"
    ),
    "tray_id": (
        "Tray-level tracking record temporally proximate to infection prevention signal — "
        "flagged for infection prevention review"
    ),
    "time_window": (
        "Instrument tracking record and quality safety event occur within a proximate time window — "
        "flagged as near-miss signal for quality review"
    ),
}


def _seed(s: str) -> random.Random:
    h = hashlib.md5(s.encode()).hexdigest()[:8]
    return random.Random(int(h, 16))


def _get_connector(system_name: str, tenant_id: str, facility_id: str, config: dict):
    """Factory: returns the right connector class based on system_name."""
    from app.services.connectors.spd_connectors import (
        AbacusConnector,
        CensiTracConnector,
        ReadySetConnector,
        SPMConnector,
        VendorMadeConnector,
    )
    from app.services.connectors.quality_safety_connectors import (
        MIDASConnector,
        RLDatixConnector,
        SafeCareConnector,
        VergeHealthConnector,
    )
    from app.services.connectors.ip_connectors import (
        ICNetConnector,
        TheradocConnector,
        VigiLanzConnector,
    )

    mapping = {
        "censitrac": CensiTracConnector,
        "spm": SPMConnector,
        "readyset": ReadySetConnector,
        "abacus": AbacusConnector,
        "vendormade": VendorMadeConnector,
        "safecare": SafeCareConnector,
        "rldatix": RLDatixConnector,
        "midas": MIDASConnector,
        "verge": VergeHealthConnector,
        "icnet": ICNetConnector,
        "vigilanz": VigiLanzConnector,
        "theradoc": TheradocConnector,
    }
    cls = mapping.get(system_name.lower())
    if cls is None:
        raise ValueError(f"Unknown system_name: {system_name}")
    return cls(tenant_id, facility_id, config)


def run_correlation(
    db: Session,
    tenant_id: str,
    facility_id: str = "",
    days_back: int = 30,
) -> dict:
    """
    Identifies potential associations between imported external records.
    Does NOT claim causation. All candidates require human quality review.
    """
    since = datetime.utcnow() - timedelta(days=days_back)
    window = timedelta(days=3)

    q_instr = db.query(InstrumentTrackingRecord).filter(
        InstrumentTrackingRecord.tenant_id == tenant_id,
        InstrumentTrackingRecord.event_timestamp >= since,
    )
    if facility_id:
        q_instr = q_instr.filter(InstrumentTrackingRecord.facility_id == facility_id)
    instr_records = q_instr.all()

    q_qs = db.query(QualitySafetyEventRecord).filter(
        QualitySafetyEventRecord.tenant_id == tenant_id,
        QualitySafetyEventRecord.event_timestamp >= since,
    )
    if facility_id:
        q_qs = q_qs.filter(QualitySafetyEventRecord.facility_id == facility_id)
    qs_records = q_qs.all()

    q_ip = db.query(InfectionPreventionEventRecord).filter(
        InfectionPreventionEventRecord.tenant_id == tenant_id,
        InfectionPreventionEventRecord.event_timestamp >= since,
    )
    if facility_id:
        q_ip = q_ip.filter(InfectionPreventionEventRecord.facility_id == facility_id)
    ip_records = q_ip.all()

    records_analyzed = len(instr_records) + len(qs_records) + len(ip_records)
    candidates_created = 0
    data_source = "real"

    if records_analyzed == 0:
        # Seeded mock fallback
        data_source = "mock"
        rng = _seed(tenant_id + "correlation")
        candidates_created = rng.randint(2, 8)
        return {
            "candidates_created": candidates_created,
            "records_analyzed": rng.randint(30, 150),
            "data_source": data_source,
            "disclaimer": DISCLAIMER,
        }

    # Build lookup maps
    inst_map: dict[str, list] = {}
    tray_map: dict[str, list] = {}

    for r in qs_records:
        if r.instrument_reference:
            inst_map.setdefault(r.instrument_reference, []).append(r)
        if r.tray_reference:
            tray_map.setdefault(r.tray_reference, []).append(r)

    for r in ip_records:
        if r.instrument_reference:
            inst_map.setdefault(r.instrument_reference, []).append(r)

    # Match instrument tracking records against quality/IP events
    for itr in instr_records:
        matched_qs: Optional[QualitySafetyEventRecord] = None
        matched_ip: Optional[InfectionPreventionEventRecord] = None
        method = None
        score = 0.0
        reason_key = "time_window"

        # UDI match (highest confidence)
        if itr.udi:
            for qs in qs_records:
                if qs.instrument_reference == itr.udi:
                    matched_qs = qs
                    method = "udi_match"
                    score = 0.8
                    reason_key = "udi"
                    break

        # Instrument ID match
        if not matched_qs and itr.instrument_id:
            for qs in qs_records:
                if qs.instrument_reference == itr.instrument_id:
                    matched_qs = qs
                    method = "instrument_id_match"
                    score = 0.6
                    reason_key = "instrument_id"
                    break

        # Tray ID match
        if not matched_qs and itr.tray_id:
            for ip in ip_records:
                if ip.instrument_reference == itr.tray_id:
                    matched_ip = ip
                    method = "tray_id_match"
                    score = 0.4
                    reason_key = "tray_id"
                    break

        # Time window match (±3 days)
        if not matched_qs and not matched_ip:
            for qs in qs_records:
                if (
                    itr.event_timestamp
                    and qs.event_timestamp
                    and abs((itr.event_timestamp - qs.event_timestamp).total_seconds()) <= window.total_seconds()
                ):
                    matched_qs = qs
                    method = "time_window"
                    score = 0.3
                    reason_key = "time_window"
                    break

        if matched_qs or matched_ip:
            candidate = PatientImpactCorrelationCandidate(
                tenant_id=tenant_id,
                facility_id=facility_id or itr.facility_id,
                instrument_tracking_record_id=itr.id,
                quality_safety_event_record_id=matched_qs.id if matched_qs else None,
                infection_prevention_event_record_id=matched_ip.id if matched_ip else None,
                instrument_id=itr.instrument_id,
                tray_id=itr.tray_id,
                udi=itr.udi,
                barcode=itr.barcode,
                vendor_id=itr.vendor_id,
                association_score=score,
                confidence_score=score * 0.9,
                association_reason=_ASSOCIATION_REASONS[reason_key],
                recommended_review_action="Quality review recommended — investigate potential association between instrument tracking and reported event",
                human_review_required=True,
                human_review_status="pending",
                correlation_method=method or "time_window",
            )
            db.add(candidate)
            candidates_created += 1

    db.commit()
    return {
        "candidates_created": candidates_created,
        "records_analyzed": records_analyzed,
        "data_source": data_source,
        "disclaimer": DISCLAIMER,
    }


def get_integration_dashboard(db: Session, tenant_id: str, facility_id: str = "") -> dict:
    """Returns integration KPI dashboard. DB-first, seeded mock fallback."""

    since_24h = datetime.utcnow() - timedelta(hours=24)

    q_conn = db.query(ExternalSystemConnection).filter(
        ExternalSystemConnection.tenant_id == tenant_id,
        ExternalSystemConnection.connection_status == "active",
    )
    if facility_id:
        q_conn = q_conn.filter(ExternalSystemConnection.facility_id == facility_id)
    active_connections = q_conn.count()

    failed_imports = db.query(IntegrationImportRun).filter(
        IntegrationImportRun.tenant_id == tenant_id,
        IntegrationImportRun.status == "failed",
        IntegrationImportRun.started_at >= since_24h,
    ).count()

    q_qs = db.query(QualitySafetyEventRecord).filter(QualitySafetyEventRecord.tenant_id == tenant_id)
    if facility_id:
        q_qs = q_qs.filter(QualitySafetyEventRecord.facility_id == facility_id)
    imported_safety_events = q_qs.count()

    spd_count = (
        db.query(InstrumentTrackingRecord).filter(InstrumentTrackingRecord.tenant_id == tenant_id).count()
        + db.query(TrayTrackingRecord).filter(TrayTrackingRecord.tenant_id == tenant_id).count()
        + db.query(SterilizationCycleRecord).filter(SterilizationCycleRecord.tenant_id == tenant_id).count()
    )

    ip_count = db.query(InfectionPreventionEventRecord).filter(
        InfectionPreventionEventRecord.tenant_id == tenant_id
    ).count()

    pending_candidates = db.query(PatientImpactCorrelationCandidate).filter(
        PatientImpactCorrelationCandidate.tenant_id == tenant_id,
        PatientImpactCorrelationCandidate.human_review_status == "pending",
    ).count()

    high_score = db.query(PatientImpactCorrelationCandidate).filter(
        PatientImpactCorrelationCandidate.tenant_id == tenant_id,
        PatientImpactCorrelationCandidate.association_score >= 0.6,
    ).count()

    data_source = "real"
    all_zero = (
        active_connections == 0
        and imported_safety_events == 0
        and spd_count == 0
        and ip_count == 0
    )

    if all_zero:
        data_source = "mock"
        rng = _seed(tenant_id + "dashboard")
        active_connections = rng.randint(2, 8)
        failed_imports = rng.randint(0, 2)
        imported_safety_events = rng.randint(10, 80)
        spd_count = rng.randint(50, 400)
        ip_count = rng.randint(5, 40)
        pending_candidates = rng.randint(1, 10)
        high_score = rng.randint(0, 5)

    return {
        "active_connections": active_connections,
        "failed_imports_last_24h": failed_imports,
        "imported_safety_events": imported_safety_events,
        "imported_spd_records": spd_count,
        "imported_ip_signals": ip_count,
        "correlation_candidates_pending": pending_candidates,
        "potential_harm_signals": high_score,
        "data_source": data_source,
        "disclaimer": DISCLAIMER,
    }
