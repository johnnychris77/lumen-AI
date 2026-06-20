"""P12 Clinical Validation — API routes for FP/FN analysis and validation reports."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.deps import get_db
from app.enterprise_auth import require_enterprise_auth
from app.models.validation import ValidationCase
from app.schemas.validation import ValidationCaseCreate
from app.services.validation_engine import (
    FINDING_CATEGORIES,
    compute_validation_report,
    list_validation_cases,
)

router = APIRouter(prefix="/api/validation", tags=["validation"])


@router.post("/cases")
def submit_validation_case(
    payload: ValidationCaseCreate,
    request: Request,
    db: Session = Depends(get_db),
) -> dict:
    """Submit a labeled validation case."""
    auth = require_enterprise_auth(request, db=db)
    tenant_id = auth.tenant_id

    case = ValidationCase(
        tenant_id=tenant_id,
        case_ref=payload.case_ref,
        instrument_category=payload.instrument_category,
        finding_category=payload.finding_category,
        ground_truth=payload.ground_truth,
        ai_prediction=payload.ai_prediction,
        ai_confidence=payload.ai_confidence,
        human_prediction=payload.human_prediction,
        reader_role=payload.reader_role,
        is_critical=payload.is_critical,
        notes=payload.notes,
    )
    db.add(case)
    db.commit()
    db.refresh(case)

    return {
        "id": case.id,
        "tenant_id": case.tenant_id,
        "case_ref": case.case_ref,
        "instrument_category": case.instrument_category,
        "finding_category": case.finding_category,
        "ground_truth": case.ground_truth,
        "ai_prediction": case.ai_prediction,
        "ai_confidence": case.ai_confidence,
        "human_prediction": case.human_prediction,
        "reader_role": case.reader_role,
        "is_critical": case.is_critical,
        "notes": case.notes,
        "created_at": case.created_at.isoformat() if case.created_at else "",
    }


@router.get("/cases")
def list_cases(
    request: Request,
    finding_category: Optional[str] = "",
    limit: int = 100,
    db: Session = Depends(get_db),
) -> dict:
    """List validation cases for the authenticated tenant."""
    auth = require_enterprise_auth(request, db=db)
    tenant_id = auth.tenant_id

    cases = list_validation_cases(
        tenant_id=tenant_id,
        finding_category=finding_category or "",
        limit=limit,
        db=db,
    )

    return {
        "tenant_id": tenant_id,
        "count": len(cases),
        "cases": [
            {
                "id": c.id,
                "tenant_id": c.tenant_id,
                "case_ref": c.case_ref,
                "instrument_category": c.instrument_category,
                "finding_category": c.finding_category,
                "ground_truth": c.ground_truth,
                "ai_prediction": c.ai_prediction,
                "ai_confidence": c.ai_confidence,
                "human_prediction": c.human_prediction,
                "reader_role": c.reader_role,
                "is_critical": c.is_critical,
                "notes": c.notes,
                "created_at": c.created_at.isoformat() if c.created_at else "",
            }
            for c in cases
        ],
    }


@router.get("/report")
def get_validation_report(
    request: Request,
    run_label: str = "mock-run",
    db: Session = Depends(get_db),
) -> dict:
    """Compute full validation report with per-category FP/FN analysis."""
    auth = require_enterprise_auth(request, db=db)
    tenant_id = auth.tenant_id

    report = compute_validation_report(
        tenant_id=tenant_id,
        run_label=run_label,
        db=db,
    )
    return report


@router.get("/report/{finding_category}")
def get_category_report(
    finding_category: str,
    request: Request,
    run_label: str = "mock-run",
    db: Session = Depends(get_db),
) -> dict:
    """Per-category FP/FN breakdown for a specific finding category."""
    auth = require_enterprise_auth(request, db=db)
    tenant_id = auth.tenant_id

    report = compute_validation_report(
        tenant_id=tenant_id,
        run_label=run_label,
        db=db,
    )

    # Find the requested category in by_category
    for cat_result in report.get("by_category", []):
        if cat_result["finding_category"] == finding_category:
            return cat_result

    # If not found, return a minimal response
    return {
        "finding_category": finding_category,
        "is_critical": finding_category in {"crack", "corrosion", "insulation"},
        "ai_metrics": {},
        "human_metrics": None,
        "kappa": 0.0,
        "confidence_interval_95": {},
        "data_source": "mock",
    }


@router.get("/categories")
def list_categories(
    request: Request,
) -> list:
    """List all supported finding categories."""
    require_enterprise_auth(request)
    return FINDING_CATEGORIES
