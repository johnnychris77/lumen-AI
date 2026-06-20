"""P5: Pydantic schemas for Enterprise Benchmarking & Portfolio Intelligence."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from pydantic import BaseModel, Field


# ── Input / request schemas ───────────────────────────────────────────────────

class BenchmarkPeriod(BaseModel):
    period_type: Literal["monthly", "quarterly", "annual"] = "monthly"
    period_label: str = ""          # e.g. "2025-06", "2025-Q2" — auto-derived if empty


class HospitalBenchmarkRequest(BaseModel):
    tenant_id: str = "default-tenant"
    hospital_ids: list[str] = Field(default_factory=list)   # empty = all hospitals
    period: BenchmarkPeriod = Field(default_factory=BenchmarkPeriod)
    force_recompute: bool = False


class VendorBenchmarkRequest(BaseModel):
    tenant_id: str = "default-tenant"
    vendor_ids: list[str] = Field(default_factory=list)     # empty = all vendors
    period: BenchmarkPeriod = Field(default_factory=BenchmarkPeriod)
    force_recompute: bool = False


class EnterpriseRollupRequest(BaseModel):
    tenant_id: str = "default-tenant"
    period: BenchmarkPeriod = Field(default_factory=BenchmarkPeriod)
    force_recompute: bool = False


class BoardReportRequest(BaseModel):
    tenant_id: str = "default-tenant"
    report_type: Literal["monthly", "quarterly", "annual"] = "monthly"
    period_label: str = ""
    publish: bool = False


# ── Output schemas ────────────────────────────────────────────────────────────

class HospitalBenchmarkResult(BaseModel):
    hospital_id: str
    hospital_name: str
    region: str = ""
    facility_type: str = "hospital"
    period_label: str

    # Volume
    total_inspections: int = 0
    cv_analyses_run: int = 0

    # Contamination
    contamination_rate_pct: float = 0.0
    blood_finding_count: int = 0
    bone_finding_count: int = 0
    tissue_finding_count: int = 0
    avg_contamination_score: float = 100.0

    # Damage
    damage_rate_pct: float = 0.0
    avg_damage_score: float = 100.0

    # Cleanliness
    avg_cleanliness_score: float = 100.0
    pct_instruments_clean: float = 100.0

    # Baseline
    baseline_match_rate_pct: float = 0.0
    avg_baseline_match_pct: float = 0.0
    baseline_pass_count: int = 0
    baseline_fail_count: int = 0

    # Recognition
    instrument_recognition_rate_pct: float = 0.0

    # Composite
    compliance_score: float = 0.0
    portfolio_rank: int = 0
    risk_tier: str = "low"

    computed_at: datetime | None = None


class VendorBenchmarkResult(BaseModel):
    vendor_id: str
    vendor_name: str
    vendor_type: str = "medical_device"
    period_label: str

    # Baseline
    baselines_submitted: int = 0
    baselines_approved: int = 0
    baseline_adoption_rate_pct: float = 0.0
    baseline_approval_rate_pct: float = 0.0

    # Defects
    total_findings: int = 0
    defect_rate_pct: float = 0.0
    critical_finding_count: int = 0
    blood_finding_count: int = 0

    # CAPA
    open_capas: int = 0
    closed_capas: int = 0
    capa_closure_rate_pct: float = 0.0

    # Composite
    vendor_score: float = 0.0
    portfolio_rank: int = 0
    risk_tier: str = "low"

    computed_at: datetime | None = None


class EnterpriseRollupResult(BaseModel):
    tenant_id: str
    period_label: str
    period_type: str

    # Volume
    total_hospitals: int = 0
    total_inspections: int = 0
    total_cv_analyses: int = 0
    total_instruments: int = 0

    # Quality
    avg_cleanliness_score: float = 100.0
    avg_contamination_rate_pct: float = 0.0
    avg_baseline_match_pct: float = 0.0
    total_blood_findings: int = 0
    total_critical_findings: int = 0
    pct_hospitals_compliant: float = 100.0
    baseline_adoption_rate_pct: float = 0.0

    # Vendor
    total_vendors: int = 0
    avg_vendor_score: float = 0.0

    # Risk distribution
    hospitals_low_risk: int = 0
    hospitals_medium_risk: int = 0
    hospitals_high_risk: int = 0
    hospitals_critical_risk: int = 0

    # Leaderboards
    top_hospitals: list[dict[str, Any]] = Field(default_factory=list)
    bottom_hospitals: list[dict[str, Any]] = Field(default_factory=list)
    top_vendors: list[dict[str, Any]] = Field(default_factory=list)
    bottom_vendors: list[dict[str, Any]] = Field(default_factory=list)

    # data_source indicates whether these numbers are from real inspection records
    # or from the seeded mock generator. Callers should surface "No data yet" UX
    # when data_source == "mock" rather than presenting fabricated numbers as real.
    data_source: str = "real"   # "real" | "mock" | "insufficient"

    computed_at: datetime | None = None


class TrendPoint(BaseModel):
    period_label: str
    period_start: datetime
    value: float


class TrendSeries(BaseModel):
    subject_id: str
    subject_name: str
    metric_name: str
    points: list[TrendPoint]


class ExecutiveDashboard(BaseModel):
    """Single-payload executive view for C-suite / Market Directors."""
    tenant_id: str
    generated_at: datetime
    period_label: str
    data_source: str = "real"   # "real" | "mock" | "insufficient"

    # Headline numbers
    total_hospitals: int = 0
    total_inspections_mtd: int = 0
    portfolio_cleanliness_score: float = 100.0
    blood_detections_mtd: int = 0
    baseline_adoption_rate_pct: float = 0.0
    pct_hospitals_compliant: float = 100.0

    # Risk snapshot
    hospitals_at_critical_risk: int = 0
    hospitals_at_high_risk: int = 0
    open_critical_capas: int = 0

    # Trend direction (vs prior period)
    cleanliness_score_delta: float = 0.0   # positive = improvement
    contamination_rate_delta: float = 0.0  # positive = more contamination (bad)
    baseline_adoption_delta: float = 0.0

    # Leaderboards
    top_performing_hospitals: list[dict[str, Any]] = Field(default_factory=list)
    highest_risk_hospitals: list[dict[str, Any]] = Field(default_factory=list)
    top_vendors: list[dict[str, Any]] = Field(default_factory=list)
    lowest_vendors: list[dict[str, Any]] = Field(default_factory=list)

    # Trend series (last 6 periods)
    contamination_trend: list[TrendPoint] = Field(default_factory=list)
    cleanliness_trend: list[TrendPoint] = Field(default_factory=list)
    baseline_adoption_trend: list[TrendPoint] = Field(default_factory=list)

    # Role-specific insights
    spd_director_insights: list[str] = Field(default_factory=list)
    quality_leader_insights: list[str] = Field(default_factory=list)
    market_director_insights: list[str] = Field(default_factory=list)


class BoardReportResult(BaseModel):
    id: int | None = None
    tenant_id: str
    report_type: str
    period_label: str
    title: str
    executive_summary: str
    key_findings: list[str]
    recommendations: list[str]
    status: str = "draft"
    generated_by: str = "system"
    published_at: datetime | None = None
    created_at: datetime | None = None
    rollup: EnterpriseRollupResult | None = None
