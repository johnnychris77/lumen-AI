"""P12 Clinical Validation — Pydantic schemas."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict


class ValidationCaseCreate(BaseModel):
    case_ref: str
    instrument_category: str
    finding_category: str
    ground_truth: bool
    ai_prediction: Optional[bool] = None
    ai_confidence: float = 0.0
    human_prediction: Optional[bool] = None
    reader_role: str = ""
    is_critical: bool = False
    notes: str = ""


class ValidationCaseResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tenant_id: str
    case_ref: str
    instrument_category: str
    finding_category: str
    ground_truth: bool
    ai_prediction: Optional[bool]
    ai_confidence: float
    human_prediction: Optional[bool]
    reader_role: str
    is_critical: bool
    notes: str
    created_at: str


class ConfusionMatrix(BaseModel):
    tp: int = 0
    tn: int = 0
    fp: int = 0
    fn: int = 0
    precision: float = 0.0
    recall: float = 0.0
    specificity: float = 0.0
    f1: float = 0.0
    accuracy: float = 0.0
    false_positive_rate: float = 0.0
    false_negative_rate: float = 0.0
    case_count: int = 0


class CategoryValidationResult(BaseModel):
    finding_category: str
    is_critical: bool
    ai_metrics: ConfusionMatrix
    human_metrics: Optional[ConfusionMatrix] = None
    kappa: float = 0.0
    confidence_interval_95: dict = {}  # {"lower": float, "upper": float}


class ValidationReportResult(BaseModel):
    tenant_id: str
    run_label: str
    generated_at: str
    data_source: str
    overall_accuracy: float
    overall_precision: float
    overall_recall: float
    overall_f1: float
    overall_kappa: float
    critical_finding_fn_rate: float
    meets_primary_endpoint: bool  # kappa >= 0.80
    meets_safety_endpoint: bool  # critical FN rate <= 2%
    by_category: list[CategoryValidationResult]
    recommendations: list[str]


class ValidationRunResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tenant_id: str
    run_label: str
    finding_category: str
    reader_type: str
    tp: int
    tn: int
    fp: int
    fn: int
    precision: float
    recall: float
    specificity: float
    f1: float
    kappa: float
    auc: float
    case_count: int
    data_source: str
    run_at: str
