"""Pydantic schemas for the Inspection Ranking Engine."""
from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field


class RankingRequest(BaseModel):
    finding_id: int | None = None
    finding_category: str
    severity: str
    confidence_score: float = Field(ge=0.0, le=1.0)
    instrument_name: str = ""
    instrument_category: str = ""
    barcode_value: str = ""
    qr_code_value: str = ""
    key_dot_value: str = ""
    baseline_status: str = ""
    instrument_match_status: str = ""
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
