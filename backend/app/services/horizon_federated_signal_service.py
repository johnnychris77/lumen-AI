"""v3.4 — Project Horizon, Section 4: Federated Learning Signals.

Aggregates real per-tenant data into the six signal categories P23 GSIN's
instrument-centric schema doesn't compute (finding frequency, anatomy
trend, instrument failure pattern, coverage effectiveness, supervisor
agreement, educational effectiveness) — using GSIN's own k-anonymity gate
and differential-privacy noise (`GLOBAL_K_THRESHOLD`/`EARLY_WARNING_K`/
`_apply_laplace_noise` imported from `global_aggregation_job.py`, never
redefined). Only organizations with an active federated sharing
agreement (`horizon_participation_service.list_enrolled_tenant_ids`)
contribute — opt-in governance enforced as an actual data-scope filter,
not just a checkbox.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.federated_horizon import FEDERATED_SIGNAL_CATEGORIES, FederatedLearningSignal
from app.models.inspection import Inspection
from app.models.inspection_finding import InspectionFinding
from app.models.supervisor_review import SupervisorReview
from app.services import horizon_participation_service
from app.services.global_aggregation_job import EARLY_WARNING_K, GLOBAL_K_THRESHOLD, _apply_laplace_noise

_LOOKBACK_DAYS = 90
_FAILURE_DISPOSITIONS = ("REMOVE FROM SERVICE", "REPROCESS")


def _row_to_dict(obj) -> dict:
    result: dict = {}
    for col in obj.__table__.columns:
        val = getattr(obj, col.name)
        if hasattr(val, "isoformat"):
            val = val.isoformat()
        result[col.name] = val
    return result


def _enrolled_tenants(db: Session) -> list[str]:
    return horizon_participation_service.list_enrolled_tenant_ids(db)


def _finding_frequency(db: Session, tenant_ids: list[str], finding_type: str, since: datetime) -> tuple[int, int]:
    rows = (
        db.query(InspectionFinding.tenant_id, InspectionFinding.id)
        .filter(InspectionFinding.tenant_id.in_(tenant_ids), InspectionFinding.finding_type == finding_type, InspectionFinding.created_at >= since)
        .all()
    )
    return len(rows), len({r[0] for r in rows})


def _anatomy_trend(db: Session, tenant_ids: list[str], zone: str, since: datetime) -> tuple[int, int]:
    rows = (
        db.query(InspectionFinding.tenant_id, InspectionFinding.id)
        .filter(InspectionFinding.tenant_id.in_(tenant_ids), InspectionFinding.zone == zone, InspectionFinding.created_at >= since)
        .all()
    )
    return len(rows), len({r[0] for r in rows})


def _instrument_failure_pattern(db: Session, tenant_ids: list[str], instrument_type: str, since: datetime) -> tuple[float | None, int]:
    rows = (
        db.query(Inspection.tenant_id, Inspection.disposition)
        .filter(Inspection.tenant_id.in_(tenant_ids), Inspection.instrument_type == instrument_type, Inspection.created_at >= since)
        .all()
    )
    if not rows:
        return None, 0
    failures = sum(1 for _, disposition in rows if disposition in _FAILURE_DISPOSITIONS)
    return round(failures / len(rows), 4), len({r[0] for r in rows})


def _coverage_effectiveness(db: Session, tenant_ids: list[str], instrument_type: str, since: datetime) -> tuple[float | None, int]:
    rows = (
        db.query(Inspection.tenant_id, Inspection.coverage_pct)
        .filter(
            Inspection.tenant_id.in_(tenant_ids), Inspection.instrument_type == instrument_type,
            Inspection.created_at >= since, Inspection.coverage_pct.isnot(None),
        )
        .all()
    )
    if not rows:
        return None, 0
    return round(sum(r[1] for r in rows) / len(rows), 2), len({r[0] for r in rows})


def _supervisor_agreement(db: Session, tenant_ids: list[str], since: datetime) -> tuple[float | None, int]:
    rows = (
        db.query(SupervisorReview.tenant_id, SupervisorReview.agreement)
        .filter(SupervisorReview.tenant_id.in_(tenant_ids), SupervisorReview.created_at >= since)
        .all()
    )
    if not rows:
        return None, 0
    agree = sum(1 for _, agreement in rows if agreement == "agree")
    return round(agree / len(rows), 4), len({r[0] for r in rows})


def _educational_effectiveness(db: Session, tenant_ids: list[str]) -> tuple[float | None, int]:
    from app.services.competency_service import technician_quality_dashboard

    tenant_averages = []
    for tenant_id in tenant_ids:
        dashboard = technician_quality_dashboard(db, tenant_id)
        progress_values = [t["training_progress_pct"] for t in dashboard.get("technicians", []) if t.get("training_progress_pct") is not None]
        if progress_values:
            tenant_averages.append(sum(progress_values) / len(progress_values))
    if not tenant_averages:
        return None, 0
    return round(sum(tenant_averages) / len(tenant_averages), 2), len(tenant_averages)


def compute_federated_signal(db: Session, *, signal_category: str, scope_key: str) -> dict:
    if signal_category not in FEDERATED_SIGNAL_CATEGORIES:
        raise ValueError(f"signal_category must be one of {FEDERATED_SIGNAL_CATEGORIES}")

    since = datetime.now(timezone.utc) - timedelta(days=_LOOKBACK_DAYS)
    tenant_ids = _enrolled_tenants(db)

    if signal_category == "finding_frequency":
        count, tenant_count = _finding_frequency(db, tenant_ids, scope_key, since)
        value = float(count)
    elif signal_category == "anatomy_trend":
        count, tenant_count = _anatomy_trend(db, tenant_ids, scope_key, since)
        value = float(count)
    elif signal_category == "instrument_failure_pattern":
        value, tenant_count = _instrument_failure_pattern(db, tenant_ids, scope_key, since)
    elif signal_category == "coverage_effectiveness":
        value, tenant_count = _coverage_effectiveness(db, tenant_ids, scope_key, since)
    elif signal_category == "supervisor_agreement":
        value, tenant_count = _supervisor_agreement(db, tenant_ids, since)
    else:  # educational_effectiveness
        value, tenant_count = _educational_effectiveness(db, tenant_ids)

    k_anonymity_verified = tenant_count >= GLOBAL_K_THRESHOLD
    published = tenant_count >= GLOBAL_K_THRESHOLD
    published_value = round(_apply_laplace_noise(value), 4) if (published and value is not None) else None

    row = FederatedLearningSignal(
        signal_category=signal_category, scope_key=scope_key, tenant_count=tenant_count,
        value=published_value, k_anonymity_verified=k_anonymity_verified, published=published,
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    result = _row_to_dict(row)
    result["k_threshold"] = GLOBAL_K_THRESHOLD
    result["early_warning_k"] = EARLY_WARNING_K
    result["raw_value_suppressed"] = not published
    return result


def generate_all_federated_signals(db: Session) -> list[dict]:
    """Iterates a representative scope per category from what's actually
    present in the enrolled tenants' data — never a hardcoded list that
    might not exist."""
    tenant_ids = _enrolled_tenants(db)
    if not tenant_ids:
        return []

    since = datetime.now(timezone.utc) - timedelta(days=_LOOKBACK_DAYS)
    finding_types = [
        r[0] for r in db.query(InspectionFinding.finding_type).filter(InspectionFinding.tenant_id.in_(tenant_ids), InspectionFinding.created_at >= since).distinct().limit(5).all()
    ]
    zones = [
        r[0] for r in db.query(InspectionFinding.zone).filter(InspectionFinding.tenant_id.in_(tenant_ids), InspectionFinding.created_at >= since, InspectionFinding.zone != "").distinct().limit(5).all()
    ]
    instrument_types = [
        r[0] for r in db.query(Inspection.instrument_type).filter(Inspection.tenant_id.in_(tenant_ids), Inspection.created_at >= since).distinct().limit(5).all()
    ]

    results = []
    for ft in finding_types:
        results.append(compute_federated_signal(db, signal_category="finding_frequency", scope_key=ft))
    for zone in zones:
        results.append(compute_federated_signal(db, signal_category="anatomy_trend", scope_key=zone))
    for it in instrument_types:
        results.append(compute_federated_signal(db, signal_category="instrument_failure_pattern", scope_key=it))
        results.append(compute_federated_signal(db, signal_category="coverage_effectiveness", scope_key=it))
    results.append(compute_federated_signal(db, signal_category="supervisor_agreement", scope_key="all"))
    results.append(compute_federated_signal(db, signal_category="educational_effectiveness", scope_key="all"))
    return results


def list_federated_signals(db: Session, *, signal_category: str = "", published_only: bool = True) -> list[dict]:
    q = db.query(FederatedLearningSignal)
    if signal_category:
        q = q.filter(FederatedLearningSignal.signal_category == signal_category)
    if published_only:
        q = q.filter(FederatedLearningSignal.published.is_(True))
    rows = q.order_by(FederatedLearningSignal.id.desc()).limit(100).all()
    return [_row_to_dict(r) for r in rows]
