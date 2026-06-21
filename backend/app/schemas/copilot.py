"""P9: Autonomous Inspection Copilot — Pydantic v2 schemas."""
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, ConfigDict


# ── Request schemas ──────────────────────────────────────────────────────────

class StartSessionRequest(BaseModel):
    technician_id: str
    instrument_name: str
    instrument_id: str = ""
    facility_id: str = ""
    copilot_mode: str = "guided"  # guided | autonomous | audit


class StepResponseRequest(BaseModel):
    technician_response: str  # pass | fail | skip | escalate
    finding_category: str = ""
    notes: str = ""


class ResolveEscalationRequest(BaseModel):
    resolved_by: str
    notes: str = ""


# ── Result schemas ───────────────────────────────────────────────────────────

class InspectionStepResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    session_id: int
    step_number: int
    step_type: str
    step_title: str
    step_instructions: str
    ai_recommendation: str
    technician_response: str
    finding_category: str
    severity: str
    confidence: float
    completed_at: Optional[str]
    notes: str


class CopilotRecommendationResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    session_id: int
    step_id: Optional[int]
    recommendation_type: str
    message: str
    confidence: float
    evidence: list[dict[str, Any]]
    acted_on: bool
    technician_decision: str
    created_at: str


class InspectionSessionResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tenant_id: str
    facility_id: str
    technician_id: str
    instrument_name: str
    instrument_id: str
    session_status: str
    started_at: str
    completed_at: Optional[str]
    total_steps: int
    completed_steps: int
    copilot_mode: str
    risk_level: str
    session_notes: str
    escalation_reason: str
    steps: list[InspectionStepResult] = []
    recommendations: list[CopilotRecommendationResult] = []
    data_source: str = "real"


class EscalationEventResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    session_id: int
    tenant_id: str
    escalation_type: str
    severity: str
    description: str
    auto_generated: bool
    notified_supervisor: bool
    resolved: bool
    resolved_by: str
    resolved_at: Optional[str]
    created_at: str


class ProtocolResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tenant_id: str
    protocol_name: str
    instrument_category: str
    steps: list[dict[str, Any]]
    is_active: bool
    version: int
    created_by: str


class CopilotDashboard(BaseModel):
    tenant_id: str
    facility_id: str
    generated_at: str
    data_source: str
    active_sessions: int
    completed_today: int
    escalations_open: int
    escalations_resolved: int
    avg_session_duration_minutes: float
    pass_rate_pct: float
    high_risk_instruments: list[str]
    top_finding_categories: list[dict[str, Any]]  # [{category, count, pct}]
    protocol_compliance_pct: float
    technician_performance: list[dict[str, Any]]  # [{technician_id, sessions, pass_rate}]
