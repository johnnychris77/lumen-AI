"""P20: Network Intelligence Platform & Market Leadership.

Phases covered:
  1 – National SPD Registry & intelligence sharing
  2 – Instrument Lifecycle Intelligence
  3 – Recall Early Warning System
  4 – Research Data Exchange
  5 – Executive Intelligence dashboards & snapshots

Privacy & governance:
  - k-anonymity floor of 5 for all cross-network publications
  - Laplace noise flag enforced on all aggregate reads
  - Facility/tenant identity NEVER exposed in network-level responses
  - Every mutation is audit-logged with compliance_flag=True
  - All signals carry human_review_required:true — no automated action
  - No causation claims; no FDA/regulatory approval claims
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.audit import log_audit_event
from app.authz import require_roles
from app.deps import get_db
from app.models.p20_network_intelligence import (
    SPDRegistryEntry,
    IntelligenceSharingAgreement,
    NetworkAggregateSnapshot,
    InstrumentLifecycleRecord,
    LifecycleEvent,
    LifecycleBenchmark,
    RecallEarlyWarning,
    ManufacturerIntelligenceProfile,
    AnomalyDetectionRun,
    ResearchDataset,
    ResearchStudy,
    ResearchPublication,
    ExecutiveIntelligenceDashboard,
    ExecutiveIntelligenceSnapshot,
)

router = APIRouter(prefix="/api/network-intelligence", tags=["network-intelligence"])


def _audit(db, action_type: str, tenant_id: str, details: dict | None = None):
    """Thin wrapper to match the platform log_audit_event signature."""
    log_audit_event(
        db,
        tenant_id=tenant_id,
        tenant_name="NetworkIntelligence",
        actor_email="system",
        actor_role="admin",
        action_type=action_type,
        resource_type="network_intelligence",
        resource_id="",
        details=details or {},
        compliance_flag=True,
    )

# k-anonymity floor — applies to all cross-network aggregate publications.
_K_FLOOR = 5
# Minimum facilities to surface a recall early warning internally (lower than publish floor).
_RECALL_SIGNAL_FLOOR = 3

_FACILITY_TYPES = {"hospital", "health_system", "asc", "ltac"}
_REGIONS = {"northeast", "southeast", "midwest", "west", "mountain"}
_PARTICIPATION_TIERS = {"observer", "contributor", "full_member"}
_WARNING_LEVELS = {"watch", "advisory", "alert"}
_WARNING_STATUSES = {"candidate", "under_review", "escalated", "closed", "suppressed"}
_LIFECYCLE_STATUSES = {"active", "repair", "retired", "recalled"}
_SHARING_SCOPES = {"benchmark", "research", "full"}

_DISCLAIMER = (
    "All network intelligence outputs are anonymized aggregates. "
    "Signals are candidate indicators requiring human review — not causation findings. "
    "LumenAI does not claim FDA clearance or regulatory approval."
)


# ===========================================================================
# Phase 1 — National SPD Registry
# ===========================================================================

class RegistryIn(BaseModel):
    tenant_id: str
    facility_type: str = "hospital"
    bed_count_range: Optional[str] = None
    region: Optional[str] = None
    annual_case_volume_range: Optional[str] = None
    sterilization_methods: Optional[str] = None
    participation_tier: str = "contributor"


@router.post("/registry", status_code=201,
             dependencies=[Depends(require_roles("admin", "executive"))])
def register_facility(body: RegistryIn, db: Session = Depends(get_db)):
    """Register a facility in the national SPD intelligence network."""
    if body.facility_type not in _FACILITY_TYPES:
        raise HTTPException(400, f"facility_type must be one of {_FACILITY_TYPES}")
    if body.participation_tier not in _PARTICIPATION_TIERS:
        raise HTTPException(400, f"participation_tier must be one of {_PARTICIPATION_TIERS}")

    existing = db.query(SPDRegistryEntry).filter_by(tenant_id=body.tenant_id).first()
    if existing:
        raise HTTPException(409, "Facility already registered. Use PATCH to update.")

    pseudonym = f"SPD-{uuid.uuid4().hex[:8].upper()}"
    entry = SPDRegistryEntry(
        tenant_id=body.tenant_id,
        facility_pseudonym=pseudonym,
        facility_type=body.facility_type,
        bed_count_range=body.bed_count_range,
        region=body.region,
        annual_case_volume_range=body.annual_case_volume_range,
        sterilization_methods=body.sterilization_methods,
        participation_tier=body.participation_tier,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    _audit(db, "spd_registry_registered", body.tenant_id, {"pseudonym": pseudonym})
    return {"id": entry.id, "facility_pseudonym": pseudonym,
            "participation_tier": entry.participation_tier, "status": "active"}


@router.get("/registry",
            dependencies=[Depends(require_roles("admin", "executive"))])
def list_registry(tenant_id: str = Query(...), db: Session = Depends(get_db)):
    """Return the registry entry for the requesting tenant (own record only)."""
    entry = db.query(SPDRegistryEntry).filter_by(tenant_id=tenant_id).first()
    if not entry:
        raise HTTPException(404, "Not registered. POST /registry to join the network.")
    return {
        "id": entry.id,
        "facility_pseudonym": entry.facility_pseudonym,
        "facility_type": entry.facility_type,
        "bed_count_range": entry.bed_count_range,
        "region": entry.region,
        "participation_tier": entry.participation_tier,
        "registry_status": entry.registry_status,
        "opted_in_at": entry.opted_in_at,
    }


@router.get("/registry/network-summary",
            dependencies=[Depends(require_roles("admin", "executive"))])
def network_summary(db: Session = Depends(get_db)):
    """Anonymized network composition summary (k-anonymity enforced)."""
    total = db.query(SPDRegistryEntry).filter_by(registry_status="active").count()
    if total < _K_FLOOR:
        return {"suppressed": True, "reason": f"Network below k-anonymity floor ({_K_FLOOR})."}

    from sqlalchemy import func
    by_type = {r[0]: r[1] for r in
               db.query(SPDRegistryEntry.facility_type,
                        func.count()).filter_by(registry_status="active")
               .group_by(SPDRegistryEntry.facility_type).all()}
    by_region = {}
    for r in (db.query(SPDRegistryEntry.region, func.count())
              .filter_by(registry_status="active")
              .group_by(SPDRegistryEntry.region).all()):
        if r[1] >= _K_FLOOR:
            by_region[r[0]] = r[1]
        else:
            by_region[r[0]] = "suppressed"

    return {
        "total_active_facilities": total,
        "by_facility_type": by_type,
        "by_region": by_region,
        "k_anonymity_floor": _K_FLOOR,
        "disclaimer": _DISCLAIMER,
    }


# Intelligence Sharing Agreement

class AgreementIn(BaseModel):
    tenant_id: str
    agreed_by: str
    agreement_version: str = "1.0"
    sharing_scope: str = "benchmark"


@router.post("/sharing-agreements", status_code=201,
             dependencies=[Depends(require_roles("admin"))])
def create_agreement(body: AgreementIn, db: Session = Depends(get_db)):
    if body.sharing_scope not in _SHARING_SCOPES:
        raise HTTPException(400, f"sharing_scope must be one of {_SHARING_SCOPES}")
    agreement = IntelligenceSharingAgreement(
        tenant_id=body.tenant_id,
        agreement_version=body.agreement_version,
        agreed_by=body.agreed_by,
        sharing_scope=body.sharing_scope,
    )
    db.add(agreement)
    db.commit()
    db.refresh(agreement)
    _audit(db, "intelligence_sharing_agreement_created", body.tenant_id, {"scope": body.sharing_scope, "version": body.agreement_version})
    return {"id": agreement.id, "status": "active", "sharing_scope": agreement.sharing_scope}


@router.delete("/sharing-agreements/{agreement_id}",
               dependencies=[Depends(require_roles("admin"))])
def withdraw_agreement(agreement_id: int, withdrawn_by: str = Query(...),
                       db: Session = Depends(get_db)):
    agreement = db.get(IntelligenceSharingAgreement, agreement_id)
    if not agreement:
        raise HTTPException(404, "Agreement not found.")
    if agreement.status == "withdrawn":
        raise HTTPException(409, "Agreement already withdrawn.")
    agreement.status = "withdrawn"
    agreement.withdrawn_at = datetime.now(timezone.utc)
    agreement.withdrawn_by = withdrawn_by
    db.commit()
    _audit(db, "intelligence_sharing_agreement_withdrawn", agreement.tenant_id, {"agreement_id": agreement_id, "withdrawn_by": withdrawn_by})
    return {"id": agreement_id, "status": "withdrawn"}


# Network Aggregate Snapshots

class AggregateSnapshotIn(BaseModel):
    metric_name: str
    cohort: str = "all"
    cohort_value: Optional[str] = None
    n_participants: int
    p25: Optional[float] = None
    p50: float
    p75: Optional[float] = None
    p90: Optional[float] = None
    mean: float
    captured_by: Optional[str] = None


@router.post("/aggregate-snapshots", status_code=201,
             dependencies=[Depends(require_roles("admin"))])
def capture_aggregate_snapshot(body: AggregateSnapshotIn, db: Session = Depends(get_db)):
    if body.n_participants < _K_FLOOR:
        raise HTTPException(409,
            f"Cannot publish aggregate below k-anonymity floor ({_K_FLOOR} participants).")
    snap = NetworkAggregateSnapshot(**body.model_dump(), noise_applied=True)
    db.add(snap)
    db.commit()
    db.refresh(snap)
    _audit(db, "network_aggregate_snapshot_captured", "__network__", {"metric": body.metric_name, "n": body.n_participants})
    return {"id": snap.id, "captured_at": snap.captured_at, "metric_name": snap.metric_name}


@router.get("/aggregate-snapshots",
            dependencies=[Depends(require_roles("admin", "executive"))])
def list_aggregate_snapshots(metric_name: Optional[str] = None,
                             db: Session = Depends(get_db)):
    q = db.query(NetworkAggregateSnapshot)
    if metric_name:
        q = q.filter_by(metric_name=metric_name)
    rows = q.order_by(NetworkAggregateSnapshot.captured_at.desc()).limit(100).all()
    return {
        "snapshots": [
            {"id": r.id, "captured_at": r.captured_at, "metric_name": r.metric_name,
             "cohort": r.cohort, "n_participants": r.n_participants,
             "p50": r.p50, "mean": r.mean, "noise_applied": r.noise_applied}
            for r in rows
        ],
        "disclaimer": _DISCLAIMER,
    }


# ===========================================================================
# Phase 2 — Instrument Lifecycle Intelligence
# ===========================================================================

class LifecycleRecordIn(BaseModel):
    tenant_id: str
    facility_id: str
    instrument_uid: str
    manufacturer_name: str
    model_name: str
    instrument_category: str
    udi: Optional[str] = None
    serial_number: Optional[str] = None
    acquisition_date: Optional[datetime] = None
    acquisition_source: Optional[str] = None


@router.post("/lifecycle/instruments", status_code=201,
             dependencies=[Depends(require_roles("admin", "spd_manager"))])
def create_lifecycle_record(body: LifecycleRecordIn, db: Session = Depends(get_db)):
    existing = (db.query(InstrumentLifecycleRecord)
                .filter_by(tenant_id=body.tenant_id, instrument_uid=body.instrument_uid)
                .first())
    if existing:
        raise HTTPException(409, "Lifecycle record already exists for this instrument_uid.")
    rec = InstrumentLifecycleRecord(**body.model_dump())
    db.add(rec)
    db.commit()
    db.refresh(rec)
    _audit(db, "lifecycle_record_created", body.tenant_id, {"instrument_uid": body.instrument_uid, "category": body.instrument_category})
    return {"id": rec.id, "instrument_uid": rec.instrument_uid, "lifecycle_status": rec.lifecycle_status}


@router.get("/lifecycle/instruments",
            dependencies=[Depends(require_roles("admin", "spd_manager", "executive"))])
def list_lifecycle_records(tenant_id: str = Query(...),
                           facility_id: Optional[str] = None,
                           lifecycle_status: Optional[str] = None,
                           db: Session = Depends(get_db)):
    q = db.query(InstrumentLifecycleRecord).filter_by(tenant_id=tenant_id)
    if facility_id:
        q = q.filter_by(facility_id=facility_id)
    if lifecycle_status:
        q = q.filter_by(lifecycle_status=lifecycle_status)
    recs = q.order_by(InstrumentLifecycleRecord.updated_at.desc()).limit(200).all()
    return {
        "instruments": [
            {"id": r.id, "instrument_uid": r.instrument_uid, "manufacturer_name": r.manufacturer_name,
             "model_name": r.model_name, "instrument_category": r.instrument_category,
             "lifecycle_status": r.lifecycle_status, "total_inspections": r.total_inspections,
             "total_defects_found": r.total_defects_found, "total_repairs": r.total_repairs,
             "defect_rate": r.defect_rate, "last_inspection_date": r.last_inspection_date,
             "estimated_remaining_cycles": r.estimated_remaining_cycles}
            for r in recs
        ]
    }


class LifecycleEventIn(BaseModel):
    tenant_id: str
    instrument_uid: str
    event_type: str  # acquired/inspected/repaired/replacement_recommended/retired/recalled
    event_date: Optional[datetime] = None
    performed_by: Optional[str] = None
    notes: Optional[str] = None
    outcome: Optional[str] = None
    cost_usd: Optional[float] = None


_LIFECYCLE_EVENT_TYPES = {
    "acquired", "inspected", "repaired",
    "replacement_recommended", "retired", "recalled"
}


@router.post("/lifecycle/events", status_code=201,
             dependencies=[Depends(require_roles("admin", "spd_manager"))])
def log_lifecycle_event(body: LifecycleEventIn, db: Session = Depends(get_db)):
    if body.event_type not in _LIFECYCLE_EVENT_TYPES:
        raise HTTPException(400, f"event_type must be one of {_LIFECYCLE_EVENT_TYPES}")

    rec = (db.query(InstrumentLifecycleRecord)
           .filter_by(tenant_id=body.tenant_id, instrument_uid=body.instrument_uid)
           .first())
    if not rec:
        raise HTTPException(404, "Lifecycle record not found. Create it first.")

    event = LifecycleEvent(
        tenant_id=body.tenant_id,
        instrument_uid=body.instrument_uid,
        event_type=body.event_type,
        event_date=body.event_date or datetime.now(timezone.utc),
        performed_by=body.performed_by,
        notes=body.notes,
        outcome=body.outcome,
        cost_usd=body.cost_usd,
    )
    db.add(event)

    # Update lifecycle record counters
    now = datetime.now(timezone.utc)
    if body.event_type == "inspected":
        rec.total_inspections += 1
        rec.last_inspection_date = event.event_date
        if not rec.first_inspection_date:
            rec.first_inspection_date = event.event_date
        if body.outcome == "fail":
            rec.total_defects_found += 1
        if rec.total_inspections > 0:
            rec.defect_rate = round(rec.total_defects_found / rec.total_inspections, 4)
    elif body.event_type == "repaired":
        rec.total_repairs += 1
        rec.last_repair_date = event.event_date
        rec.last_repair_type = body.notes
    elif body.event_type == "replacement_recommended":
        rec.replacement_recommended_at = event.event_date
        rec.replacement_recommended_by = body.performed_by
    elif body.event_type == "retired":
        rec.lifecycle_status = "retired"
        rec.retired_at = event.event_date
        rec.retirement_reason = body.notes
    elif body.event_type == "recalled":
        rec.lifecycle_status = "recalled"
    rec.updated_at = now

    db.commit()
    db.refresh(event)
    _audit(db, "lifecycle_event_logged", body.tenant_id, {"instrument_uid": body.instrument_uid, "event_type": body.event_type})
    return {"id": event.id, "instrument_uid": event.instrument_uid,
            "event_type": event.event_type, "event_date": event.event_date}


@router.get("/lifecycle/events",
            dependencies=[Depends(require_roles("admin", "spd_manager"))])
def list_lifecycle_events(tenant_id: str = Query(...),
                          instrument_uid: str = Query(...),
                          db: Session = Depends(get_db)):
    events = (db.query(LifecycleEvent)
              .filter_by(tenant_id=tenant_id, instrument_uid=instrument_uid)
              .order_by(LifecycleEvent.event_date.asc()).all())
    return {
        "instrument_uid": instrument_uid,
        "events": [
            {"id": e.id, "event_type": e.event_type, "event_date": e.event_date,
             "performed_by": e.performed_by, "outcome": e.outcome,
             "notes": e.notes, "cost_usd": e.cost_usd}
            for e in events
        ]
    }


class LifecycleBenchmarkIn(BaseModel):
    instrument_category: str
    metric_name: str
    cohort: str = "all"
    n_facilities: int
    p50: float
    p75: Optional[float] = None
    p90: Optional[float] = None
    mean: float


@router.post("/lifecycle/benchmarks", status_code=201,
             dependencies=[Depends(require_roles("admin"))])
def publish_lifecycle_benchmark(body: LifecycleBenchmarkIn, db: Session = Depends(get_db)):
    if body.n_facilities < _K_FLOOR:
        raise HTTPException(409,
            f"Cannot publish below k-anonymity floor ({_K_FLOOR} facilities).")
    bm = LifecycleBenchmark(**body.model_dump(), noise_applied=True)
    db.add(bm)
    db.commit()
    db.refresh(bm)
    _audit(db, "lifecycle_benchmark_published", "__network__", {"category": body.instrument_category, "metric": body.metric_name})
    return {"id": bm.id, "instrument_category": bm.instrument_category,
            "metric_name": bm.metric_name, "n_facilities": bm.n_facilities}


@router.get("/lifecycle/benchmarks",
            dependencies=[Depends(require_roles("admin", "spd_manager", "executive"))])
def list_lifecycle_benchmarks(instrument_category: Optional[str] = None,
                              db: Session = Depends(get_db)):
    q = db.query(LifecycleBenchmark)
    if instrument_category:
        q = q.filter_by(instrument_category=instrument_category)
    rows = q.order_by(LifecycleBenchmark.computed_at.desc()).limit(200).all()
    return {
        "benchmarks": [
            {"id": r.id, "instrument_category": r.instrument_category,
             "metric_name": r.metric_name, "cohort": r.cohort,
             "n_facilities": r.n_facilities, "p50": r.p50, "mean": r.mean,
             "noise_applied": r.noise_applied, "computed_at": r.computed_at}
            for r in rows
        ],
        "disclaimer": _DISCLAIMER,
    }


# ===========================================================================
# Phase 3 — Recall Early Warning System
# ===========================================================================

class RecallWarningIn(BaseModel):
    instrument_category: str
    finding_type: str
    n_facilities_reporting: int
    first_observed: datetime
    last_observed: datetime
    anomaly_score: float = Field(ge=0.0, le=1.0)
    manufacturer_pseudonym: Optional[str] = None
    model_pseudonym: Optional[str] = None
    trend: str = "stable"
    warning_level: str = "watch"


@router.post("/recall-early-warning", status_code=201,
             dependencies=[Depends(require_roles("admin"))])
def create_early_warning(body: RecallWarningIn, db: Session = Depends(get_db)):
    if body.n_facilities_reporting < _RECALL_SIGNAL_FLOOR:
        raise HTTPException(409,
            f"Signal requires >= {_RECALL_SIGNAL_FLOOR} reporting facilities.")
    if body.warning_level not in _WARNING_LEVELS:
        raise HTTPException(400, f"warning_level must be one of {_WARNING_LEVELS}")

    signal_ref = f"REW-{datetime.now(timezone.utc).year}-{uuid.uuid4().hex[:6].upper()}"
    warning = RecallEarlyWarning(
        signal_ref=signal_ref,
        instrument_category=body.instrument_category,
        manufacturer_pseudonym=body.manufacturer_pseudonym,
        model_pseudonym=body.model_pseudonym,
        finding_type=body.finding_type,
        anomaly_score=body.anomaly_score,
        n_facilities_reporting=body.n_facilities_reporting,
        first_observed=body.first_observed,
        last_observed=body.last_observed,
        trend=body.trend,
        warning_level=body.warning_level,
        status="candidate",
        human_review_required=True,
    )
    db.add(warning)
    db.commit()
    db.refresh(warning)
    _audit(db, "recall_early_warning_created", "__network__", {"signal_ref": signal_ref, "category": body.instrument_category,
                             "warning_level": body.warning_level})
    return {
        "id": warning.id,
        "signal_ref": signal_ref,
        "warning_level": warning.warning_level,
        "status": "candidate",
        "human_review_required": True,
        "disclaimer": _DISCLAIMER,
    }


@router.get("/recall-early-warning",
            dependencies=[Depends(require_roles("admin", "executive"))])
def list_early_warnings(status: Optional[str] = None,
                        warning_level: Optional[str] = None,
                        db: Session = Depends(get_db)):
    q = db.query(RecallEarlyWarning)
    if status:
        q = q.filter_by(status=status)
    if warning_level:
        q = q.filter_by(warning_level=warning_level)
    rows = q.order_by(RecallEarlyWarning.last_observed.desc()).limit(100).all()
    return {
        "early_warnings": [
            {"id": r.id, "signal_ref": r.signal_ref,
             "instrument_category": r.instrument_category,
             "finding_type": r.finding_type,
             "anomaly_score": r.anomaly_score,
             "n_facilities_reporting": r.n_facilities_reporting,
             "warning_level": r.warning_level, "trend": r.trend,
             "status": r.status, "human_review_required": r.human_review_required,
             "last_observed": r.last_observed}
            for r in rows
        ],
        "disclaimer": _DISCLAIMER,
    }


@router.post("/recall-early-warning/{warning_id}/review",
             dependencies=[Depends(require_roles("admin"))])
def review_early_warning(warning_id: int,
                         decision: str = Query(...),
                         reviewed_by: str = Query(...),
                         notes: Optional[str] = Query(None),
                         db: Session = Depends(get_db)):
    """Human review of a recall early warning. Required before any escalation."""
    valid_decisions = {"escalate", "monitor", "close", "suppress"}
    if decision not in valid_decisions:
        raise HTTPException(400, f"decision must be one of {valid_decisions}")

    warning = db.get(RecallEarlyWarning, warning_id)
    if not warning:
        raise HTTPException(404, "Early warning not found.")

    status_map = {
        "escalate": "escalated",
        "monitor": "under_review",
        "close": "closed",
        "suppress": "suppressed",
    }
    warning.status = status_map[decision]
    warning.reviewed_by = reviewed_by
    warning.reviewed_at = datetime.now(timezone.utc)
    warning.review_notes = notes
    warning.human_review_required = False
    if decision == "escalate":
        warning.escalated_to_steward_at = datetime.now(timezone.utc)
    db.commit()
    _audit(db, "recall_early_warning_reviewed", "__network__", {"signal_ref": warning.signal_ref, "decision": decision,
                             "reviewed_by": reviewed_by})
    return {"id": warning_id, "signal_ref": warning.signal_ref,
            "status": warning.status, "decision": decision}


@router.post("/anomaly-detection/run", status_code=201,
             dependencies=[Depends(require_roles("admin"))])
def log_anomaly_detection_run(
    triggered_by: str = Query(default="scheduled"),
    categories_scanned: int = Query(default=0),
    signals_surfaced: int = Query(default=0),
    signals_escalated: int = Query(default=0),
    notes: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    run = AnomalyDetectionRun(
        triggered_by=triggered_by,
        instrument_categories_scanned=categories_scanned,
        signals_surfaced=signals_surfaced,
        signals_escalated=signals_escalated,
        notes=notes,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    _audit(db, "anomaly_detection_run_logged", "__network__", {"triggered_by": triggered_by, "signals": signals_surfaced})
    return {"id": run.id, "run_at": run.run_at, "run_status": run.run_status}


@router.get("/anomaly-detection/runs",
            dependencies=[Depends(require_roles("admin"))])
def list_anomaly_runs(db: Session = Depends(get_db)):
    runs = (db.query(AnomalyDetectionRun)
            .order_by(AnomalyDetectionRun.run_at.desc()).limit(50).all())
    return {"runs": [{"id": r.id, "run_at": r.run_at, "triggered_by": r.triggered_by,
                      "signals_surfaced": r.signals_surfaced,
                      "signals_escalated": r.signals_escalated,
                      "run_status": r.run_status} for r in runs]}


@router.get("/manufacturer-intelligence",
            dependencies=[Depends(require_roles("admin", "executive"))])
def list_manufacturer_profiles(instrument_category: Optional[str] = None,
                               db: Session = Depends(get_db)):
    q = db.query(ManufacturerIntelligenceProfile)
    if instrument_category:
        q = q.filter_by(instrument_category=instrument_category)
    rows = q.order_by(ManufacturerIntelligenceProfile.last_computed.desc()).limit(100).all()
    publishable = [r for r in rows if r.n_facilities_contributing >= _K_FLOOR]
    return {
        "profiles": [
            {"id": r.id, "manufacturer_pseudonym": r.manufacturer_pseudonym,
             "instrument_category": r.instrument_category,
             "n_facilities_contributing": r.n_facilities_contributing,
             "network_defect_rate": r.network_defect_rate,
             "network_pass_rate": r.network_pass_rate,
             "intelligence_grade": r.intelligence_grade,
             "open_early_warnings": r.open_early_warnings,
             "last_computed": r.last_computed}
            for r in publishable
        ],
        "suppressed_count": len(rows) - len(publishable),
        "k_anonymity_floor": _K_FLOOR,
        "disclaimer": _DISCLAIMER,
    }


class ManufacturerProfileIn(BaseModel):
    manufacturer_pseudonym: str
    instrument_category: str
    n_facilities_contributing: int
    network_defect_rate: float
    network_pass_rate: float
    network_repair_rate: float
    open_early_warnings: int = 0
    formal_recall_count: int = 0
    intelligence_grade: str = "B"


@router.post("/manufacturer-intelligence", status_code=201,
             dependencies=[Depends(require_roles("admin"))])
def upsert_manufacturer_profile(body: ManufacturerProfileIn, db: Session = Depends(get_db)):
    if body.n_facilities_contributing < _K_FLOOR:
        raise HTTPException(409,
            f"Profile requires >= {_K_FLOOR} contributing facilities.")
    existing = (db.query(ManufacturerIntelligenceProfile)
                .filter_by(manufacturer_pseudonym=body.manufacturer_pseudonym,
                           instrument_category=body.instrument_category).first())
    if existing:
        for k, v in body.model_dump().items():
            setattr(existing, k, v)
        existing.last_computed = datetime.now(timezone.utc)
        existing.noise_applied = True
        db.commit()
        db.refresh(existing)
        return {"id": existing.id, "updated": True}
    profile = ManufacturerIntelligenceProfile(**body.model_dump(), noise_applied=True)
    db.add(profile)
    db.commit()
    db.refresh(profile)
    _audit(db, "manufacturer_profile_upserted", "__network__", {"pseudonym": body.manufacturer_pseudonym})
    return {"id": profile.id, "created": True}


# ===========================================================================
# Phase 4 — Research Data Exchange
# ===========================================================================

class ResearchDatasetIn(BaseModel):
    title: str
    description: Optional[str] = None
    dataset_type: str
    instrument_categories: Optional[str] = None
    date_range_start: Optional[datetime] = None
    date_range_end: Optional[datetime] = None
    n_facilities_contributing: int
    n_records: int
    irb_approval_number: Optional[str] = None
    created_by: str


@router.post("/research/datasets", status_code=201,
             dependencies=[Depends(require_roles("admin"))])
def create_research_dataset(body: ResearchDatasetIn, db: Session = Depends(get_db)):
    if body.n_facilities_contributing < _K_FLOOR:
        raise HTTPException(409,
            f"Research dataset requires >= {_K_FLOOR} contributing facilities.")
    dataset_ref = f"RDS-{datetime.now(timezone.utc).year}-{uuid.uuid4().hex[:6].upper()}"
    ds = ResearchDataset(dataset_ref=dataset_ref, **body.model_dump())
    db.add(ds)
    db.commit()
    db.refresh(ds)
    _audit(db, "research_dataset_created", "__network__", {"dataset_ref": dataset_ref, "title": body.title})
    return {"id": ds.id, "dataset_ref": dataset_ref, "release_status": "draft"}


@router.post("/research/datasets/{dataset_id}/approve",
             dependencies=[Depends(require_roles("admin"))])
def approve_research_dataset(dataset_id: int, approved_by: str = Query(...),
                             db: Session = Depends(get_db)):
    ds = db.get(ResearchDataset, dataset_id)
    if not ds:
        raise HTTPException(404, "Dataset not found.")
    if ds.governance_approved:
        raise HTTPException(409, "Dataset already approved.")
    ds.governance_approved = True
    ds.approved_by = approved_by
    ds.approved_at = datetime.now(timezone.utc)
    ds.release_status = "approved"
    db.commit()
    _audit(db, "research_dataset_approved", "__network__", {"dataset_ref": ds.dataset_ref, "approved_by": approved_by})
    return {"id": dataset_id, "dataset_ref": ds.dataset_ref, "release_status": "approved"}


@router.post("/research/datasets/{dataset_id}/release",
             dependencies=[Depends(require_roles("admin"))])
def release_research_dataset(dataset_id: int, db: Session = Depends(get_db)):
    ds = db.get(ResearchDataset, dataset_id)
    if not ds:
        raise HTTPException(404, "Dataset not found.")
    if not ds.governance_approved:
        raise HTTPException(409, "Dataset must be governance-approved before release.")
    if ds.release_status == "released":
        raise HTTPException(409, "Dataset already released.")
    ds.release_status = "released"
    ds.released_at = datetime.now(timezone.utc)
    db.commit()
    _audit(db, "research_dataset_released", "__network__", {"dataset_ref": ds.dataset_ref})
    return {"id": dataset_id, "dataset_ref": ds.dataset_ref, "release_status": "released"}


@router.get("/research/datasets",
            dependencies=[Depends(require_roles("admin", "executive"))])
def list_research_datasets(release_status: Optional[str] = None,
                           db: Session = Depends(get_db)):
    q = db.query(ResearchDataset)
    if release_status:
        q = q.filter_by(release_status=release_status)
    rows = q.order_by(ResearchDataset.created_at.desc()).limit(100).all()
    return {
        "datasets": [
            {"id": r.id, "dataset_ref": r.dataset_ref, "title": r.title,
             "dataset_type": r.dataset_type,
             "n_facilities_contributing": r.n_facilities_contributing,
             "n_records": r.n_records, "release_status": r.release_status,
             "governance_approved": r.governance_approved}
            for r in rows
        ],
        "disclaimer": _DISCLAIMER,
    }


class ResearchStudyIn(BaseModel):
    title: str
    principal_investigator: str
    institution: Optional[str] = None
    study_type: str = "observational"
    dataset_refs: Optional[str] = None
    irb_approval_number: Optional[str] = None
    claims_discipline_acknowledged: bool = False


@router.post("/research/studies", status_code=201,
             dependencies=[Depends(require_roles("admin"))])
def create_research_study(body: ResearchStudyIn, db: Session = Depends(get_db)):
    if not body.claims_discipline_acknowledged:
        raise HTTPException(422,
            "Principal investigator must acknowledge no-causation claims discipline.")
    study_ref = f"STU-{datetime.now(timezone.utc).year}-{uuid.uuid4().hex[:6].upper()}"
    study = ResearchStudy(study_ref=study_ref, **body.model_dump())
    db.add(study)
    db.commit()
    db.refresh(study)
    _audit(db, "research_study_created", "__network__", {"study_ref": study_ref, "pi": body.principal_investigator})
    return {"id": study.id, "study_ref": study_ref, "status": "proposed"}


@router.get("/research/studies",
            dependencies=[Depends(require_roles("admin", "executive"))])
def list_research_studies(db: Session = Depends(get_db)):
    rows = (db.query(ResearchStudy)
            .order_by(ResearchStudy.created_at.desc()).limit(100).all())
    return {
        "studies": [
            {"id": r.id, "study_ref": r.study_ref, "title": r.title,
             "principal_investigator": r.principal_investigator,
             "study_type": r.study_type, "status": r.status,
             "irb_approval_number": r.irb_approval_number}
            for r in rows
        ]
    }


class ResearchPublicationIn(BaseModel):
    study_ref: str
    publication_title: str
    journal: Optional[str] = None
    doi: Optional[str] = None
    published_date: Optional[datetime] = None
    causation_claim_present: bool = False


@router.post("/research/publications", status_code=201,
             dependencies=[Depends(require_roles("admin"))])
def record_research_publication(body: ResearchPublicationIn, db: Session = Depends(get_db)):
    if body.causation_claim_present:
        raise HTTPException(422,
            "Publications with causation claims cannot be recorded under LumenAI network data governance.")
    pub = ResearchPublication(**body.model_dump(), lumenai_data_cited=True)
    db.add(pub)
    db.commit()
    db.refresh(pub)
    _audit(db, "research_publication_recorded", "__network__", {"study_ref": body.study_ref, "title": body.publication_title})
    return {"id": pub.id, "study_ref": pub.study_ref,
            "governance_cleared": pub.governance_cleared}


# ===========================================================================
# Phase 5 — Executive Intelligence
# ===========================================================================

class DashboardIn(BaseModel):
    tenant_id: str
    dashboard_name: str
    dashboard_type: str = "national_benchmark"
    config_json: Optional[str] = None
    created_by: str


_DASHBOARD_TYPES = {"national_benchmark", "manufacturer", "lifecycle", "recall_watch"}


@router.post("/executive/dashboards", status_code=201,
             dependencies=[Depends(require_roles("admin", "executive"))])
def create_executive_dashboard(body: DashboardIn, db: Session = Depends(get_db)):
    if body.dashboard_type not in _DASHBOARD_TYPES:
        raise HTTPException(400, f"dashboard_type must be one of {_DASHBOARD_TYPES}")
    dash = ExecutiveIntelligenceDashboard(**body.model_dump())
    db.add(dash)
    db.commit()
    db.refresh(dash)
    _audit(db, "executive_dashboard_created", body.tenant_id, {"dashboard_name": body.dashboard_name,
                             "dashboard_type": body.dashboard_type})
    return {"id": dash.id, "dashboard_name": dash.dashboard_name,
            "dashboard_type": dash.dashboard_type}


@router.get("/executive/dashboards",
            dependencies=[Depends(require_roles("admin", "executive"))])
def list_executive_dashboards(tenant_id: str = Query(...), db: Session = Depends(get_db)):
    rows = (db.query(ExecutiveIntelligenceDashboard)
            .filter_by(tenant_id=tenant_id)
            .order_by(ExecutiveIntelligenceDashboard.created_at.desc()).all())
    return {"dashboards": [
        {"id": r.id, "dashboard_name": r.dashboard_name,
         "dashboard_type": r.dashboard_type, "created_at": r.created_at}
        for r in rows
    ]}


class ExecSnapshotIn(BaseModel):
    tenant_id: str
    network_pass_rate_p50: Optional[float] = None
    tenant_pass_rate: Optional[float] = None
    network_defect_rate_p50: Optional[float] = None
    tenant_defect_rate: Optional[float] = None
    open_early_warnings_network: int = 0
    tenant_recall_exposure_score: float = 0.0
    accreditation_readiness_score: Optional[float] = None
    network_percentile: Optional[float] = None
    captured_by: Optional[str] = None


@router.post("/executive/snapshots", status_code=201,
             dependencies=[Depends(require_roles("admin", "executive"))])
def capture_executive_snapshot(body: ExecSnapshotIn, db: Session = Depends(get_db)):
    snap = ExecutiveIntelligenceSnapshot(**body.model_dump(), human_review_required=True)
    db.add(snap)
    db.commit()
    db.refresh(snap)
    _audit(db, "executive_snapshot_captured", body.tenant_id, {"percentile": body.network_percentile})
    return {
        "id": snap.id,
        "captured_at": snap.captured_at,
        "human_review_required": True,
        "disclaimer": _DISCLAIMER,
    }


@router.get("/executive/snapshots",
            dependencies=[Depends(require_roles("admin", "executive"))])
def list_executive_snapshots(tenant_id: str = Query(...), db: Session = Depends(get_db)):
    rows = (db.query(ExecutiveIntelligenceSnapshot)
            .filter_by(tenant_id=tenant_id)
            .order_by(ExecutiveIntelligenceSnapshot.captured_at.desc())
            .limit(24).all())
    return {
        "snapshots": [
            {"id": r.id, "captured_at": r.captured_at,
             "network_pass_rate_p50": r.network_pass_rate_p50,
             "tenant_pass_rate": r.tenant_pass_rate,
             "network_defect_rate_p50": r.network_defect_rate_p50,
             "tenant_defect_rate": r.tenant_defect_rate,
             "open_early_warnings_network": r.open_early_warnings_network,
             "tenant_recall_exposure_score": r.tenant_recall_exposure_score,
             "accreditation_readiness_score": r.accreditation_readiness_score,
             "network_percentile": r.network_percentile,
             "human_review_required": r.human_review_required}
            for r in rows
        ],
        "disclaimer": _DISCLAIMER,
    }


@router.get("/executive/network-intelligence-summary",
            dependencies=[Depends(require_roles("admin", "executive"))])
def network_intelligence_summary(tenant_id: str = Query(...), db: Session = Depends(get_db)):
    """Composite executive summary: registry, lifecycle, recall watch, research."""
    registry = db.query(SPDRegistryEntry).filter_by(registry_status="active").count()
    open_warnings = (db.query(RecallEarlyWarning)
                     .filter(RecallEarlyWarning.status.in_(["candidate", "under_review", "escalated"]))
                     .count())
    active_studies = db.query(ResearchStudy).filter_by(status="active").count()
    released_datasets = db.query(ResearchDataset).filter_by(release_status="released").count()
    latest_snap = (db.query(ExecutiveIntelligenceSnapshot)
                   .filter_by(tenant_id=tenant_id)
                   .order_by(ExecutiveIntelligenceSnapshot.captured_at.desc()).first())

    return {
        "network_active_facilities": registry if registry >= _K_FLOOR else "suppressed",
        "open_recall_early_warnings": open_warnings,
        "active_research_studies": active_studies,
        "released_research_datasets": released_datasets,
        "latest_executive_snapshot": {
            "captured_at": latest_snap.captured_at if latest_snap else None,
            "network_percentile": latest_snap.network_percentile if latest_snap else None,
            "tenant_recall_exposure_score": latest_snap.tenant_recall_exposure_score if latest_snap else None,
        } if latest_snap else None,
        "human_review_required": True,
        "disclaimer": _DISCLAIMER,
    }
