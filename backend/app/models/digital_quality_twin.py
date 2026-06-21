"""P22: Healthcare Digital Quality Twin — SQLAlchemy models."""
from __future__ import annotations

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text
from sqlalchemy.sql import func

from app.db.base import Base


class QualityTwinState(Base):
    """Unified quality state snapshot for a facility."""

    __tablename__ = "quality_twin_states"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(String, nullable=False, index=True)
    facility_id = Column(String, default="")
    snapshot_date = Column(DateTime(timezone=True), server_default=func.now())
    overall_quality_score = Column(Float, default=0.0)
    inspection_quality_score = Column(Float, default=0.0)
    patient_safety_score = Column(Float, default=0.0)
    vendor_performance_score = Column(Float, default=0.0)
    recall_exposure_score = Column(Float, default=0.0)
    infection_prevention_score = Column(Float, default=0.0)
    capa_effectiveness_score = Column(Float, default=0.0)
    benchmarking_percentile = Column(Float, default=50.0)
    open_emerging_risks = Column(Integer, default=0)
    open_investigations = Column(Integer, default=0)
    pending_recommendations = Column(Integer, default=0)
    active_recalls = Column(Integer, default=0)
    trend_direction = Column(String, default="stable")
    trend_confidence = Column(Float, default=0.0)
    data_source = Column(String, default="simulated")
    human_review_required = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ScenarioSimulation(Base):
    """What-if scenario simulation record."""

    __tablename__ = "scenario_simulations"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(String, nullable=False, index=True)
    scenario_name = Column(String, nullable=False)
    scenario_type = Column(String, nullable=False)
    intervention_type = Column(String, nullable=False)
    intervention_description = Column(Text)
    parameters = Column(Text)
    projected_quality_delta = Column(Float, default=0.0)
    projected_risk_reduction = Column(Float, default=0.0)
    projected_timeframe_days = Column(Integer, default=90)
    confidence_score = Column(Float, default=0.0)
    association_reason = Column(Text)
    human_review_required = Column(Boolean, default=True, nullable=False)
    disclaimer = Column(
        Text,
        default=(
            "Simulation output for planning purposes only. Does not establish causation "
            "or predict specific outcomes. Human review required before any operational decisions."
        ),
    )
    status = Column(String, default="draft")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    reviewed_by = Column(String, nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)


class QualityForecast(Base):
    """Forward-looking quality risk projection."""

    __tablename__ = "quality_forecasts"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(String, nullable=False, index=True)
    facility_id = Column(String, default="")
    forecast_horizon_days = Column(Integer, nullable=False)
    forecast_date = Column(DateTime(timezone=True), server_default=func.now())
    projected_quality_score = Column(Float)
    projected_risk_level = Column(String)
    risk_drivers = Column(Text)
    recommended_interventions = Column(Text)
    confidence_score = Column(Float, default=0.0)
    association_reason = Column(Text)
    human_review_required = Column(Boolean, default=True, nullable=False)
    disclaimer = Column(
        Text,
        default=(
            "Forecast is a modeled projection for planning purposes. Does not establish causation "
            "or guarantee outcomes. All forecasts require human review before operational decisions."
        ),
    )
    data_source = Column(String, default="simulated")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class InterventionModel(Base):
    """Advisory intervention model with projected quality outcomes."""

    __tablename__ = "intervention_models"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(String, nullable=False, index=True)
    intervention_type = Column(String, nullable=False)
    intervention_target = Column(String)
    baseline_quality_score = Column(Float)
    projected_quality_score = Column(Float)
    projected_improvement = Column(Float)
    effort_estimate = Column(String)
    timeframe_days = Column(Integer, default=90)
    confidence_score = Column(Float, default=0.0)
    association_reason = Column(Text)
    human_review_required = Column(Boolean, default=True, nullable=False)
    disclaimer = Column(
        Text,
        default=(
            "Intervention model is advisory only. Projected outcomes are estimates based on "
            "available data patterns. Does not establish causation. Human review and approval "
            "required before implementation."
        ),
    )
    status = Column(String, default="modeled")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ExecutiveDecisionBrief(Base):
    """Role-specific executive decision support brief."""

    __tablename__ = "executive_decision_briefs"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(String, nullable=False, index=True)
    role = Column(String, nullable=False)
    brief_date = Column(DateTime(timezone=True), server_default=func.now())
    headline_risk = Column(String)
    top_concerns = Column(Text)
    recommended_actions = Column(Text)
    emerging_signals_count = Column(Integer, default=0)
    quality_trend = Column(String, default="stable")
    vendor_exposure_summary = Column(Text)
    recall_exposure_summary = Column(Text)
    patient_safety_summary = Column(Text)
    human_review_required = Column(Boolean, default=True, nullable=False)
    disclaimer = Column(
        Text,
        default=(
            "This brief is generated from available quality signals for decision support. "
            "All findings represent potential associations for human review. Does not establish "
            "causation or constitute clinical guidance."
        ),
    )
    data_source = Column(String, default="simulated")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
