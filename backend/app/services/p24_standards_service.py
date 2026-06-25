"""P24: Global Healthcare Intelligence Ecosystem — service layer with seeded reference data."""
from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from app.models.p24_standards import (
    AdvisoryConsortiumMember,
    APIPartnerApplication,
    BaselineGovernanceRecord,
    BenchmarkReport,
    QualityStandard,
    RegionalDeployment,
    StandardsPublication,
)

DISCLAIMER = (
    "LumenAI P24 Global Standards outputs are for planning and governance purposes only. "
    "No individual facility, patient, or instrument is identified. "
    "All outputs require human review before operational decisions. "
    "Does not constitute regulatory approval or clearance."
)

# ---------------------------------------------------------------------------
# Serialisation
# ---------------------------------------------------------------------------


def _to_dict(obj: Any) -> dict:
    result: dict[str, Any] = {}
    for col in obj.__table__.columns:
        val = getattr(obj, col.name)
        if hasattr(val, "isoformat"):
            val = val.isoformat()
        result[col.name] = val
    result["human_review_required"] = True
    return result


# ---------------------------------------------------------------------------
# Seed data
# ---------------------------------------------------------------------------

_QUALITY_STANDARDS_SEED = [
    {
        "standard_type": "contamination_classification",
        "version": "2.1",
        "status": "published",
        "title": "Global Surgical Instrument Contamination Classification Standard v2.1",
        "description": (
            "Defines a four-tier contamination severity classification for surgical instruments "
            "across all participating network facilities. Aligned with ISO 17664 and AAMI ST79."
        ),
        "criteria": json.dumps({
            "tier_1_critical": "Visible biological contamination or confirmed pathogen presence",
            "tier_2_major": "Residual protein >200 mcg/device or biofilm detected by ATP",
            "tier_3_moderate": "Residual protein 50-200 mcg/device or surface pitting",
            "tier_4_minor": "Cosmetic staining without functional impact",
        }),
        "applicable_categories": json.dumps([
            "flexible_scopes", "rigid_scopes", "laparoscopic_instruments",
            "powered_instruments", "retractors"
        ]),
        "regulatory_alignment": json.dumps({"ISO": "17664", "AAMI": "ST79", "EU_MDR": "Annex_I"}),
    },
    {
        "standard_type": "instrument_defect",
        "version": "1.4",
        "status": "published",
        "title": "Surgical Instrument Physical Defect Classification Standard v1.4",
        "description": (
            "Standardized defect grading for physical integrity failures including pitting, "
            "corrosion, deformation, and identification marking degradation."
        ),
        "criteria": json.dumps({
            "grade_A_critical": "Functional compromise — instrument must be removed from service",
            "grade_B_major": "Significant defect requiring immediate inspection and repair evaluation",
            "grade_C_moderate": "Defect requiring monitoring and scheduled maintenance",
            "grade_D_minor": "Cosmetic defect with no functional or safety impact",
        }),
        "applicable_categories": json.dumps([
            "orthopaedic_instruments", "cardiovascular_instruments",
            "rigid_scopes", "powered_instruments"
        ]),
        "regulatory_alignment": json.dumps({"FDA": "21CFR820", "EUMDR": "Article_10", "TGA": "ARTG"}),
    },
    {
        "standard_type": "baseline_variance",
        "version": "1.0",
        "status": "published",
        "title": "Network Baseline Variance Tolerance Standard v1.0",
        "description": (
            "Defines acceptable variance thresholds for instrument quality baselines "
            "against network-published reference standards. Enables early deviation detection."
        ),
        "criteria": json.dumps({
            "within_tolerance": "Facility rate within ±1.5 SD of network baseline",
            "watch_zone": "Facility rate 1.5–2.5 SD from network baseline — monitoring recommended",
            "alert_zone": "Facility rate >2.5 SD from network baseline — investigation recommended",
            "critical_deviation": "Facility rate >3 SD — immediate review required",
        }),
        "applicable_categories": json.dumps(["all_categories"]),
        "regulatory_alignment": json.dumps({"ISO": "13485", "FDA": "QMSR", "EUMDR": "MDR_2017_745"}),
    },
    {
        "standard_type": "inspection_scoring",
        "version": "3.0",
        "status": "published",
        "title": "Global Instrument Inspection Scoring Standard v3.0",
        "description": (
            "Unified 100-point inspection scoring rubric enabling cross-network benchmarking. "
            "Covers visual inspection, functional testing, cleanliness verification, and documentation."
        ),
        "criteria": json.dumps({
            "visual_inspection": "30 points — physical integrity, identification, surface condition",
            "cleanliness_verification": "35 points — ATP, protein residue, biofilm indicators",
            "functional_testing": "25 points — mechanism, articulation, seal integrity",
            "documentation": "10 points — traceability, service records, cycle count",
        }),
        "applicable_categories": json.dumps(["all_categories"]),
        "regulatory_alignment": json.dumps({
            "AAMI": "ST79", "ISO": "15883", "FDA": "21CFR820", "EUMDR": "MDR_2017_745"
        }),
    },
]

