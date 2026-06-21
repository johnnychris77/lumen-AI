"""P9: Autonomous Inspection Copilot — ORM models."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text

from app.db.base import Base


class InspectionSession(Base):
    """Active inspection session managed by the copilot."""
    __tablename__ = "inspection_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(String(100), nullable=False, index=True)
    facility_id = Column(String(100), nullable=False, default="")
    technician_id = Column(String(100), nullable=False)
    instrument_name = Column(String(255), nullable=False)
    instrument_id = Column(String(200), nullable=False, default="")
    session_status = Column(String(50), nullable=False, default="active")  # active|paused|completed|escalated
    started_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime, nullable=True)
    total_steps = Column(Integer, nullable=False, default=0)
    completed_steps = Column(Integer, nullable=False, default=0)
    copilot_mode = Column(String(50), nullable=False, default="guided")  # guided|autonomous|audit
    risk_level = Column(String(50), nullable=False, default="unknown")  # low|medium|high|critical
    session_notes = Column(Text, nullable=False, default="")
    escalation_reason = Column(Text, nullable=False, default="")


class InspectionStep(Base):
    """Individual step within an inspection session."""
    __tablename__ = "inspection_steps"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("inspection_sessions.id"), nullable=False, index=True)
    step_number = Column(Integer, nullable=False)
    step_type = Column(String(50), nullable=False)  # visual|contamination|structural|functional|documentation
    step_title = Column(String(255), nullable=False)
    step_instructions = Column(Text, nullable=False)
    ai_recommendation = Column(Text, nullable=False, default="")
    technician_response = Column(String(50), nullable=False, default="")  # pass|fail|skip|escalate
    finding_category = Column(String(100), nullable=False, default="")
    severity = Column(String(50), nullable=False, default="none")
    confidence = Column(Float, nullable=False, default=0.0)
    completed_at = Column(DateTime, nullable=True)
    image_path = Column(String(500), nullable=False, default="")
    notes = Column(Text, nullable=False, default="")


class CopilotRecommendation(Base):
    """AI-generated recommendations during inspection."""
    __tablename__ = "copilot_recommendations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("inspection_sessions.id"), nullable=False, index=True)
    step_id = Column(Integer, ForeignKey("inspection_steps.id"), nullable=True)
    recommendation_type = Column(String(50), nullable=False)  # action|warning|escalate|approve|reject
    message = Column(Text, nullable=False)
    confidence = Column(Float, nullable=False, default=0.0)
    evidence = Column(Text, nullable=False, default="[]")  # JSON array
    acted_on = Column(Boolean, nullable=False, default=False)
    technician_decision = Column(String(50), nullable=False, default="")  # accepted|rejected|deferred
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))


class InspectionProtocol(Base):
    """Reusable inspection protocol templates."""
    __tablename__ = "inspection_protocols"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(String(100), nullable=False, index=True)
    protocol_name = Column(String(255), nullable=False)
    instrument_category = Column(String(100), nullable=False)
    steps_json = Column(Text, nullable=False, default="[]")
    is_active = Column(Boolean, nullable=False, default=True)
    created_by = Column(String(100), nullable=False, default="system")
    version = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))


class EscalationEvent(Base):
    """Tracks escalations triggered by the copilot."""
    __tablename__ = "escalation_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("inspection_sessions.id"), nullable=False, index=True)
    tenant_id = Column(String(100), nullable=False, index=True)
    escalation_type = Column(String(100), nullable=False)  # contamination|structural|recall|protocol_deviation|repeat_failure
    severity = Column(String(50), nullable=False)
    description = Column(Text, nullable=False)
    auto_generated = Column(Boolean, nullable=False, default=True)
    notified_supervisor = Column(Boolean, nullable=False, default=False)
    resolved = Column(Boolean, nullable=False, default=False)
    resolved_by = Column(String(100), nullable=False, default="")
    resolved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
