"""P10: Digital Twin of SPD Operations — Engine."""
from __future__ import annotations

import hashlib
import json
import random
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.models.digital_twin import (
    InstrumentFlowRecord,
    SPDAlert,
    SPDWorkflowStation,
    WhatIfScenario,
)
from app.schemas.digital_twin import (
    InstrumentFlowResult,
    SPDAlertResult,
    StationStatus,
    TwinDashboard,
    TwinStateResult,
    WhatIfRequest,
    WhatIfResult,
)

DEFAULT_STATIONS = [
    {"station_name": "Decontamination Bay 1", "station_type": "decontamination", "capacity": 20, "avg_processing_time_minutes": 45.0},
    {"station_name": "Decontamination Bay 2", "station_type": "decontamination", "capacity": 20, "avg_processing_time_minutes": 45.0},
    {"station_name": "Inspection Station A",  "station_type": "inspection",       "capacity": 10, "avg_processing_time_minutes": 15.0},
    {"station_name": "Inspection Station B",  "station_type": "inspection",       "capacity": 10, "avg_processing_time_minutes": 15.0},
    {"station_name": "Sterilizer 1",          "station_type": "sterilization",    "capacity": 30, "avg_processing_time_minutes": 60.0},
    {"station_name": "Sterilizer 2",          "station_type": "sterilization",    "capacity": 30, "avg_processing_time_minutes": 60.0},
    {"station_name": "Sterile Storage",       "station_type": "storage",          "capacity": 200, "avg_processing_time_minutes": 0.0},
    {"station_name": "Dispatch",              "station_type": "dispatch",         "capacity": 50, "avg_processing_time_minutes": 5.0},
]

# Utilization ranges by station type for mock
MOCK_UTILIZATION_RANGES = {
    "decontamination": (0.60, 0.80),
    "inspection": (0.40, 0.70),
    "sterilization": (0.50, 0.85),
    "storage": (0.20, 0.40),
    "dispatch": (0.10, 0.30),
}


def _seed(s: str) -> random.Random:
    seed = hashlib.md5(s.encode()).hexdigest()[:8]
    return random.Random(int(seed, 16))


def _dt_str(dt: Optional[datetime]) -> Optional[str]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


def _station_to_status(station: SPDWorkflowStation) -> StationStatus:
    cap = station.capacity or 1
    util = round((station.current_load / cap) * 100, 1)
    return StationStatus(
        id=station.id,
        tenant_id=station.tenant_id,
        facility_id=station.facility_id or "",
        station_name=station.station_name,
        station_type=station.station_type,
        capacity=station.capacity,
        current_load=station.current_load,
        avg_processing_time_minutes=station.avg_processing_time_minutes,
        status=station.status,
        utilization_pct=util,
        last_updated=_dt_str(station.last_updated) or "",
    )


def _flow_to_result(flow: InstrumentFlowRecord) -> InstrumentFlowResult:
    return InstrumentFlowResult(
        id=flow.id,
        tenant_id=flow.tenant_id,
        instrument_name=flow.instrument_name,
        instrument_id=flow.instrument_id or "",
        from_station=flow.from_station or "",
        to_station=flow.to_station,
        station_type=flow.station_type,
        arrived_at=_dt_str(flow.arrived_at) or "",
        departed_at=_dt_str(flow.departed_at),
        processing_time_minutes=flow.processing_time_minutes,
        outcome=flow.outcome,
        notes=flow.notes or "",
    )


def _alert_to_result(alert: SPDAlert) -> SPDAlertResult:
    return SPDAlertResult(
        id=alert.id,
        tenant_id=alert.tenant_id,
        facility_id=alert.facility_id or "",
        alert_type=alert.alert_type,
        severity=alert.severity,
        station_name=alert.station_name or "",
        message=alert.message,
        metric_value=alert.metric_value,
        threshold_value=alert.threshold_value,
        acknowledged=alert.acknowledged,
        acknowledged_by=alert.acknowledged_by or "",
        created_at=_dt_str(alert.created_at) or "",
        resolved_at=_dt_str(alert.resolved_at),
    )


