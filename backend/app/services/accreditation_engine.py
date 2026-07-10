"""P8: Accreditation readiness scoring and audit package generation."""
from __future__ import annotations

import hashlib
import json
import random
from datetime import datetime, timezone
from app.schemas.regulatory import (
    AccreditationReadinessResult,
    AccreditationFinding,
    AuditPackageResult,
    FDASubmissionResult,
    RegulatoryDashboard,
)
from app.services.regulatory_standards_catalogue import (
    get_mappings_for_finding,
    get_standards,
)


def _seed(s: str) -> random.Random:
    h = hashlib.md5(s.encode()).hexdigest()[:8]
    return random.Random(int(h, 16))


def _now_str() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Accreditation Readiness Scoring ──────────────────────────────────────────

def compute_accreditation_readiness(
    tenant_id: str,
    facility_id: str = "",
    db=None,
) -> AccreditationReadinessResult:
    """Compute real-time accreditation readiness score from inspection data."""
    now = _now_str()
    findings: list[AccreditationFinding] = []
    data_source = "mock"

    if db is not None:
        try:
            from app.models.cv_inference import CVInferenceRecord
            q = db.query(CVInferenceRecord).filter(
                CVInferenceRecord.tenant_id == tenant_id,
            )
            if facility_id:
                q = q.filter(CVInferenceRecord.facility_id == facility_id)
            records = q.order_by(CVInferenceRecord.id.desc()).limit(100).all()

            if records:
                data_source = "real"
                # Aggregate finding counts
                finding_totals = {
                    "blood": sum(r.blood_count for r in records),
                    "bone": sum(r.bone_count for r in records),
                    "tissue": sum(r.tissue_count for r in records),
                    "crack": sum(r.crack_count for r in records),
                    "corrosion": sum(r.corrosion_count for r in records),
                    "insulation": sum(r.insulation_count for r in records),
                    "residue": sum(r.residue_count for r in records),
                }
                n = len(records)

                for finding_cat, count in finding_totals.items():
                    if count == 0:
                        continue
                    mappings = get_mappings_for_finding(finding_cat)
                    for m in mappings:
                        severity = "critical" if count / n > 0.2 else "high" if count / n > 0.05 else "medium"
                        findings.append(AccreditationFinding(
                            standard_code=m.standard_code,
                            finding_category=finding_cat,
                            occurrence_count=count,
                            rate_pct=round(count / n * 100, 1),
                            severity=severity,
                            citation_text=m.citation_text,
                            remediation_guidance=m.remediation_guidance,
                            auto_capa_required=m.auto_capa_required,
                        ))

        except Exception:
            data_source = "mock"

    if data_source == "mock":
        findings = _mock_findings(tenant_id)

    return _score_from_findings(tenant_id, facility_id, findings, now, data_source)


def _score_from_findings(
    tenant_id: str,
    facility_id: str,
    findings: list[AccreditationFinding],
    now: str,
    data_source: str,
) -> AccreditationReadinessResult:
    # Deduct points per finding by severity
    deductions = {"critical": 15.0, "high": 8.0, "medium": 4.0, "low": 1.0}
    total_deduction = sum(deductions.get(f.severity, 4.0) for f in findings)

    overall = max(0.0, round(100.0 - total_deduction, 1))

    # Per-body scores
    body_findings: dict[str, list[AccreditationFinding]] = {}
    standards = {s.code: s for s in get_standards()}
    for f in findings:
        std = standards.get(f.standard_code)
        body = std.body if std else "unknown"
        body_findings.setdefault(body, []).append(f)

    def body_score(body: str) -> float:
        bfs = body_findings.get(body, [])
        d = sum(deductions.get(f.severity, 4.0) for f in bfs)
        return max(0.0, round(100.0 - d, 1))

    critical_count = sum(1 for f in findings if f.severity == "critical")
    capa_required = sum(1 for f in findings if f.auto_capa_required)

    return AccreditationReadinessResult(
        tenant_id=tenant_id,
        facility_id=facility_id,
        assessment_date=now,
        overall_score=overall,
        joint_commission_score=body_score("joint_commission"),
        aami_score=body_score("aami"),
        fda_score=body_score("fda"),
        cms_score=body_score("cms"),
        iso_score=body_score("iso"),
        deficiency_count=len(findings),
        critical_deficiency_count=critical_count,
        open_capa_count=capa_required,
        findings=findings,
        data_source=data_source,
        readiness_tier=_readiness_tier(overall),
        recommended_actions=_readiness_actions(overall, critical_count, findings),
    )


def _readiness_tier(score: float) -> str:
    if score >= 90:
        return "survey_ready"
    if score >= 75:
        return "conditional"
    if score >= 60:
        return "needs_improvement"
    return "at_risk"


