"""v4.7 — Project Apollo, Section 4: Audit Center.

Composes `accreditation_engine.py` + `regulatory_standards_catalogue.py`
(already extended with AAMI ST91/AORN/DNV standards and the
internal/vendor package types) — this module does not add a second
audit-package generator. Every finding an audit package carries already
cites its evidence: a `standard_code`, `citation_text`, and
`remediation_guidance` from the standards catalogue mapping.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.services import accreditation_engine

# All audit package types Apollo supports — mirrors
# `accreditation_engine.generate_audit_package`'s `body_map` keys.
AUDIT_PACKAGE_TYPES = [
    "joint_commission", "aami", "aami_st91", "fda", "cms", "aorn", "dnv", "internal", "vendor", "full",
]


class UnsupportedAuditPackageTypeError(Exception):
    pass


def audit_center_summary(db: Session, tenant_id: str, *, facility_id: str = "") -> dict:
    """Regulatory dashboard (readiness scores, standards summary, top
    findings) — the Audit Center's home tile."""
    dashboard = accreditation_engine.compute_regulatory_dashboard(tenant_id, facility_id, db)
    return {
        "overall_readiness_score": dashboard.overall_readiness_score,
        "readiness_tier": dashboard.readiness_tier,
        "joint_commission_score": dashboard.joint_commission_score,
        "aami_score": dashboard.aami_score,
        "fda_score": dashboard.fda_score,
        "cms_score": dashboard.cms_score,
        "iso_score": dashboard.iso_score,
        "total_deficiencies": dashboard.total_deficiencies,
        "critical_deficiencies": dashboard.critical_deficiencies,
        "open_capas": dashboard.open_capas,
        "standards_summary": dashboard.standards_summary,
        "top_findings": [f.model_dump() for f in dashboard.top_findings],
        "recommended_actions": dashboard.recommended_actions,
        "supported_package_types": AUDIT_PACKAGE_TYPES,
        "data_source": dashboard.data_source,
        "human_review_required": True,
    }


def generate_audit(
    tenant_id: str, *, package_type: str, facility_id: str = "", period_label: str = "",
    generated_by: str = "system", db=None,
) -> dict:
    """Generates an audit-ready evidence package for any of the 9 supported
    bodies (Joint Commission/AAMI ST79/AAMI ST91/AORN/CMS/DNV/Internal/
    Vendor/full). Every finding in the package already carries its
    standard citation and remediation guidance — no unlinked findings."""
    if package_type not in AUDIT_PACKAGE_TYPES:
        raise UnsupportedAuditPackageTypeError(
            f"Unsupported audit package type '{package_type}'. Supported: {AUDIT_PACKAGE_TYPES}",
        )
    result = accreditation_engine.generate_audit_package(
        tenant_id, facility_id=facility_id, package_type=package_type,
        period_label=period_label, generated_by=generated_by, db=db,
    )
    return result.model_dump()