_REGIONAL_DEPLOYMENTS_SEED = [
    {
        "region": "north_america",
        "deployment_status": "active",
        "data_residency_country": "United States",
        "privacy_framework": "HIPAA",
        "regulatory_frameworks": json.dumps(["FDA_21CFR820", "FDA_QMSR", "Health_Canada"]),
        "compliance_status": "compliant",
        "active_participants": 34,
        "data_residency_verified": True,
        "cross_border_transfer_approved": False,
        "notes": "Primary deployment region. Full HIPAA BAA program active.",
    },
    {
        "region": "europe",
        "deployment_status": "active",
        "data_residency_country": "Germany",
        "privacy_framework": "GDPR",
        "regulatory_frameworks": json.dumps(["EU_MDR_2017_745", "EU_IVDR_2017_746"]),
        "compliance_status": "compliant",
        "active_participants": 18,
        "data_residency_verified": True,
        "cross_border_transfer_approved": True,
        "notes": "EU data residency in Frankfurt. Standard Contractual Clauses active for cross-border.",
    },
    {
        "region": "apac",
        "deployment_status": "pilot",
        "data_residency_country": "Singapore",
        "privacy_framework": "PDPA",
        "regulatory_frameworks": json.dumps(["HSA_Singapore", "NMPA_China", "PMDA_Japan"]),
        "compliance_status": "partial",
        "active_participants": 7,
        "data_residency_verified": True,
        "cross_border_transfer_approved": False,
        "notes": "Pilot phase. PDPA compliance complete. PMDA alignment in progress.",
    },
    {
        "region": "australia",
        "deployment_status": "active",
        "data_residency_country": "Australia",
        "privacy_framework": "Privacy_Act_1988",
        "regulatory_frameworks": json.dumps(["TGA_ARTG", "TGA_MDO_2021"]),
        "compliance_status": "compliant",
        "active_participants": 11,
        "data_residency_verified": True,
        "cross_border_transfer_approved": False,
        "notes": "Full TGA compliance. Australian data residency enforced.",
    },
    {
        "region": "latam",
        "deployment_status": "planning",
        "data_residency_country": "Brazil",
        "privacy_framework": "LGPD",
        "regulatory_frameworks": json.dumps(["ANVISA_Brazil", "INVIMA_Colombia"]),
        "compliance_status": "assessing",
        "active_participants": 0,
        "data_residency_verified": False,
        "cross_border_transfer_approved": False,
        "notes": "Planning phase. LGPD assessment in progress. Target launch: H2 2026.",
    },
]