def _readiness_actions(score: float, critical: int, findings: list) -> list[str]:
    actions = []
    if critical > 0:
        actions.append(f"Resolve {critical} critical deficiency finding(s) immediately. These will result in Requirements for Improvement (RFIs) during survey.")
    auto_capas = [f for f in findings if f.auto_capa_required]
    if auto_capas:
        actions.append(f"Open CAPAs for {len(auto_capas)} finding(s) that require corrective action per standard mapping.")
    if score < 75:
        actions.append("Schedule internal mock survey before next Joint Commission visit. Focus on IC and EC standards.")
    if score < 90:
        actions.append("Review decontamination SOPs against AAMI ST79 and update staff training records.")
    if score >= 90:
        actions.append("Accreditation readiness is strong. Maintain documentation currency and conduct quarterly self-assessments.")
    return actions


def _mock_findings(tenant_id: str) -> list[AccreditationFinding]:
    rng = _seed(f"accred:{tenant_id}")
    findings = []
    mock_specs = [
        ("blood", "JC-IC.02.02.01", "high", 3, 2.1),
        ("bone", "AAMI-ST79-4", "medium", 7, 4.8),
        ("crack", "AAMI-ST79-5", "critical", 2, 1.4),
        ("corrosion", "ISO-17664-1", "medium", 5, 3.5),
        ("insulation", "AAMI-ST79-5", "critical", 1, 0.7),
    ]
    for finding_cat, code, sev, count, rate in mock_specs[:rng.randint(2, 5)]:
        mappings = get_mappings_for_finding(finding_cat)
        m = next((x for x in mappings if x.standard_code == code), mappings[0] if mappings else None)
        if m:
            findings.append(AccreditationFinding(
                standard_code=code,
                finding_category=finding_cat,
                occurrence_count=count,
                rate_pct=rate,
                severity=sev,
                citation_text=m.citation_text,
                remediation_guidance=m.remediation_guidance,
                auto_capa_required=m.auto_capa_required,
            ))
    return findings


# ── Audit Package Generation ──────────────────────────────────────────────────

def generate_audit_package(
    tenant_id: str,
    facility_id: str = "",
    package_type: str = "joint_commission",
    period_label: str = "",
    generated_by: str = "system",
    db=None,
) -> AuditPackageResult:
    """Generate an audit-ready evidence package for a regulatory body."""
    now = _now_str()
    if not period_label:
        period_label = datetime.now(timezone.utc).strftime("%Y-%m")

    readiness = compute_accreditation_readiness(tenant_id, facility_id, db)

    # Filter findings to relevant body
    body_map = {
        "joint_commission": "joint_commission",
        "aami": "aami",
        "fda": "fda",
        "cms": "cms",
        # v4.7 Project Apollo additions — AAMI ST91 (endoscope reprocessing),
        # AORN (perioperative practice), DNV (accreditation body), and
        # facility-defined internal/vendor audit package types. Internal and
        # vendor audits are not tied to a single regulatory body's standards,
        # so they include the full standards catalogue like "full" does.
        "aami_st91": "aami_st91",
        "aorn": "aorn",
        "dnv": "dnv",
        "internal": None,
        "vendor": None,
        "full": None,  # all bodies
    }
    target_body = body_map.get(package_type)
    standards = {s.code: s for s in get_standards()}

    relevant_findings = [
        f for f in readiness.findings
        if target_body is None or (standards.get(f.standard_code) and standards[f.standard_code].body == target_body)
    ]

    standards_covered = list({f.standard_code for f in relevant_findings})

    # Build package content
    package_content = {
        "package_type": package_type,
        "tenant_id": tenant_id,
        "facility_id": facility_id,
        "period_label": period_label,
        "generated_by": generated_by,
        "generated_at": now,
        "accreditation_score": readiness.overall_score,
        "readiness_tier": readiness.readiness_tier,
        "standards_covered": standards_covered,
        "findings": [f.model_dump() for f in relevant_findings],
        "recommended_actions": readiness.recommended_actions,
        "data_source": readiness.data_source,
        "attestation": {
            "statement": f"This package was auto-generated by LumenAI on {now}. All findings are derived from AI-assisted instrument inspection records.",
            "generated_by": generated_by,
            "system_version": "P8.1",
        },
    }

    # Persist to DB
    if db is not None:
        try:
            from app.models.regulatory import RegulatoryAuditPackage
            pkg = RegulatoryAuditPackage(
                tenant_id=tenant_id,
                facility_id=facility_id,
                package_type=package_type,
                period_label=period_label,
                generated_by=generated_by,
                findings_count=len(relevant_findings),
                standards_covered=json.dumps(standards_covered),
                package_json=json.dumps(package_content),
                status="ready",
            )
            db.add(pkg)
            db.commit()
            db.refresh(pkg)
            pkg_id = pkg.id
        except Exception:
            pkg_id = None
    else:
        pkg_id = None

    return AuditPackageResult(
        id=pkg_id,
        tenant_id=tenant_id,
        facility_id=facility_id,
        package_type=package_type,
        period_label=period_label,
        status="ready",
        generated_by=generated_by,
        generated_at=now,
        accreditation_score=readiness.overall_score,
        readiness_tier=readiness.readiness_tier,
        standards_covered=standards_covered,
        findings_count=len(relevant_findings),
        findings=relevant_findings,
        recommended_actions=readiness.recommended_actions,
        data_source=readiness.data_source,
    )


