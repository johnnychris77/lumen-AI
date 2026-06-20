"""P5: Enterprise Multi-Hospital Benchmarking & Portfolio Intelligence — data models."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, Integer, String, Text

from app.db.base import Base


class HospitalBenchmark(Base):
    """Aggregated per-hospital inspection quality metrics.

    One row per (tenant_id, hospital_id, period_start, period_end).
    Populated by the benchmark engine on demand and on schedule.
    """
    __tablename__ = "hospital_benchmarks"

    id = Column(Integer, primary_key=True, index=True)

    # Identity
    tenant_id = Column(String(100), nullable=False, index=True, default="default-tenant")
    hospital_id = Column(String(100), nullable=False, index=True)
    hospital_name = Column(String(255), nullable=False, default="")
    region = Column(String(100), nullable=False, default="")
    facility_type = Column(String(100), nullable=False, default="hospital")

    # Period
    period_type = Column(String(20), nullable=False, default="monthly")   # monthly | quarterly | annual
    period_label = Column(String(20), nullable=False, default="")         # "2025-Q1" | "2025-06"
    period_start = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    period_end = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    # Volume
    total_inspections = Column(Integer, default=0, nullable=False)
    total_instruments_inspected = Column(Integer, default=0, nullable=False)
    cv_analyses_run = Column(Integer, default=0, nullable=False)

    # Contamination
    contamination_rate_pct = Column(Float, default=0.0, nullable=False)
    blood_finding_count = Column(Integer, default=0, nullable=False)
    bone_finding_count = Column(Integer, default=0, nullable=False)
    tissue_finding_count = Column(Integer, default=0, nullable=False)
    residue_finding_count = Column(Integer, default=0, nullable=False)
    avg_contamination_score = Column(Float, default=100.0, nullable=False)

    # Damage
    damage_rate_pct = Column(Float, default=0.0, nullable=False)
    corrosion_finding_count = Column(Integer, default=0, nullable=False)
    crack_finding_count = Column(Integer, default=0, nullable=False)
    insulation_finding_count = Column(Integer, default=0, nullable=False)
    avg_damage_score = Column(Float, default=100.0, nullable=False)

    # Cleanliness
    avg_cleanliness_score = Column(Float, default=100.0, nullable=False)
    pct_instruments_clean = Column(Float, default=100.0, nullable=False)   # % with score >= 80

    # Baseline
    baseline_match_rate_pct = Column(Float, default=0.0, nullable=False)
    avg_baseline_match_pct = Column(Float, default=0.0, nullable=False)
    baseline_comparisons_run = Column(Integer, default=0, nullable=False)
    baseline_pass_count = Column(Integer, default=0, nullable=False)
    baseline_fail_count = Column(Integer, default=0, nullable=False)

    # Recognition
    instrument_recognition_rate_pct = Column(Float, default=0.0, nullable=False)

    # Compliance composite (0-100 — derived from weighted sub-scores)
    compliance_score = Column(Float, default=0.0, nullable=False)

    # Ranking within portfolio (populated by rollup)
    portfolio_rank = Column(Integer, default=0, nullable=False)
    risk_tier = Column(String(20), nullable=False, default="low")   # low | medium | high | critical

    computed_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))


class VendorBenchmark(Base):
    """Aggregated per-vendor quality and baseline adoption metrics."""
    __tablename__ = "vendor_benchmarks"

    id = Column(Integer, primary_key=True, index=True)

    # Identity
    tenant_id = Column(String(100), nullable=False, index=True, default="default-tenant")
    vendor_id = Column(String(100), nullable=False, index=True)
    vendor_name = Column(String(255), nullable=False, default="")
    vendor_type = Column(String(100), nullable=False, default="medical_device")

    # Period
    period_type = Column(String(20), nullable=False, default="monthly")
    period_label = Column(String(20), nullable=False, default="")
    period_start = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    period_end = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    # Baseline
    baselines_submitted = Column(Integer, default=0, nullable=False)
    baselines_approved = Column(Integer, default=0, nullable=False)
    baselines_pending = Column(Integer, default=0, nullable=False)
    baselines_rejected = Column(Integer, default=0, nullable=False)
    baseline_adoption_rate_pct = Column(Float, default=0.0, nullable=False)   # approved / total instruments
    baseline_approval_rate_pct = Column(Float, default=0.0, nullable=False)   # approved / submitted

    # Defects
    total_findings = Column(Integer, default=0, nullable=False)
    defect_rate_pct = Column(Float, default=0.0, nullable=False)
    critical_finding_count = Column(Integer, default=0, nullable=False)
    high_finding_count = Column(Integer, default=0, nullable=False)
    avg_finding_confidence = Column(Float, default=0.0, nullable=False)
    blood_finding_count = Column(Integer, default=0, nullable=False)
    contamination_finding_count = Column(Integer, default=0, nullable=False)

    # CAPA
    open_capas = Column(Integer, default=0, nullable=False)
    closed_capas = Column(Integer, default=0, nullable=False)
    overdue_capas = Column(Integer, default=0, nullable=False)
    capa_closure_rate_pct = Column(Float, default=0.0, nullable=False)

    # Performance
    vendor_score = Column(Float, default=0.0, nullable=False)   # 0-100 composite
    portfolio_rank = Column(Integer, default=0, nullable=False)
    risk_tier = Column(String(20), nullable=False, default="low")

    computed_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))


class EnterpriseRollup(Base):
    """Cross-hospital enterprise summary for executive reporting."""
    __tablename__ = "enterprise_rollups"

    id = Column(Integer, primary_key=True, index=True)

    tenant_id = Column(String(100), nullable=False, index=True, default="default-tenant")
    period_type = Column(String(20), nullable=False, default="monthly")
    period_label = Column(String(20), nullable=False, default="")
    period_start = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    period_end = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    # Volume
    total_hospitals = Column(Integer, default=0, nullable=False)
    total_inspections = Column(Integer, default=0, nullable=False)
    total_cv_analyses = Column(Integer, default=0, nullable=False)
    total_instruments = Column(Integer, default=0, nullable=False)

    # Quality
    avg_cleanliness_score = Column(Float, default=100.0, nullable=False)
    avg_contamination_rate_pct = Column(Float, default=0.0, nullable=False)
    avg_baseline_match_pct = Column(Float, default=0.0, nullable=False)
    total_blood_findings = Column(Integer, default=0, nullable=False)
    total_critical_findings = Column(Integer, default=0, nullable=False)
    pct_hospitals_compliant = Column(Float, default=100.0, nullable=False)  # compliance_score >= 80

    # Baseline
    baseline_adoption_rate_pct = Column(Float, default=0.0, nullable=False)

    # Vendor
    total_vendors = Column(Integer, default=0, nullable=False)
    avg_vendor_score = Column(Float, default=0.0, nullable=False)

    # Risk distribution
    hospitals_low_risk = Column(Integer, default=0, nullable=False)
    hospitals_medium_risk = Column(Integer, default=0, nullable=False)
    hospitals_high_risk = Column(Integer, default=0, nullable=False)
    hospitals_critical_risk = Column(Integer, default=0, nullable=False)

    # Top / bottom performers (JSON arrays stored as text)
    top_hospitals_json = Column(Text, default="[]", nullable=False)       # [{hospital_id, name, score}]
    bottom_hospitals_json = Column(Text, default="[]", nullable=False)
    top_vendors_json = Column(Text, default="[]", nullable=False)
    bottom_vendors_json = Column(Text, default="[]", nullable=False)

    computed_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))


class BenchmarkTrendPoint(Base):
    """Single metric data point in a time-series trend.

    Used to build trend charts: contamination over months,
    baseline adoption improvement, etc.
    """
    __tablename__ = "benchmark_trend_points"

    id = Column(Integer, primary_key=True, index=True)

    tenant_id = Column(String(100), nullable=False, index=True, default="default-tenant")
    subject_type = Column(String(20), nullable=False, index=True)   # "hospital" | "vendor" | "enterprise"
    subject_id = Column(String(100), nullable=False, index=True)    # hospital_id / vendor_id / "all"
    metric_name = Column(String(100), nullable=False, index=True)   # "contamination_rate_pct", etc.
    period_label = Column(String(20), nullable=False, index=True)
    period_start = Column(DateTime, nullable=False)
    value = Column(Float, nullable=False, default=0.0)

    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))


class BoardReport(Base):
    """Generated board / executive report metadata."""
    __tablename__ = "board_reports"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(100), nullable=False, index=True, default="default-tenant")
    report_type = Column(String(50), nullable=False, default="monthly")   # monthly | quarterly | annual
    period_label = Column(String(20), nullable=False, default="")
    title = Column(String(255), nullable=False, default="")
    executive_summary = Column(Text, default="", nullable=False)
    key_findings_json = Column(Text, default="[]", nullable=False)
    recommendations_json = Column(Text, default="[]", nullable=False)
    rollup_id = Column(Integer, nullable=True, index=True)
    generated_by = Column(String(100), nullable=False, default="system")
    status = Column(String(30), nullable=False, default="draft")   # draft | published | archived
    published_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
