"""P6: Vendor Intelligence Exchange — Pydantic request/response schemas."""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel


# ── Vendor Scorecard ──────────────────────────────────────────────────────────

class VendorScorecardResult(BaseModel):
    vendor_id: str
    vendor_name: str
    tenant_id: str
    period_label: str
    period_type: str
    baseline_adoption_rate_pct: float
    baseline_approval_rate_pct: float
    defect_rate_pct: float
    contamination_recurrence_rate_pct: float
    capa_avg_response_days: float
    capa_closure_rate_pct: float
    inspection_failure_rate_pct: float
    composite_score: float
    risk_tier: str
    portfolio_rank: int
    computed_at: str
    data_source: str = "mock"


class VendorTrendPoint(BaseModel):
    period_label: str
    total_defects: int
    critical_defects: int
    blood_findings: int
    defect_rate_pct: float
    trend_direction: str


class VendorTrendResult(BaseModel):
    vendor_id: str
    vendor_name: str
    tenant_id: str
    period_type: str
    trend_points: List[VendorTrendPoint]
    data_source: str = "mock"


# ── Manufacturer Scorecard ────────────────────────────────────────────────────

class ManufacturerScorecardResult(BaseModel):
    manufacturer_id: str
    manufacturer_name: str
    tenant_id: str
    period_label: str
    period_type: str
    baseline_quality_score: float
    baseline_adoption_rate_pct: float
    inspection_pass_rate_pct: float
    contamination_recurrence_rate_pct: float
    instrument_defect_frequency: float
    recall_count: int
    capa_effectiveness_score: float
    composite_score: float
    risk_tier: str
    portfolio_rank: int
    computed_at: str
    data_source: str = "mock"


class ManufacturerTrendPoint(BaseModel):
    period_label: str
    total_defects: int
    critical_defects: int
    trend_direction: str


class ManufacturerTrendResult(BaseModel):
    manufacturer_id: str
    manufacturer_name: str
    tenant_id: str
    period_type: str
    trend_points: List[ManufacturerTrendPoint]
    data_source: str = "mock"


# ── Shared Defect Signals ─────────────────────────────────────────────────────

class SharedDefectSignalResult(BaseModel):
    id: int
    signal_type: str
    instrument_category: str
    finding_category: str
    occurrence_count: int
    severity: str
    confidence_score: float
    first_seen_period: str
    last_seen_period: str
    is_active: bool


# ── Instrument Risk Patterns ──────────────────────────────────────────────────

class InstrumentRiskPatternResult(BaseModel):
    id: int
    instrument_category: str
    pattern_type: str
    risk_score: float
    occurrence_rate_pct: float
    hospital_count_affected: int   # anonymized count, never IDs
    description: str
    recommended_action: str
    detected_at: str
    is_active: bool


# ── Recall ────────────────────────────────────────────────────────────────────

class RecallEventResult(BaseModel):
    id: int
    tenant_id: str
    vendor_id: str
    manufacturer_id: Optional[str]
    recall_number: str
    recall_title: str
    recall_description: str
    affected_instrument_categories: List[str]
    severity: str
    recall_date: str
    resolution_date: Optional[str]
    status: str
    source: str
    source_url: str
    created_at: str


class RecallImpactResult(BaseModel):
    recall_event_id: int
    tenant_id: str
    affected_instruments_count: int
    affected_hospitals_count: int   # anonymized
    risk_level: str
    assessment_notes: str
    assessed_by: str
    assessed_at: str


# ── CAPA Effectiveness ────────────────────────────────────────────────────────

class CapaEffectivenessResult(BaseModel):
    tenant_id: str
    period_label: str
    total_capas: int
    open_capas: int
    closed_capas: int
    overdue_capas: int
    closure_rate_pct: float
    avg_closure_days: float
    on_time_closure_rate_pct: float
    recurrence_rate_pct: float
    effectiveness_score: float   # 0-100 composite
    data_source: str = "mock"


# ── Intelligence Dashboard ────────────────────────────────────────────────────

class IntelligenceDashboard(BaseModel):
    tenant_id: str
    period_label: str
    period_type: str
    generated_at: str
    data_source: str = "mock"

    # Vendor summary
    total_vendors_scored: int
    avg_vendor_composite_score: float
    top_vendor: Optional[VendorScorecardResult]
    bottom_vendor: Optional[VendorScorecardResult]
    vendors_at_high_risk: int
    vendors_at_critical_risk: int

    # Manufacturer summary
    total_manufacturers_scored: int
    avg_manufacturer_composite_score: float
    top_manufacturer: Optional[ManufacturerScorecardResult]
    bottom_manufacturer: Optional[ManufacturerScorecardResult]

    # Shared intelligence
    active_shared_defect_signals: int
    active_recalls: int
    critical_recalls: int

    # CAPA
    capa_effectiveness: CapaEffectivenessResult

    # Top-level scorecards
    vendor_scorecards: List[VendorScorecardResult]
    manufacturer_scorecards: List[ManufacturerScorecardResult]
    shared_defect_signals: List[SharedDefectSignalResult]
    instrument_risk_patterns: List[InstrumentRiskPatternResult]
    recall_events: List[RecallEventResult]