_BENCHMARK_REPORTS_SEED = [
    {
        "report_type": "annual",
        "report_period": "2025-Annual",
        "region": "global",
        "facility_count": 47,
        "network_percentile": 72.0,
        "contamination_rate": 0.031,
        "reliability_score": 0.94,
        "inspection_pass_rate": 0.961,
        "capa_closure_rate": 0.887,
        "benchmark_summary": (
            "2025 Annual Network Benchmark: 47 participating facilities across 4 regions. "
            "Network mean contamination rate 3.1% — 18% improvement vs 2024. "
            "Inspection pass rate 96.1% — exceeds 95% network target. "
            "CAPA closure rate 88.7% — approaching 90% target."
        ),
        "executive_summary": (
            "The 2025 Global Surgical Instrument Quality Benchmark demonstrates measurable "
            "network-wide quality improvement across contamination, reliability, and inspection "
            "dimensions. Participating facilities in the top quartile achieve 2.4% contamination "
            "rates versus 4.8% for non-network facilities (external reference data). "
            "Association identified — causation not established. Human review required."
        ),
        "status": "published",
    },
    {
        "report_type": "contamination",
        "report_period": "2025-H1",
        "region": "north_america",
        "facility_count": 28,
        "network_percentile": 68.0,
        "contamination_rate": 0.028,
        "reliability_score": None,
        "inspection_pass_rate": 0.954,
        "capa_closure_rate": 0.901,
        "benchmark_summary": (
            "H1 2025 North America Contamination Benchmark: 28 facilities. "
            "Flexible scope contamination rate 2.8% — top quartile threshold 1.9%. "
            "Laparoscopic biofilm signal elevated (see Global Recall Warning GW-2025-002). "
            "Human review recommended before operational decisions."
        ),
        "executive_summary": (
            "Contamination trends for H1 2025 indicate network-wide improvement in flexible scope "
            "decontamination. Three facilities remain in the alert zone (>2.5 SD from baseline). "
            "Laparoscopic biofilm pattern warrants continued monitoring. "
            "Association identified — causation not established."
        ),
        "status": "published",
    },
    {
        "report_type": "reliability",
        "report_period": "2025-H1",
        "region": "global",
        "facility_count": 42,
        "network_percentile": 79.0,
        "contamination_rate": None,
        "reliability_score": 0.951,
        "inspection_pass_rate": 0.963,
        "capa_closure_rate": 0.894,
        "benchmark_summary": (
            "H1 2025 Global Reliability Benchmark: 42 facilities. "
            "Network mean reliability score 95.1%. Orthopaedic instrument category "
            "shows identification failure improvement (see QS-DEFECT-1.4). "
            "Powered instruments reliability stable at 96.2%."
        ),
        "executive_summary": (
            "Instrument reliability metrics demonstrate positive trajectory across all categories. "
            "Orthopaedic labeling improvements associated with recent identification standard adoption. "
            "Possible contributing factor: CAPA program improvements. Investigation recommended. "
            "Association observed — causation not established. Human review required."
        ),
        "status": "published",
    },
    {
        "report_type": "executive_scorecard",
        "report_period": "2025-Q2",
        "region": "global",
        "facility_count": 47,
        "network_percentile": 72.0,
        "contamination_rate": 0.031,
        "reliability_score": 0.94,
        "inspection_pass_rate": 0.961,
        "capa_closure_rate": 0.887,
        "benchmark_summary": (
            "Q2 2025 Executive Scorecard: Overall network quality score 91.4/100. "
            "Key metrics trending positive. Two recall early warnings active. "
            "Three facilities requiring governance intervention."
        ),
        "executive_summary": (
            "Q2 2025 executive network health: Strong. Network quality index 91.4 vs 89.1 Q1. "
            "Active governance items: 2 recall warnings, 3 baseline deviation alerts, "
            "1 standards publication under consortium review. "
            "Human review required before any operational decisions."
        ),
        "status": "published",
    },
]

_CONSORTIUM_SEED = [
    {
        "organization_type": "standards_body",
        "region": "global",
        "membership_tier": "steering",
        "membership_status": "active",
        "governance_roles": json.dumps(["standards_chair", "publication_approver"]),
        "standards_review_active": True,
        "voting_rights": True,
    },
    {
        "organization_type": "regulator",
        "region": "north_america",
        "membership_tier": "voting",
        "membership_status": "active",
        "governance_roles": json.dumps(["regulatory_liaison", "standards_reviewer"]),
        "standards_review_active": True,
        "voting_rights": True,
    },
    {
        "organization_type": "academic",
        "region": "europe",
        "membership_tier": "contributor",
        "membership_status": "active",
        "governance_roles": json.dumps(["research_contributor", "publication_reviewer"]),
        "standards_review_active": True,
        "voting_rights": False,
    },
    {
        "organization_type": "hospital",
        "region": "north_america",
        "membership_tier": "contributor",
        "membership_status": "active",
        "governance_roles": json.dumps(["clinical_reviewer"]),
        "standards_review_active": False,
        "voting_rights": False,
    },
    {
        "organization_type": "manufacturer",
        "region": "europe",
        "membership_tier": "observer",
        "membership_status": "active",
        "governance_roles": json.dumps([]),
        "standards_review_active": False,
        "voting_rights": False,
    },
]