def _ensure_stations(tenant_id: str, facility_id: str, db: Session) -> list[SPDWorkflowStation]:
    """Seed default stations if none exist for tenant."""
    stations = db.query(SPDWorkflowStation).filter_by(tenant_id=tenant_id).all()
    if not stations:
        now = datetime.now(timezone.utc)
        rng = _seed(f"stations:{tenant_id}:{facility_id}")
        for s in DEFAULT_STATIONS:
            cap = s["capacity"]
            stype = s["station_type"]
            lo, hi = MOCK_UTILIZATION_RANGES.get(stype, (0.3, 0.6))
            load = int(rng.uniform(lo, hi) * cap)
            station = SPDWorkflowStation(
                tenant_id=tenant_id,
                facility_id=facility_id,
                station_name=s["station_name"],
                station_type=stype,
                capacity=cap,
                current_load=load,
                avg_processing_time_minutes=s["avg_processing_time_minutes"],
                status="active",
                last_updated=now,
            )
            db.add(station)
        db.commit()
        stations = db.query(SPDWorkflowStation).filter_by(tenant_id=tenant_id).all()
    return stations


def get_twin_state(tenant_id: str, facility_id: str, db: Session) -> TwinStateResult:
    """Compute the current digital twin state."""
    try:
        stations = _ensure_stations(tenant_id, facility_id, db)

        # In-flight count
        in_flight = db.query(InstrumentFlowRecord).filter_by(
            tenant_id=tenant_id, outcome="pending"
        ).count()

        # Throughput: flow records completed in last hour
        one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
        # Also check CVInferenceRecord for throughput
        throughput = db.query(InstrumentFlowRecord).filter(
            InstrumentFlowRecord.tenant_id == tenant_id,
            InstrumentFlowRecord.departed_at.isnot(None),
            InstrumentFlowRecord.departed_at >= one_hour_ago,
        ).count()

        try:
            from app.models.cv_inference import CVInferenceRecord  # type: ignore
            cv_count = db.query(CVInferenceRecord).filter(
                CVInferenceRecord.tenant_id == tenant_id,
            ).count()
            if cv_count > 0 and throughput == 0:
                # Use CV records as proxy for throughput
                throughput = min(cv_count, 30)
        except Exception:
            pass

        # Station statuses
        station_statuses = [_station_to_status(s) for s in stations]

        # Bottleneck: station with highest utilization
        bottleneck = ""
        max_util = 0.0
        total_util = 0.0
        for ss in station_statuses:
            total_util += ss.utilization_pct
            if ss.utilization_pct > max_util:
                max_util = ss.utilization_pct
                bottleneck = ss.station_name

        avg_util = total_util / len(station_statuses) if station_statuses else 0.0

        # Avg cycle time from completed flows
        completed_flows = db.query(InstrumentFlowRecord).filter(
            InstrumentFlowRecord.tenant_id == tenant_id,
            InstrumentFlowRecord.departed_at.isnot(None),
            InstrumentFlowRecord.processing_time_minutes > 0,
        ).all()

        if completed_flows:
            avg_cycle = sum(f.processing_time_minutes for f in completed_flows) / len(completed_flows)
        else:
            # Estimate from station processing times
            avg_cycle = sum(s.avg_processing_time_minutes for s in stations)

        # Generate alerts for high utilization
        _check_and_create_alerts(tenant_id, facility_id, station_statuses, avg_cycle, db)

        now = datetime.now(timezone.utc)
        kpis = {
            "throughput": throughput,
            "cycle_time": round(avg_cycle, 1),
            "utilization": round(avg_util, 1),
            "defect_rate": 0.0,
            "instruments_in_flight": in_flight,
            "bottleneck_utilization": round(max_util, 1),
        }

        return TwinStateResult(
            tenant_id=tenant_id,
            facility_id=facility_id,
            snapshot_at=now.isoformat(),
            data_source="real",
            total_instruments_in_flight=in_flight,
            throughput_per_hour=float(throughput),
            bottleneck_station=bottleneck,
            avg_cycle_time_minutes=round(avg_cycle, 1),
            utilization_pct=round(avg_util, 1),
            stations=station_statuses,
            kpis=kpis,
        )
    except Exception:
        return _mock_twin_state(tenant_id, facility_id)


