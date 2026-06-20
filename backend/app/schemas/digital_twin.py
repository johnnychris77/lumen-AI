"""P10: Digital Twin of SPD Operations — Pydantic schemas."""
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, ConfigDict


class StationStatus(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tenant_id: str
    facility_id: str
    station_name: str
    station_type: str
    capacity: int
    current_load: int
    avg_processing_time_minutes: float
    status: str
    utilization_pct: float
    last_updated: str


class InstrumentFlowResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tenant_id: str
    instrument_name: str
    instrument_id: str
    from_station: str
    to_station: str
    station_type: str
    arrived_at: str
    departed_at: Optional[str]
    processing_time_minutes: float
    outcome: str
    notes: str


class TwinStateResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    tenant_id: str
    facility_id: str
    snapshot_at: str
    data_source: str
    total_instruments_in_flight: int
    throughput_per_hour: float
    bottleneck_station: str
    avg_cycle_time_minutes: float
    utilization_pct: float
    stations: list[StationStatus]
    kpis: dict[str, Any]


class WhatIfRequest(BaseModel):
    scenario_name: str
    description: str = ""
    add_station: Optional[str] = None
    remove_station: Optional[str] = None
    capacity_change: dict[str, int] = {}
    volume_change_pct: float = 0.0


class WhatIfResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: Optional[int]
    scenario_name: str
    description: str
    parameters: dict[str, Any]
    baseline: dict[str, Any]
    simulated: dict[str, Any]
    delta: dict[str, Any]
    recommendation: str
    created_at: str


class SPDAlertResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tenant_id: str
    facility_id: str
    alert_type: str
    severity: str
    station_name: str
    message: str
    metric_value: float
    threshold_value: float
    acknowledged: bool
    acknowledged_by: str
    created_at: str
    resolved_at: Optional[str]


class TwinDashboard(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    tenant_id: str
    facility_id: str
    generated_at: str
    data_source: str
    twin_state: TwinStateResult
    recent_flow: list[InstrumentFlowResult]
    open_alerts: list[SPDAlertResult]
    what_if_scenarios: list[WhatIfResult]
    trend_data: list[dict[str, Any]]
    recommendations: list[str]


class LogFlowRequest(BaseModel):
    instrument_name: str
    instrument_id: str = ""
    from_station: str = ""
    to_station: str
    station_type: str
    notes: str = ""


class CompleteFlowRequest(BaseModel):
    outcome: str = "passed"
    notes: str = ""


class AcknowledgeAlertRequest(BaseModel):
    acknowledged_by: str = "system"
