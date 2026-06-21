"""P15: National SPD Intelligence Network — benchmark participation models."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String

from app.db.base import Base


class NetworkParticipant(Base):
    __tablename__ = "network_participants"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(String, nullable=False, unique=True)
    pseudonym = Column(String, nullable=False)  # rotating anonymized ID
    participation_tier = Column(String, default="contributor")  # observer/contributor/full_member
    opted_in_at = Column(DateTime, default=datetime.utcnow)
    opted_out_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    facility_type = Column(String, default="hospital")  # hospital/health_system/asc
    bed_count_range = Column(String, nullable=True)  # "100-299", "300-499", "500+" (never exact)
    region = Column(String, nullable=True)  # "northeast", "southeast", "midwest", "west"


class IndustryBenchmark(Base):
    __tablename__ = "industry_benchmarks"

    id = Column(Integer, primary_key=True)
    benchmark_date = Column(DateTime, default=datetime.utcnow)
    period = Column(String, default="monthly")  # monthly/quarterly/annual
    metric_name = Column(String, nullable=False)
    cohort = Column(String, default="all")  # all/hospital/health_system/asc/region
    cohort_value = Column(String, nullable=True)  # e.g., "northeast" for region cohort
    n_facilities = Column(Integer, nullable=False)  # must be >= 5
    p25 = Column(Float, nullable=False)
    p50 = Column(Float, nullable=False)
    p75 = Column(Float, nullable=False)
    p90 = Column(Float, nullable=False)
    mean = Column(Float, nullable=False)
    noise_added = Column(Boolean, default=True)  # always true — Laplace noise applied