def _check_and_create_alerts(
    tenant_id: str,
    facility_id: str,
    station_statuses: list[StationStatus],
    avg_cycle: float,
    db: Session,
) -> None:
    """Create alerts for overloaded stations and high cycle times."""
    for ss in station_statuses:
        if ss.utilization_pct > 90:
            # Check if alert already exists
            existing = db.query(SPDAlert).filter_by(
                tenant_id=tenant_id,
                station_name=ss.station_name,
                acknowledged=False,
                alert_type="overload",
            ).first()
            if not existing:
                alert_type = "bottleneck" if ss.utilization_pct >= 95 else "overload"
                severity = "critical" if ss.utilization_pct >= 95 else "high"
                alert = SPDAlert(
                    tenant_id=tenant_id,
                    facility_id=facility_id,
                    alert_type=alert_type,
                    severity=severity,
                    station_name=ss.station_name,
                    message=f"Station '{ss.station_name}' utilization at {ss.utilization_pct:.1f}% — exceeds 90% threshold.",
                    metric_value=ss.utilization_pct,
                    threshold_value=90.0,
                )
                db.add(alert)

        if ss.status == "offline":
            existing = db.query(SPDAlert).filter_by(
                tenant_id=tenant_id,
                station_name=ss.station_name,
                acknowledged=False,
                alert_type="station_offline",
            ).first()
            if not existing:
                alert = SPDAlert(
                    tenant_id=tenant_id,
                    facility_id=facility_id,
                    alert_type="station_offline",
                    severity="high",
                    station_name=ss.station_name,
                    message=f"Station '{ss.station_name}' is offline.",
                    metric_value=0.0,
                    threshold_value=0.0,
                )
                db.add(alert)

    if avg_cycle > 120:
        existing = db.query(SPDAlert).filter_by(
            tenant_id=tenant_id,
            acknowledged=False,
            alert_type="cycle_time_exceeded",
        ).first()
        if not existing:
            alert = SPDAlert(
                tenant_id=tenant_id,
                facility_id=facility_id,
                alert_type="cycle_time_exceeded",
                severity="medium",
                message=f"Average cycle time {avg_cycle:.1f} min exceeds 120 min threshold.",
                metric_value=avg_cycle,
                threshold_value=120.0,
            )
            db.add(alert)

    try:
        db.commit()
    except Exception:
        db.rollback()


def _mock_twin_state(tenant_id: str, facility_id: str) -> TwinStateResult:
    """Deterministic mock twin state."""
    rng = _seed(f"twin:{tenant_id}:{facility_id}")
    now = datetime.now(timezone.utc)

    stations = []
    station_id = 1
    total_util = 0.0
    bottleneck = ""
    max_util = 0.0

    for s in DEFAULT_STATIONS:
        stype = s["station_type"]
        lo, hi = MOCK_UTILIZATION_RANGES.get(stype, (0.3, 0.6))
        util = round(rng.uniform(lo, hi) * 100, 1)
        cap = s["capacity"]
        load = int(util / 100 * cap)
        total_util += util
        if util > max_util:
            max_util = util
            bottleneck = s["station_name"]
        stations.append(StationStatus(
            id=station_id,
            tenant_id=tenant_id,
            facility_id=facility_id,
            station_name=s["station_name"],
            station_type=stype,
            capacity=cap,
            current_load=load,
            avg_processing_time_minutes=s["avg_processing_time_minutes"],
            status="active",
            utilization_pct=util,
            last_updated=now.isoformat(),
        ))
        station_id += 1

    avg_util = round(total_util / len(DEFAULT_STATIONS), 1)
    throughput = round(rng.uniform(15, 45), 1)
    avg_cycle = round(sum(s["avg_processing_time_minutes"] for s in DEFAULT_STATIONS if s["avg_processing_time_minutes"] > 0) / 6, 1)
    in_flight = int(rng.uniform(5, 30))

    kpis = {
        "throughput": throughput,
        "cycle_time": avg_cycle,
        "utilization": avg_util,
        "defect_rate": round(rng.uniform(0.01, 0.05), 3),
        "instruments_in_flight": in_flight,
        "bottleneck_utilization": round(max_util, 1),
    }

    return TwinStateResult(
        tenant_id=tenant_id,
        facility_id=facility_id,
        snapshot_at=now.isoformat(),
        data_source="mock",
        total_instruments_in_flight=in_flight,
        throughput_per_hour=throughput,
        bottleneck_station=bottleneck,
        avg_cycle_time_minutes=avg_cycle,
        utilization_pct=avg_util,
        stations=stations,
        kpis=kpis,
    )