_PUBLICATIONS_SEED = [
    {
        "title": "Global Surgical Instrument Quality Framework v1.0",
        "publication_type": "standard",
        "version": "1.0",
        "status": "published",
        "abstract": (
            "Comprehensive quality framework establishing classification standards for "
            "contamination, defects, baseline variance, and inspection scoring across "
            "the Global Surgical Intelligence Network. Applicable to all instrument categories."
        ),
        "authors": json.dumps(["GSIN Standards Committee", "Clinical Advisory Board"]),
        "regulatory_bodies_aligned": json.dumps(["FDA", "EUMDR", "TGA", "HealthCanada"]),
        "public_comment_period_days": 60,
    },
    {
        "title": "Network Baseline Governance Standard v1.0",
        "publication_type": "guidance",
        "version": "1.0",
        "status": "published",
        "abstract": (
            "Governance framework for baseline approval, version control, provenance tracking, "
            "and audit requirements for instrument quality baselines within the GSIN network."
        ),
        "authors": json.dumps(["GSIN Governance Board", "Data Standards Working Group"]),
        "regulatory_bodies_aligned": json.dumps(["FDA", "EUMDR", "ISO_13485"]),
        "public_comment_period_days": 45,
    },
    {
        "title": "2025 Annual Global Benchmark Report",
        "publication_type": "benchmark_report",
        "version": "2025.1",
        "status": "published",
        "abstract": (
            "Annual network-wide benchmark of surgical instrument quality metrics across "
            "47 participating facilities. Anonymized aggregate data only. "
            "Does not identify individual facilities, patients, or instruments."
        ),
        "authors": json.dumps(["GSIN Analytics Committee"]),
        "regulatory_bodies_aligned": json.dumps(["FDA", "EUMDR", "TGA"]),
        "public_comment_period_days": 0,
    },
    {
        "title": "International Data Residency and Privacy Compliance Framework",
        "publication_type": "technical_note",
        "version": "1.0",
        "status": "consortium_review",
        "abstract": (
            "Technical framework for data residency enforcement, cross-border transfer governance, "
            "and privacy regulation compliance across GSIN regional deployments. "
            "Covers GDPR, HIPAA, PDPA, Privacy Act 1988, and LGPD."
        ),
        "authors": json.dumps(["GSIN Privacy Working Group", "Legal Advisory Council"]),
        "regulatory_bodies_aligned": json.dumps(["GDPR", "HIPAA", "PDPA", "LGPD"]),
        "public_comment_period_days": 30,
    },
]


# ---------------------------------------------------------------------------
# Seeding helpers
# ---------------------------------------------------------------------------


def _seed_standards(db: Session, tenant_id: str) -> list[dict]:
    results = []
    for s in _QUALITY_STANDARDS_SEED:
        obj = QualityStandard(**s)
        db.add(obj)
        db.flush()
        results.append(_to_dict(obj))
    db.commit()
    return results


def _seed_benchmarks(db: Session, tenant_id: str) -> list[dict]:
    results = []
    for b in _BENCHMARK_REPORTS_SEED:
        obj = BenchmarkReport(tenant_id=tenant_id, **b)
        db.add(obj)
        db.flush()
        results.append(_to_dict(obj))
    db.commit()
    return results


def _seed_regions(db: Session) -> list[dict]:
    results = []
    for r in _REGIONAL_DEPLOYMENTS_SEED:
        obj = RegionalDeployment(**r)
        db.add(obj)
        db.flush()
        results.append(_to_dict(obj))
    db.commit()
    return results


def _seed_consortium(db: Session, tenant_id: str) -> list[dict]:
    results = []
    for i, m in enumerate(_CONSORTIUM_SEED):
        synthetic_tenant = f"consortium-member-{i + 1}"
        if db.query(AdvisoryConsortiumMember).filter_by(tenant_id=synthetic_tenant).first():
            continue
        obj = AdvisoryConsortiumMember(tenant_id=synthetic_tenant, **m)
        db.add(obj)
        db.flush()
        results.append(_to_dict(obj))
    db.commit()
    return results


def _seed_publications(db: Session) -> list[dict]:
    results = []
    for p in _PUBLICATIONS_SEED:
        obj = StandardsPublication(**p)
        db.add(obj)
        db.flush()
        results.append(_to_dict(obj))
    db.commit()
    return results