# ── Finding → Clause Mapper ───────────────────────────────────────────────────

def map_finding_to_clauses(finding_category: str, severity: str = "any") -> list[dict]:
    """Return all regulatory clauses triggered by a CV finding."""
    mappings = get_mappings_for_finding(finding_category)
    standards = {s.code: s for s in get_standards()}
    return [
        {
            "standard_code": m.standard_code,
            "standard_title": standards[m.standard_code].title if m.standard_code in standards else "",
            "body": standards[m.standard_code].body if m.standard_code in standards else "",
            "citation_text": m.citation_text,
            "remediation_guidance": m.remediation_guidance,
            "auto_capa_required": m.auto_capa_required,
        }
        for m in mappings
        if m.severity_threshold == "any" or m.severity_threshold == severity
    ]


# ── FDA Submission Tracker ────────────────────────────────────────────────────

def list_fda_submissions(tenant_id: str, db=None) -> list[FDASubmissionResult]:
    if db is not None:
        try:
            from app.models.regulatory import FDASubmissionTracker
            rows = db.query(FDASubmissionTracker).filter_by(tenant_id=tenant_id).all()
            if rows:
                return [FDASubmissionResult(
                    id=r.id,
                    tenant_id=r.tenant_id,
                    submission_type=r.submission_type,
                    submission_number=r.submission_number,
                    device_name=r.device_name,
                    manufacturer=r.manufacturer,
                    status=r.status,
                    submission_date=r.submission_date.isoformat() if r.submission_date else None,
                    decision_date=r.decision_date.isoformat() if r.decision_date else None,
                    notes=r.notes or "",
                ) for r in rows]
        except Exception:
            pass

    # Mock fallback
    return [
        FDASubmissionResult(
            id=1, tenant_id=tenant_id, submission_type="510k",
            submission_number="K253421",
            device_name="LumenAI CV Inspection Module",
            manufacturer="LumenAI Inc.",
            status="cleared",
            submission_date="2025-09-01T00:00:00+00:00",
            decision_date="2025-11-15T00:00:00+00:00",
            notes="Cleared for SPD inspection workflow integration.",
        ),
    ]


# ── Regulatory Dashboard ──────────────────────────────────────────────────────

def compute_regulatory_dashboard(
    tenant_id: str,
    facility_id: str = "",
    db=None,
) -> RegulatoryDashboard:
    now = _now_str()
    readiness = compute_accreditation_readiness(tenant_id, facility_id, db)
    fda_submissions = list_fda_submissions(tenant_id, db)

    # Open CAPAs (from enterprise_quality if available)
    open_capas = 0
    if db is not None:
        try:
            from app.models.enterprise_quality import EnterpriseCapa
            open_capas = db.query(EnterpriseCapa).filter(
                EnterpriseCapa.tenant_id == tenant_id,
                EnterpriseCapa.status.in_(["open", "in_progress"]),
            ).count()
        except Exception:
            open_capas = readiness.open_capa_count

    # Standards summary
    standards_map: dict[str, dict] = {}
    for std in get_standards():
        if std.body not in standards_map:
            standards_map[std.body] = {"body": std.body, "standards_count": 0, "deficiencies": 0}
        standards_map[std.body]["standards_count"] += 1

    stds = {s.code: s for s in get_standards()}
    for f in readiness.findings:
        std = stds.get(f.standard_code)
        if std and std.body in standards_map:
            standards_map[std.body]["deficiencies"] += 1

    return RegulatoryDashboard(
        tenant_id=tenant_id,
        facility_id=facility_id,
        generated_at=now,
        data_source=readiness.data_source,
        overall_readiness_score=readiness.overall_score,
        readiness_tier=readiness.readiness_tier,
        joint_commission_score=readiness.joint_commission_score,
        aami_score=readiness.aami_score,
        fda_score=readiness.fda_score,
        cms_score=readiness.cms_score,
        iso_score=readiness.iso_score,
        total_deficiencies=readiness.deficiency_count,
        critical_deficiencies=readiness.critical_deficiency_count,
        open_capas=open_capas,
        auto_capa_required_count=readiness.open_capa_count,
        fda_submissions=fda_submissions,
        standards_summary=list(standards_map.values()),
        top_findings=readiness.findings[:5],
        recommended_actions=readiness.recommended_actions,
    )