def get_instrument_flow(
    tenant_id: str,
    facility_id: str,
    limit: int,
    db: Session,
) -> list[InstrumentFlowResult]:
    """Return recent instrument flow records."""
    q = db.query(InstrumentFlowRecord).filter_by(tenant_id=tenant_id)
    if facility_id:
        q = q.filter_by(facility_id=facility_id)
    flows = q.order_by(InstrumentFlowRecord.arrived_at.desc()).limit(limit).all()
    return [_flow_to_result(f) for f in flows]


def log_instrument_flow(
    tenant_id: str,
    facility_id: str,
    instrument_name: str,
    instrument_id: str,
    from_station: str,
    to_station: str,
    station_type: str,
    notes: str,
    db: Session,
) -> InstrumentFlowResult:
    """Log an instrument movement to a station."""
    now = datetime.now(timezone.utc)
    flow = InstrumentFlowRecord(
        tenant_id=tenant_id,
        facility_id=facility_id,
        instrument_name=instrument_name,
        instrument_id=instrument_id,
        from_station=from_station,
        to_station=to_station,
        station_type=station_type,
        arrived_at=now,
        outcome="pending",
        notes=notes,
    )
    db.add(flow)

    # Update station load
    station = db.query(SPDWorkflowStation).filter_by(
        tenant_id=tenant_id, station_name=to_station
    ).first()
    if station:
        station.current_load = station.current_load + 1
        station.last_updated = now
        # Auto-generate alert if utilization now > 90%
        util = (station.current_load / max(station.capacity, 1)) * 100
        if util > 90:
            existing = db.query(SPDAlert).filter_by(
                tenant_id=tenant_id,
                station_name=station.station_name,
                acknowledged=False,
                alert_type="overload",
            ).first()
            if not existing:
                alert = SPDAlert(
                    tenant_id=tenant_id,
                    facility_id=facility_id,
                    alert_type="overload",
                    severity="high",
                    station_name=station.station_name,
                    message=f"Station '{station.station_name}' overloaded at {util:.1f}% utilization.",
                    metric_value=util,
                    threshold_value=90.0,
                )
                db.add(alert)

    db.commit()
    db.refresh(flow)
    return _flow_to_result(flow)


def complete_flow(
    flow_id: int,
    outcome: str,
    notes: str,
    tenant_id: str,
    db: Session,
) -> InstrumentFlowResult:
    """Complete a flow record."""
    flow = db.query(InstrumentFlowRecord).filter_by(id=flow_id, tenant_id=tenant_id).first()
    if flow is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Flow record not found.")

    now = datetime.now(timezone.utc)
    arrived = flow.arrived_at
    if arrived.tzinfo is None:
        arrived = arrived.replace(tzinfo=timezone.utc)

    flow.departed_at = now
    flow.outcome = outcome
    flow.processing_time_minutes = (now - arrived).total_seconds() / 60
    if notes:
        flow.notes = notes

    # Decrement station load
    station = db.query(SPDWorkflowStation).filter_by(
        tenant_id=tenant_id, station_name=flow.to_station
    ).first()
    if station:
        station.current_load = max(0, station.current_load - 1)
        station.last_updated = now

    db.commit()
    db.refresh(flow)
    return _flow_to_result(flow)


def get_stations(tenant_id: str, facility_id: str, db: Session) -> list[StationStatus]:
    """Return all stations for a tenant."""
    stations = _ensure_stations(tenant_id, facility_id, db)
    return [_station_to_status(s) for s in stations]


def get_alerts(tenant_id: str, facility_id: str, db: Session) -> list[SPDAlertResult]:
    """Return open alerts."""
    q = db.query(SPDAlert).filter_by(tenant_id=tenant_id, acknowledged=False)
    if facility_id:
        q = q.filter_by(facility_id=facility_id)
    alerts = q.order_by(SPDAlert.created_at.desc()).all()
    return [_alert_to_result(a) for a in alerts]


def acknowledge_alert(
    alert_id: int,
    acknowledged_by: str,
    tenant_id: str,
    db: Session,
) -> SPDAlertResult:
    """Acknowledge an alert."""
    alert = db.query(SPDAlert).filter_by(id=alert_id, tenant_id=tenant_id).first()
    if alert is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Alert not found.")
    alert.acknowledged = True
    alert.acknowledged_by = acknowledged_by
    alert.resolved_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(alert)
    return _alert_to_result(alert)


