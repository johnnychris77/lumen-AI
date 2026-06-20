"""Inspection Ranking Engine API routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.deps import get_db
from app.models.enterprise_quality import EnterpriseFinding, EnterpriseRiskScore
from app.schemas.ranking import RankingKPISummary, RankingRequest, RankingResult
from app.services.ranking_engine import score_inspection

router = APIRouter(prefix="/api/enterprise/ranking", tags=["ranking"])


@router.post("/score", response_model=RankingResult)
def compute_ranking_score(req: RankingRequest, db: Session = Depends(get_db)):
    """Compute inspection ranking score for a finding."""
    result = score_inspection(req)

    # Persist updated overall_score and risk_tier back to EnterpriseRiskScore if linked
    if req.finding_id:
        risk_row = (
            db.query(EnterpriseRiskScore)
            .filter(EnterpriseRiskScore.finding_id == req.finding_id)
            .first()
        )
        if risk_row:
            risk_row.overall_score = result.inspection_score
            risk_row.risk_tier = result.risk_level.lower()
            db.commit()

    return result


@router.get("/history/{finding_id}", response_model=RankingResult)
def get_ranking_for_finding(finding_id: int, db: Session = Depends(get_db)):
    """Re-compute ranking for an existing finding from stored data."""
    finding = db.query(EnterpriseFinding).filter(EnterpriseFinding.id == finding_id).first()
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found")

    risk_row = (
        db.query(EnterpriseRiskScore)
        .filter(EnterpriseRiskScore.finding_id == finding_id)
        .first()
    )

    req = RankingRequest(
        finding_id=finding_id,
        finding_category=finding.finding_category,
        severity=finding.severity,
        confidence_score=finding.confidence_score,
        tenant_id=finding.tenant_id,
        baseline_status=risk_row.risk_tier if risk_row else "",
    )
    return score_inspection(req)


@router.get("/kpi-summary", response_model=RankingKPISummary)
def ranking_kpi_summary(tenant_id: str = "demo-tenant", db: Session = Depends(get_db)):
    """KPI summary for the ranking engine dashboard tile."""
    findings = (
        db.query(EnterpriseFinding)
        .filter(EnterpriseFinding.tenant_id == tenant_id)
        .all()
    )

    total = len(findings)
    scores: list[int] = []
    blood = bone = tissue = corrosion = crack = insulation = other_organic = 0
    pitting = missing = baseline_mismatch = 0
    barcode_match = qr_match = key_dot_match = 0
    critical_count = high_count = 0

    for f in findings:
        cat = f.finding_category.lower()
        sev = f.severity.lower()
        if "blood" in cat:
            blood += 1
        elif "bone" in cat:
            bone += 1
        elif "tissue" in cat:
            tissue += 1
        elif "corrosion" in cat:
            corrosion += 1
        elif "crack" in cat:
            crack += 1
        elif "insulation" in cat:
            insulation += 1
        elif "pitting" in cat:
            pitting += 1
        elif "missing" in cat:
            missing += 1
        elif "organic" in cat or "bioburden" in cat:
            other_organic += 1

        if "baseline mismatch" in cat:
            baseline_mismatch += 1

        if sev == "critical":
            critical_count += 1
        elif sev == "high":
            high_count += 1

        # Compute score and accumulate
        req = RankingRequest(
            finding_id=f.id,
            finding_category=f.finding_category,
            severity=f.severity,
            confidence_score=f.confidence_score,
            tenant_id=f.tenant_id,
        )
        result = score_inspection(req)
        scores.append(result.inspection_score)

    avg_score = round(sum(scores) / total, 1) if total else 0.0

    # Identifier match stats require vendor baseline data — approximate via risk scores
    risk_rows = (
        db.query(EnterpriseRiskScore)
        .filter(EnterpriseRiskScore.tenant_id == tenant_id)
        .all()
    )
    for r in risk_rows:
        if r.risk_tier in {"low", "medium"}:
            barcode_match += 1
            qr_match += 1

    def _pct(n: int) -> float:
        return round(n / total * 100, 1) if total else 0.0

    return RankingKPISummary(
        total_ranked=total,
        avg_inspection_score=avg_score,
        blood_count=blood,
        bone_count=bone,
        tissue_count=tissue,
        corrosion_count=corrosion,
        crack_count=crack,
        insulation_damage_count=insulation,
        other_organic_count=other_organic,
        pitting_count=pitting,
        missing_component_count=missing,
        baseline_mismatch_count=baseline_mismatch,
        baseline_mismatch_rate_pct=_pct(baseline_mismatch),
        barcode_match_count=barcode_match,
        barcode_match_rate_pct=_pct(barcode_match),
        qr_match_count=qr_match,
        qr_match_rate_pct=_pct(qr_match),
        key_dot_match_count=key_dot_match,
        key_dot_match_rate_pct=0.0,
        critical_count=critical_count,
        high_count=high_count,
    )