# ---------------------------------------------------------------------------
# Public service functions
# ---------------------------------------------------------------------------


def get_quality_standards(
    db: Session, standard_type: str | None = None, status: str | None = None
) -> list[dict]:
    q = db.query(QualityStandard)
    if standard_type:
        q = q.filter(QualityStandard.standard_type == standard_type)
    if status:
        q = q.filter(QualityStandard.status == status)
    else:
        q = q.filter(QualityStandard.status == "published")
    rows = q.all()
    if not rows:
        return _seed_standards(db, "")
    return [_to_dict(r) for r in rows]


def get_baseline_governance(db: Session, tenant_id: str) -> list[dict]:
    rows = db.query(BaselineGovernanceRecord).filter_by(tenant_id=tenant_id).all()
    return [_to_dict(r) for r in rows]


def get_benchmark_reports(
    db: Session, tenant_id: str, report_type: str | None = None
) -> list[dict]:
    q = db.query(BenchmarkReport).filter(
        BenchmarkReport.tenant_id == tenant_id,
        BenchmarkReport.status == "published",
    )
    if report_type:
        q = q.filter(BenchmarkReport.report_type == report_type)
    rows = q.all()
    if not rows:
        return _seed_benchmarks(db, tenant_id)
    return [_to_dict(r) for r in rows]


def get_regional_deployments(db: Session, region: str | None = None) -> list[dict]:
    q = db.query(RegionalDeployment)
    if region:
        q = q.filter(RegionalDeployment.region == region)
    rows = q.all()
    if not rows:
        return _seed_regions(db)
    return [_to_dict(r) for r in rows]


def get_api_partners(db: Session, tenant_id: str) -> list[dict]:
    rows = db.query(APIPartnerApplication).filter_by(tenant_id=tenant_id).all()
    return [_to_dict(r) for r in rows]


def get_consortium_members(db: Session, tier: str | None = None) -> list[dict]:
    q = db.query(AdvisoryConsortiumMember).filter(
        AdvisoryConsortiumMember.membership_status == "active"
    )
    if tier:
        q = q.filter(AdvisoryConsortiumMember.membership_tier == tier)
    rows = q.all()
    if not rows:
        _seed_consortium(db, "")
        rows = db.query(AdvisoryConsortiumMember).filter(
            AdvisoryConsortiumMember.membership_status == "active"
        ).all()
    return [_to_dict(r) for r in rows]


def get_publications(db: Session, pub_type: str | None = None) -> list[dict]:
    q = db.query(StandardsPublication)
    if pub_type:
        q = q.filter(StandardsPublication.publication_type == pub_type)
    rows = q.all()
    if not rows:
        return _seed_publications(db)
    return [_to_dict(r) for r in rows]


def get_ecosystem_dashboard(db: Session, tenant_id: str) -> dict:
    standards = get_quality_standards(db)
    benchmarks = get_benchmark_reports(db, tenant_id)
    regions = get_regional_deployments(db)
    members = get_consortium_members(db)
    publications = get_publications(db)
    api_apps = get_api_partners(db, tenant_id)

    active_regions = sum(1 for r in regions if r.get("deployment_status") == "active")
    published_standards = sum(1 for s in standards if s.get("status") == "published")
    published_pubs = sum(1 for p in publications if p.get("status") == "published")
    total_participants = sum(r.get("active_participants", 0) or 0 for r in regions)

    latest_benchmark = next(
        (b for b in benchmarks if b.get("report_type") == "annual"),
        benchmarks[0] if benchmarks else {},
    )

    return {
        "published_standards": published_standards,
        "active_regions": active_regions,
        "total_network_participants": total_participants,
        "consortium_members": len(members),
        "published_papers": published_pubs,
        "api_partners": len(api_apps),
        "network_contamination_rate": latest_benchmark.get("contamination_rate"),
        "network_inspection_pass_rate": latest_benchmark.get("inspection_pass_rate"),
        "network_reliability_score": latest_benchmark.get("reliability_score"),
        "network_capa_closure_rate": latest_benchmark.get("capa_closure_rate"),
        "top_benchmarks": benchmarks[:2],
        "active_region_list": [r for r in regions if r.get("deployment_status") == "active"],
        "recent_publications": publications[:3],
        "human_review_required": True,
        "disclaimer": DISCLAIMER,
    }
