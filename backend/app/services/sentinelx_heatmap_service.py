"""Project Sentinel-X, Section 6: Enterprise Risk Heatmaps.

Pure aggregation over already-persisted `SentinelXRiskAssessment` rows --
zero new tables, no fabricated distribution.
"""
from __future__ import annotations

from collections import defaultdict

from sqlalchemy.orm import Session

from app.models.sentinelx_risk import SentinelXRiskAssessment

_DIMENSIONS = {
    "facility": "facility_name",
    "department": "department",
    "instrument_family": "instrument_family",
    "anatomy": "anatomy_zone",
    "manufacturer": "manufacturer_name",
    "service_line": "service_line",
}


def _bucket(rows: list[SentinelXRiskAssessment], attr: str) -> list[dict]:
    grouped: dict[str, list[float]] = defaultdict(list)
    for r in rows:
        key = getattr(r, attr) or "unspecified"
        grouped[key].append(r.risk_score)
    return sorted(
        ({"key": k, "count": len(v), "average_risk_score": round(sum(v) / len(v), 1)} for k, v in grouped.items()),
        key=lambda x: x["average_risk_score"], reverse=True,
    )


def risk_heatmap(db: Session, tenant_id: str, dimension: str) -> list[dict] | None:
    attr = _DIMENSIONS.get(dimension)
    if attr is None:
        return None
    rows = db.query(SentinelXRiskAssessment).filter(SentinelXRiskAssessment.tenant_id == tenant_id).all()
    return _bucket(rows, attr)


def all_heatmaps(db: Session, tenant_id: str) -> dict:
    rows = db.query(SentinelXRiskAssessment).filter(SentinelXRiskAssessment.tenant_id == tenant_id).all()
    return {dimension: _bucket(rows, attr) for dimension, attr in _DIMENSIONS.items()}
