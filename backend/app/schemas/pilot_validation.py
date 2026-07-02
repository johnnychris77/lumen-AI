"""Phase 18 — Pilot Validation Pydantic schemas."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class PilotValidationCaseCreate(BaseModel):
    inspection_id: Optional[int] = None
    instrument_family: str = ""
    manufacturer: str = ""
    model: str = ""
    anatomy_zone: str = ""
    baseline_source: str = "none"
    has_baseline: bool = False

    finding_type: str = "none"
    severity: str = "none"

    ai_prediction: Optional[bool] = None
    ai_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    ai_recommended_disposition: str = ""

    supervisor_finding: Optional[bool] = None
    supervisor_zone_correction: str = ""
    reviewer_name: str = ""
    reviewer_rationale: str = ""
    final_disposition: str = ""

    dataset_version: str = "pilot-v1"
    model_version: str = ""


class PilotValidationCaseResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tenant_id: str
    inspection_id: Optional[int]
    instrument_family: str
    manufacturer: str
    model: str
    anatomy_zone: str
    baseline_source: str
    has_baseline: bool
    finding_type: str
    severity: str
    disposition: str
    ai_prediction: Optional[bool]
    ai_confidence: float
    supervisor_finding: Optional[bool]
    supervisor_zone_correction: str
    reviewer_name: str
    reviewer_rationale: str
    ground_truth_label: str
    is_critical_finding: bool
    dataset_version: str
    model_version: str
    created_at: str