def simulate_whatif(
    tenant_id: str,
    scenario: WhatIfRequest,
    db: Session,
) -> WhatIfResult:
    """Run a what-if simulation."""
    # Get current baseline
    twin = get_twin_state(tenant_id, "", db)
    baseline = {
        "throughput_per_hour": twin.throughput_per_hour,
        "avg_cycle_time_minutes": twin.avg_cycle_time_minutes,
        "utilization_pct": twin.utilization_pct,
        "bottleneck_station": twin.bottleneck_station,
        "total_instruments_in_flight": twin.total_instruments_in_flight,
    }

    # Copy station data for simulation
    sim_stations = [s.model_copy() for s in twin.stations]

    # Apply scenario
    if scenario.add_station:
        # Find default params for this station type
        default = next(
            (d for d in DEFAULT_STATIONS if d["station_type"] == scenario.add_station),
            {"capacity": 10, "avg_processing_time_minutes": 30.0},
        )
        new_station = StationStatus(
            id=9999,
            tenant_id=tenant_id,
            facility_id="",
            station_name=f"New {scenario.add_station.title()} Station",
            station_type=scenario.add_station,
            capacity=default["capacity"],
            current_load=0,
            avg_processing_time_minutes=default["avg_processing_time_minutes"],
            status="active",
            utilization_pct=0.0,
            last_updated=datetime.now(timezone.utc).isoformat(),
        )
        sim_stations.append(new_station)

    if scenario.remove_station:
        sim_stations = [s for s in sim_stations if s.station_name != scenario.remove_station]

    if scenario.capacity_change:
        for s in sim_stations:
            if s.station_name in scenario.capacity_change:
                new_cap = scenario.capacity_change[s.station_name]
                new_util = round((s.current_load / max(new_cap, 1)) * 100, 1)
                sim_stations[sim_stations.index(s)] = s.model_copy(
                    update={"capacity": new_cap, "utilization_pct": new_util}
                )

    if scenario.volume_change_pct != 0:
        factor = 1 + scenario.volume_change_pct / 100
        new_stations = []
        for s in sim_stations:
            new_load = int(s.current_load * factor)
            new_cap = max(s.capacity, 1)
            new_util = round((new_load / new_cap) * 100, 1)
            new_stations.append(s.model_copy(
                update={"current_load": new_load, "utilization_pct": new_util}
            ))
        sim_stations = new_stations

    # Recompute KPIs
    total_util = sum(s.utilization_pct for s in sim_stations)
    avg_util = round(total_util / len(sim_stations), 1) if sim_stations else 0.0
    bottleneck = max(sim_stations, key=lambda s: s.utilization_pct, default=None)
    bottleneck_name = bottleneck.station_name if bottleneck else ""

    # Throughput scales inversely with utilization; higher capacity → more throughput
    utilization_ratio = avg_util / max(twin.utilization_pct, 1)
    sim_throughput = round(twin.throughput_per_hour / max(utilization_ratio, 0.1), 1)

    # Cycle time: lower utilization = faster processing
    sim_cycle = round(twin.avg_cycle_time_minutes * utilization_ratio, 1)

    simulated = {
        "throughput_per_hour": sim_throughput,
        "avg_cycle_time_minutes": sim_cycle,
        "utilization_pct": avg_util,
        "bottleneck_station": bottleneck_name,
        "total_instruments_in_flight": twin.total_instruments_in_flight,
    }

    delta = {
        k: round(simulated[k] - baseline[k], 2) if isinstance(baseline[k], (int, float)) else simulated[k]
        for k in baseline
        if k != "bottleneck_station"
    }
    delta["bottleneck_station"] = simulated["bottleneck_station"]

    # Recommendation
    recs = []
    if delta.get("throughput_per_hour", 0) > 0:
        recs.append(f"Throughput improves by {delta['throughput_per_hour']:.1f} instruments/hour.")
    if delta.get("avg_cycle_time_minutes", 0) < 0:
        recs.append(f"Cycle time reduces by {abs(delta['avg_cycle_time_minutes']):.1f} minutes.")
    if delta.get("utilization_pct", 0) < 0:
        recs.append(f"Overall utilization drops by {abs(delta['utilization_pct']):.1f}%, reducing bottleneck risk.")
    if delta.get("utilization_pct", 0) > 10:
        recs.append("Warning: increased utilization may create new bottlenecks.")
    if not recs:
        recs.append("Minimal impact expected from this change.")
    recommendation = " ".join(recs)

    # Persist scenario
    params = {
        "add_station": scenario.add_station,
        "remove_station": scenario.remove_station,
        "capacity_change": scenario.capacity_change,
        "volume_change_pct": scenario.volume_change_pct,
    }
    result_data = {
        "baseline": baseline,
        "simulated": simulated,
        "delta": delta,
        "recommendation": recommendation,
    }
    now = datetime.now(timezone.utc)
    db_scenario = WhatIfScenario(
        tenant_id=tenant_id,
        scenario_name=scenario.scenario_name,
        description=scenario.description,
        parameters_json=json.dumps(params),
        result_json=json.dumps(result_data),
        created_by="system",
        created_at=now,
    )
    db.add(db_scenario)
    db.commit()
    db.refresh(db_scenario)

    return WhatIfResult(
        id=db_scenario.id,
        scenario_name=scenario.scenario_name,
        description=scenario.description,
        parameters=params,
        baseline=baseline,
        simulated=simulated,
        delta=delta,
        recommendation=recommendation,
        created_at=_dt_str(db_scenario.created_at) or now.isoformat(),
    )


