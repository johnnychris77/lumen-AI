"""Pydantic schemas for the Inspection Ranking Engine."""
from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field


class RankingRequest(BaseModel):
    finding_id: int | None = None
    finding_category: str
    severity: str
    confidence_score: float = Field(ge=0.0, le=1.0)
    instrument_id: int | None = None
    instrument_name: str = ""
    instrument_category: str = ""
    barcode_value: str = ""
    qr_code_value: str = ""
    key_dot_value: str = ""
    baseline_status: str = ""
    instrument_match_status: str = ""
    tenant_id: str = "default-tenant"


class CompositeFindingInput(BaseModel):
    finding_category: str
    severity: str
    confidence_score: float = Field(ge=0.0, le=1.0)
    barcode_value: str = ""
    qr_code_value: str = ""
    key_dot_value: str = ""
    baseline_status: str = ""
    instrument_match_status: str = ""


class CompositeRankingRequest(BaseModel):
    instrument_id: int | None = None
    instrument_name: str = ""
    findings: list[CompositeFindingInput] = Field(min_length=1)
    tenant_id: str = "default-tenant"


class FindingDetail(BaseModel):
    category: str
    severity: str
    score_deduction: int
    rationale: str


class AuditEvidence(BaseModel):
    ranking_mode: str
    baseline_review_required: bool
    final_ranking_allowed: bool
    baseline_review_reason: str
    identifier_match: dict[str, str]
    scoring_breakdown: dict[str, Any]


class RankingResult(BaseModel):
    finding_id: int | None = None
    inspection_score: int = Field(ge=0, le=100)
    risk_level: str
    baseline_match_pct: float
    findings: list[FindingDetail]
    recommended_action: str
    audit_evidence: AuditEvidence
    ranking_mode: str
    final_ranking_allowed: bool
    compound_escalation_applied: bool = False
    history_elevation_applied: bool = False
    capa_auto_triggered: bool = False


class CompositeRankingResult(BaseModel):
    instrument_id: int | None = None
    instrument_name: str
    composite_score: int = Field(ge=0, le=100)
    risk_level: str
    compound_escalation_applied: bool
    finding_results: list[RankingResult]
    recommended_action: str
    total_findings: int
    critical_findings: int


class ScoringProfileCreate(BaseModel):
    profile_name: str = "Default"
    category_weights: dict[str, int] | None = None
    severity_multipliers: dict[str, float] | None = None
    compound_escalation_threshold: int = 2
    compound_escalation_window_days: int = 90
    created_by: str = ""


class ScoringProfileResponse(BaseModel):
    id: int
    tenant_id: str
    profile_name: str
    is_active: bool
    category_weights: dict[str, int] | None
    severity_multipliers: dict[str, float] | None
    compound_escalation_threshold: int
    compound_escalation_window_days: int
    created_by: str


class RankingKPISummary(BaseModel):
    total_ranked: int
    avg_inspection_score: float
    blood_count: int
    bone_count: int
    tissue_count: int
    corrosion_count: int
    crack_count: int
    insulation_damage_count: int
    other_organic_count: int
    pitting_count: int
    missing_component_count: int
    baseline_mismatch_count: int
    baseline_mismatch_rate_pct: float
    barcode_match_count: int
    barcode_match_rate_pct: float
    qr_match_count: int
    qr_match_rate_pct: float
    key_dot_match_count: int
    key_dot_match_rate_pct: float
    critical_count: int
    high_count: int
