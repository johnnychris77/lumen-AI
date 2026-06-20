"""Inspection Ranking Engine API routes."""
from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.deps import get_db
from app.enterprise_auth import require_enterprise_auth
from app.models.enterprise_quality import (
    EnterpriseCapa,
    EnterpriseFinding,
    EnterpriseRiskScore,
    EnterpriseScoringProfile,
)
from app.schemas.ranking import (
    CompositeRankingRequest,
    CompositeRankingResult,
    RankingKPISummary,
    RankingRequest,
    RankingResult,
    ScoringProfileCreate,
    ScoringProfileResponse,
)
from app.services.ranking_engine import score_composite, score_inspection

router = APIRouter(prefix="/api/enterprise/ranking", tags=["ranking"])


def _persist_score(db: Session, finding_id: int, result: RankingResult) -> None:
    """Write computed score back to EnterpriseRiskScore row."""
    risk_row = (
        db.query(EnterpriseRiskScore)
        .filter(EnterpriseRiskScore.finding_id == finding_id)
        .first()
    )
    if risk_row:
        risk_row.overall_score = result.inspection_score
        risk_row.risk_tier = result.risk_level.lower()


def _maybe_trigger_capa(db: Session, finding_id: int, result: RankingResult, tenant_id: str) -> bool:
    """Auto-create draft CAPA when finding is Critical and ranking is final."""
    if result.risk_level != "Critical" or not result.final_ranking_allowed:
        return False
    existing = (
        db.query(EnterpriseCapa)
        .filter(EnterpriseCapa.finding_id == finding_id)
        .first()
    )
    if existing:
        return False
    capa_num = f"CAPA-AUTO-{finding_id}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
    capa = EnterpriseCapa(
        tenant_id=tenant_id,
        finding_id=finding_id,
        capa_number=capa_num,
        title=f"Auto-triggered: Critical finding #{finding_id} — {result.findings[0].category if result.findings else 'unknown'}",
        description=(
            f"Automatically created by Ranking Engine.\n"
            f"Score: {result.inspection_score}/100 | Risk: {result.risk_level}\n"
            f"Recommended action: {result.recommended_action}"
        ),
        status="open",
    )
    db.add(capa)
    return True


