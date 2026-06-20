"""P7: Pydantic schemas for predictive analytics."""
from __future__ import annotations
from typing import Any
from pydantic import BaseModel, Field


class EvidenceFactor(BaseModel):
    factor: str
    value: float | str
    weight: float
    signal: str  # "elevated" | "degrading" | "stable" | "below_threshold" | "above_threshold"


class InstrumentFailurePredictionResult(BaseModel):
    instrument_name: str
    instrument_category: str = ""
    tenant_id: str
    facility_id: str = ""
    prediction_date: str
    horizon_days: int = 30
    failure_probability: float = 0.0
    risk_score: float = 0.0
    risk_category: str = "low"
    confidence: float = 0.0
    records_used: int = 0
    evidence: list[EvidenceFactor] = Field(default_factory=list)
    recommended_action: str = ""
    data_source: str = "real"


class ContaminationRecurrencePredictionResult(BaseModel):
    instrument_name: str
    instrument_category: str = ""
    tenant_id: str
    facility_id: str = ""
    prediction_date: str
    recurrence_probability: float = 0.0
    risk_score: float = 0.0
    risk_category: str = "low"
    confidence: float = 0.0
    dominant_contaminant: str = ""
    records_used: int = 0
    evidence: list[EvidenceFactor] = Field(default_factory=list)
    recommended_action: str = ""
    data_source: str = "real"


class RepairForecastResult(BaseModel):
    instrument_name: str
    instrument_category: str = ""
    tenant_id: str
    facility_id: str = ""
    prediction_date: str
    repair_probability_90d: float = 0.0
    replacement_probability_180d: float = 0.0
    risk_score: float = 0.0
    risk_category: str = "low"
    confidence: float = 0.0
    estimated_repair_cost_usd: float = 0.0
    estimated_replacement_cost_usd: float = 0.0
    recommended_action: str = ""
    records_used: int = 0
    evidence: list[EvidenceFactor] = Field(default_factory=list)
    data_source: str = "real"


class RecallRiskAssessmentResult(BaseModel):
    instrument_category: str
    tenant_id: str
    assessment_date: str
    exposure_score: float = 0.0
    active_recall_count: int = 0
    critical_recall_count: int = 0
    instruments_affected_estimate: int = 0
    urgency_tier: str = "low"
    evidence: list[EvidenceFactor] = Field(default_factory=list)
    recommended_action: str = ""
    data_source: str = "real"


class TrayRiskAssessmentResult(BaseModel):
    tray_id: str
    tenant_id: str
    facility_id: str = ""
    assessment_date: str
    tray_risk_score: float = 0.0
    risk_category: str = "low"
    instrument_count: int = 0
    high_risk_instrument_count: int = 0
    highest_risk_instrument: str = ""
    worst_failure_probability: float = 0.0
    recommended_action: str = ""
    evidence: list[EvidenceFactor] = Field(default_factory=list)
    data_source: str = "real"


class PredictiveDashboard(BaseModel):
    tenant_id: str
    facility_id: str = ""
    generated_at: str
    data_source: str = "real"

    # KPIs
    predicted_failures_30d: int = 0
    predicted_failures_90d: int = 0
    high_risk_instrument_count: int = 0
    critical_risk_instrument_count: int = 0
    projected_repair_cost_usd: float = 0.0
    projected_replacement_cost_usd: float = 0.0
    contamination_recurrence_rate_pct: float = 0.0
    recall_exposure_score: float = 0.0
    highest_risk_trays: list[dict[str, Any]] = Field(default_factory=list)
    highest_risk_instruments: list[dict[str, Any]] = Field(default_factory=list)
    top_contamination_risks: list[dict[str, Any]] = Field(default_factory=list)
    recall_risk_by_category: list[dict[str, Any]] = Field(default_factory=list)

    # Explainability summary
    top_risk_factors: list[str] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)