def list_whatif_scenarios(tenant_id: str, db: Session) -> list[WhatIfResult]:
    """List saved what-if scenarios."""
    scenarios = (
        db.query(WhatIfScenario)
        .filter_by(tenant_id=tenant_id)
        .order_by(WhatIfScenario.created_at.desc())
        .limit(20)
        .all()
    )
    results = []
    for sc in scenarios:
        try:
            result_data = json.loads(sc.result_json or "{}")
            params = json.loads(sc.parameters_json or "{}")
        except Exception:
            result_data = {}
            params = {}
        results.append(WhatIfResult(
            id=sc.id,
            scenario_name=sc.scenario_name,
            description=sc.description or "",
            parameters=params,
            baseline=result_data.get("baseline", {}),
            simulated=result_data.get("simulated", {}),
            delta=result_data.get("delta", {}),
            recommendation=result_data.get("recommendation", ""),
            created_at=_dt_str(sc.created_at) or "",
        ))
    return results


def compute_twin_dashboard(tenant_id: str, facility_id: str, db: Session) -> TwinDashboard:
    """Build the full twin dashboard."""
    twin_state = get_twin_state(tenant_id, facility_id, db)
    recent_flow = get_instrument_flow(tenant_id, facility_id, 20, db)
    open_alerts = get_alerts(tenant_id, facility_id, db)

    # Last 5 scenarios
    scenarios = list_whatif_scenarios(tenant_id, db)[:5]

    # 24h trend data (seeded mock)
    rng = _seed(f"trend:{tenant_id}:{facility_id}")
    now = datetime.now(timezone.utc)
    trend_data = []
    for h in range(23, -1, -1):
        hour_dt = now - timedelta(hours=h)
        trend_data.append({
            "hour": hour_dt.strftime("%H:00"),
            "throughput": round(rng.uniform(10, 40), 1),
            "utilization": round(rng.uniform(40, 85), 1),
        })

    # Recommendations
    recommendations = []
    if twin_state.bottleneck_station:
        recommendations.append(
            f"Address bottleneck at '{twin_state.bottleneck_station}' — consider adding capacity."
        )
    for alert in open_alerts[:3]:
        recommendations.append(f"Resolve {alert.severity} alert: {alert.message}")
    if twin_state.avg_cycle_time_minutes > 120:
        recommendations.append("Cycle time exceeds 120 min — review sterilization queue.")
    if not recommendations:
        recommendations.append("All SPD operations are within normal parameters.")

    return TwinDashboard(
        tenant_id=tenant_id,
        facility_id=facility_id,
        generated_at=now.isoformat(),
        data_source=twin_state.data_source,
        twin_state=twin_state,
        recent_flow=recent_flow,
        open_alerts=open_alerts,
        what_if_scenarios=scenarios,
        trend_data=trend_data,
        recommendations=recommendations,
    )