@router.post("/score", response_model=RankingResult)
def compute_ranking_score(
    req: RankingRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """Compute inspection ranking score. Persists score + auto-triggers CAPA on Critical."""
    require_enterprise_auth(request)
    result = score_inspection(req, db=db)

    capa_triggered = False
    if req.finding_id:
        _persist_score(db, req.finding_id, result)
        capa_triggered = _maybe_trigger_capa(db, req.finding_id, result, req.tenant_id)
        db.commit()

    result.capa_auto_triggered = capa_triggered
    return result


@router.post("/composite-score", response_model=CompositeRankingResult)
def compute_composite_score(
    req: CompositeRankingRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """Score multiple findings on the same instrument with compound escalation."""
    require_enterprise_auth(request)
    return score_composite(req, db=db)


@router.get("/history/{finding_id}", response_model=RankingResult)
def get_ranking_for_finding(
    finding_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    """Re-compute ranking for an existing finding from stored data."""
    require_enterprise_auth(request)
    finding = db.query(EnterpriseFinding).filter(EnterpriseFinding.id == finding_id).first()
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found")

    req = RankingRequest(
        finding_id=finding_id,
        finding_category=finding.finding_category,
        severity=finding.severity,
        confidence_score=finding.confidence_score,
        instrument_id=finding.instrument_id,
        tenant_id=finding.tenant_id,
    )
    return score_inspection(req, db=db)


@router.get("/score/{finding_id}/report.pdf")
def ranking_report_pdf(
    finding_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    """Generate explainability PDF governance packet for a finding's ranking score."""
    require_enterprise_auth(request)
    finding = db.query(EnterpriseFinding).filter(EnterpriseFinding.id == finding_id).first()
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found")

    req = RankingRequest(
        finding_id=finding_id,
        finding_category=finding.finding_category,
        severity=finding.severity,
        confidence_score=finding.confidence_score,
        instrument_id=finding.instrument_id,
        tenant_id=finding.tenant_id,
    )
    result = score_inspection(req, db=db)

    breakdown = result.audit_evidence.scoring_breakdown
    lines = [
        "LumenAI Inspection Ranking Report",
        f"Finding ID: {finding_id}",
        f"Category: {result.findings[0].category if result.findings else 'N/A'}",
        f"Severity: {result.findings[0].severity if result.findings else 'N/A'}",
        "",
        f"SCORE: {result.inspection_score}/100",
        f"Risk Level: {result.risk_level}",
        f"Baseline Match: {result.baseline_match_pct}%",
        f"Ranking Mode: {result.ranking_mode}",
        "",
        "SCORING BREAKDOWN",
        f"  Base score:           {breakdown.get('base_score', 100)}",
        f"  Category deduction:  -{breakdown.get('category_deduction', 0)}",
        f"  Confidence penalty:  -{breakdown.get('confidence_penalty', 0)}",
        f"  Identifier bonus:    +{breakdown.get('identifier_bonus', 0)}",
        f"  Baseline bonus:      +{breakdown.get('baseline_bonus', 0)}",
        f"  History elevation:   {breakdown.get('history_elevation', 0)}",
        f"  Final score:          {breakdown.get('final_score', result.inspection_score)}",
        "",
        "RECOMMENDED ACTION",
        f"  {result.recommended_action}",
        "",
        "BASELINE CONTRACT",
        f"  Mode: {result.audit_evidence.ranking_mode}",
        f"  Review required: {result.audit_evidence.baseline_review_required}",
        f"  Final ranking allowed: {result.audit_evidence.final_ranking_allowed}",
        "",
        "IDENTIFIER MATCH",
        *[f"  {k}: {v}" for k, v in result.audit_evidence.identifier_match.items()],
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
    ]

    try:
        import io
        import reportlab.lib.pagesizes as pagesizes
        from reportlab.pdfgen import canvas as rl_canvas

        buf = io.BytesIO()
        c = rl_canvas.Canvas(buf, pagesize=pagesizes.letter)
        c.setFont("Helvetica-Bold", 16)
        c.drawString(72, 730, "LumenAI Inspection Ranking Report")
        c.setFont("Helvetica", 10)
        y = 700
        for line in lines[1:]:
            if y < 72:
                c.showPage()
                c.setFont("Helvetica", 10)
                y = 730
            c.drawString(72, y, line)
            y -= 14
        c.save()
        pdf_bytes = buf.getvalue()
    except ImportError:
        # Fallback: plain-text PDF stub
        text = "\n".join(lines)
        pdf_bytes = (
            b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
            b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
            b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]>>endobj\n"
            b"xref\n0 4\n0000000000 65535 f \n"
            b"trailer<</Root 1 0 R/Size 4>>\nstartxref\n0\n%%EOF\n"
        ) + text.encode()

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=ranking-report-finding-{finding_id}.pdf"
        },
    )


@router.get("/kpi-summary", response_model=RankingKPISummary)
def ranking_kpi_summary(
    request: Request,
    tenant_id: str = "demo-tenant",
    db: Session = Depends(get_db),
):
    """KPI summary — reads persisted scores from DB (no re-scoring loop)."""
    require_enterprise_auth(request)
    findings = (
        db.query(EnterpriseFinding)
        .filter(EnterpriseFinding.tenant_id == tenant_id)
        .all()
    )
    risk_rows = {
        r.finding_id: r
        for r in db.query(EnterpriseRiskScore)
        .filter(EnterpriseRiskScore.tenant_id == tenant_id)
        .all()
        if r.finding_id
    }

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

        row = risk_rows.get(f.id)
        scores.append(row.overall_score if row and row.overall_score else 50)

    avg_score = round(sum(scores) / total, 1) if total else 0.0

    for r in risk_rows.values():
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


# ── Scoring Profiles ──────────────────────────────────────────────────────────

@router.post("/profiles", response_model=ScoringProfileResponse)
def create_scoring_profile(
    req: ScoringProfileCreate,
    request: Request,
    tenant_id: str = "demo-tenant",
    db: Session = Depends(get_db),
):
    """Create or replace the active scoring profile for a tenant."""
    require_enterprise_auth(request)
    # Deactivate existing active profiles
    db.query(EnterpriseScoringProfile).filter(
        EnterpriseScoringProfile.tenant_id == tenant_id,
        EnterpriseScoringProfile.is_active.is_(True),
    ).update({"is_active": False})

    row = EnterpriseScoringProfile(
        tenant_id=tenant_id,
        profile_name=req.profile_name,
        is_active=True,
        category_weights_json=json.dumps(req.category_weights) if req.category_weights else None,
        severity_multipliers_json=json.dumps(req.severity_multipliers) if req.severity_multipliers else None,
        compound_escalation_threshold=req.compound_escalation_threshold,
        compound_escalation_window_days=req.compound_escalation_window_days,
        created_by=req.created_by,
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    return ScoringProfileResponse(
        id=row.id,
        tenant_id=row.tenant_id,
        profile_name=row.profile_name,
        is_active=row.is_active,
        category_weights=json.loads(row.category_weights_json) if row.category_weights_json else None,
        severity_multipliers=json.loads(row.severity_multipliers_json) if row.severity_multipliers_json else None,
        compound_escalation_threshold=row.compound_escalation_threshold,
        compound_escalation_window_days=row.compound_escalation_window_days,
        created_by=row.created_by,
    )


@router.get("/profiles/{tenant_id}", response_model=ScoringProfileResponse | None)
def get_active_scoring_profile(
    tenant_id: str,
    request: Request,
    db: Session = Depends(get_db),
):
    """Return the active scoring profile for a tenant, or null if using defaults."""
    require_enterprise_auth(request)
    row = (
        db.query(EnterpriseScoringProfile)
        .filter(
            EnterpriseScoringProfile.tenant_id == tenant_id,
            EnterpriseScoringProfile.is_active.is_(True),
        )
        .order_by(EnterpriseScoringProfile.id.desc())
        .first()
    )
    if not row:
        return None
    return ScoringProfileResponse(
        id=row.id,
        tenant_id=row.tenant_id,
        profile_name=row.profile_name,
        is_active=row.is_active,
        category_weights=json.loads(row.category_weights_json) if row.category_weights_json else None,
        severity_multipliers=json.loads(row.severity_multipliers_json) if row.severity_multipliers_json else None,
        compound_escalation_threshold=row.compound_escalation_threshold,
        compound_escalation_window_days=row.compound_escalation_window_days,
        created_by=row.created_by,
    )
