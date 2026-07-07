"""Phase 22 §11 — Agent Context Objects.

Every agent in the multi-agent pipeline reads a typed input context and
produces a typed output context. No agent reads raw frontend state or a
raw request payload directly — the orchestrator (app/agents/orchestrator.py)
is the only thing that touches the database row, and every agent after the
first only ever sees the previous agent's context object.

These are pydantic models purely for structure/serialization — they carry
no business logic themselves.
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class InstrumentContext(BaseModel):
    instrument_type: str
    manufacturer: str = ""
    model: str = ""
    instrument_family: str
    instrument_category: str
    anatomy_zones: list[str] = []
    high_risk_zones: list[str] = []
    ifu_reference: str = ""
    digital_twin_available: bool = False
    profile_found: bool = True
    warning: Optional[str] = None


class AnatomyContext(BaseModel):
    instrument_family: str
    anatomy_zones: list[str] = []
    required_zones: list[str] = []
    high_retention_zones: list[str] = []
    inspected_zones: Optional[list[str]] = None
    missing_zones: list[str] = []
    inspection_completeness: Optional[int] = None  # 0-100, None when not assessed


class CoverageContext(BaseModel):
    coverage_pct: Optional[int] = None
    required_images: list[str] = []
    missing_images: list[str] = []
    coverage_quality: str = "not_assessed"
    capture_guidance: list[str] = []


class ContaminationFinding(BaseModel):
    finding_type: str
    probability: Optional[float] = None
    severity: str = "none"
    confidence: Optional[float] = None
    zone: str = ""
    clinical_significance: str = ""


class ContaminationContext(BaseModel):
    findings: list[ContaminationFinding] = []
    has_contamination: bool = False


class DamageFinding(BaseModel):
    finding_type: str
    severity: str = "none"
    repair_recommendation: str = ""
    trend: str = "stable"


class DamageContext(BaseModel):
    findings: list[DamageFinding] = []
    has_damage: bool = False


class ClinicalReasoningContext(BaseModel):
    interpretation: str
    reasoning_chain: list[dict] = []
    risk_level: Optional[str] = None
    risk_score: Optional[int] = None


class RecommendationContext(BaseModel):
    readiness_state: str  # READY_FOR_PACKAGING | REQUIRES_RECLEANING | REQUIRES_SUPERVISOR_REVIEW | REQUIRES_REPAIR | REMOVED_FROM_SERVICE | PENDING_ANALYSIS
    repair_candidate: bool = False
    explanation: str = ""
    human_review_required: bool = True


class SupervisorContext(BaseModel):
    review_exists: bool = False
    agreement: Optional[str] = None
    corrections: dict = {}
    override_action: str = ""
    ground_truth_label: Optional[str] = None
    training_label_created: bool = False


class LearningContext(BaseModel):
    knowledge_confidence: Optional[float] = None
    reasoning_confidence: Optional[float] = None
    clinical_recommendation_confidence: Optional[float] = None
    zone_confidence: Optional[float] = None
    sample_sizes: dict = {}
    note: str = ""


class EnterpriseContext(BaseModel):
    facility: Optional[str] = None
    facility_readiness_rate: Optional[float] = None
    most_common_contamination_type: list[dict] = []
    highest_risk_anatomy_zone: Optional[str] = None
    note: str = ""


class AgentTraceEntry(BaseModel):
    agent: str
    version: str
    input_summary: dict
    output_summary: dict
