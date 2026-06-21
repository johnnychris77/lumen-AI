"""P21: Autonomous Healthcare Quality Intelligence Network — SQLAlchemy models."""
from __future__ import annotations

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.sql import func

from app.db.base import Base


class EnterpriseRiskNode(Base):
    """Node in the Enterprise Risk Graph."""

    __tablename__ = "enterprise_risk_nodes"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(String, nullable=False, index=True)
    node_type = Column(String, nullable=False)  # instrument/tray/vendor/manufacturer/capa/recall/safety_event/infection_signal/facility/service_line
    node_id = Column(String, nullable=False)  # external ID of the referenced entity
    node_label = Column(String)
    risk_score = Column(Float, default=0.0)
    last_updated = Column(DateTime(timezone=True), server_default=func.now())


class EnterpriseRiskEdge(Base):
    """Edge in the Enterprise Risk Graph."""

    __tablename__ = "enterprise_risk_edges"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(String, nullable=False, index=True)
    source_node_id = Column(Integer, ForeignKey("enterprise_risk_nodes.id"))
    target_node_id = Column(Integer, ForeignKey("enterprise_risk_nodes.id"))
    relationship_type = Column(String, nullable=False)  # linked_to/reported_in/associated_with/escalated_by/investigated_by
    weight = Column(Float, default=1.0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class EmergingRiskSignal(Base):
    """Detected emerging risk pattern."""

    __tablename__ = "emerging_risk_signals"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(String, nullable=False, index=True)
    signal_type = Column(String, nullable=False)  # recurring_contamination/recurring_baseline_deviation/recurring_capa/recurring_safety_event/recurring_vendor_finding/recurring_manufacturer_finding
    signal_description = Column(Text)
    confidence_score = Column(Float, default=0.0)
    trend_direction = Column(String)  # increasing/stable/decreasing
    facilities_affected = Column(Integer, default=1)
    review_recommendation = Column(Text)
    human_review_required = Column(Boolean, default=True, nullable=False)
    association_reason = Column(Text)  # required — explains basis for signal
    status = Column(String, default="open")  # open/under_review/resolved/dismissed
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class QualityInvestigationP21(Base):
    """Investigation coordination record (P21)."""

    __tablename__ = "quality_investigations_p21"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(String, nullable=False, index=True)
    title = Column(String, nullable=False)
    description = Column(Text)
    status = Column(String, default="open")  # open/in_progress/resolved/closed
    priority = Column(String, default="medium")  # low/medium/high/critical
    assigned_to = Column(String)
    signal_id = Column(Integer, ForeignKey("emerging_risk_signals.id"), nullable=True)
    capa_ids = Column(Text)  # JSON list of linked CAPA IDs
    recall_ids = Column(Text)  # JSON list of linked recall IDs
    evidence_notes = Column(Text)
    resolution_notes = Column(Text)
    opened_at = Column(DateTime(timezone=True), server_default=func.now())
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    human_review_required = Column(Boolean, default=True, nullable=False)


class PreventiveActionRecommendation(Base):
    """AI-generated preventive action recommendation (requires human review)."""

    __tablename__ = "preventive_action_recommendations"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(String, nullable=False, index=True)
    recommendation_type = Column(String, nullable=False)  # inspection_frequency/vendor_review/instrument_retirement/training_intervention/capa_review
    recommendation_text = Column(Text, nullable=False)
    rationale = Column(Text)
    confidence_score = Column(Float, default=0.0)
    signal_id = Column(Integer, ForeignKey("emerging_risk_signals.id"), nullable=True)
    status = Column(String, default="pending_review")  # pending_review/accepted/rejected/implemented
    effectiveness_score = Column(Float, nullable=True)
    human_review_required = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    reviewed_by = Column(String, nullable=True)
