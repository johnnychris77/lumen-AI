from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.services.compliance_evidence_bundle_verification_service import (
    verify_compliance_evidence_bundle_hash,
)


def build_compliance_evidence_verification_summary(
    db: Session,
    *,
    bundle_hash: str,
) -> dict[str, Any]:
    verification = verify_compliance_evidence_bundle_hash(
        db,
        bundle_hash=bundle_hash,
    )

    if not verification.get("verified"):
        return {
            "status": "success",
            "verified": False,
            "bundle_hash": bundle_hash,
            "bundle_hash_algorithm": "SHA-256",
            "message": verification.get(
                "message",
                "Compliance evidence bundle could not be verified.",
            ),
        }

    bundle = verification.get("bundle") or {}

    return {
        "status": "success",
        "verified": True,
        "summary_type": "lumenai_compliance_evidence_verification_summary",
        "bundle_hash": verification["bundle_hash"],
        "bundle_hash_algorithm": verification["bundle_hash_algorithm"],
        "bundle_type": bundle.get("bundle_type", "lumenai_compliance_evidence_bundle"),
        "bundle_version": bundle.get("bundle_version", ""),
        "generated_at": verification.get("generated_at", ""),
        "generated_by": verification.get("generated_by", ""),
        "generated_role": verification.get("generated_role", ""),
        "audit_export_hash": verification.get("audit_export_hash", ""),
        "audit_export_hash_algorithm": verification.get(
            "audit_export_hash_algorithm",
            "SHA-256",
        ),
        "manifest_hash": verification.get("manifest_hash", ""),
        "manifest_hash_algorithm": verification.get(
            "manifest_hash_algorithm",
            "SHA-256",
        ),
        "export_count": verification.get("export_count"),
        "tamper_evident": bool(verification.get("tamper_evident", False)),
        "compliance_controls": bundle.get("compliance_controls", []),
        "verification": {
            "bundle_verified": True,
            "audit_export_hash_present": bool(verification.get("audit_export_hash")),
            "manifest_hash_present": bool(verification.get("manifest_hash")),
            "audit_event_id": verification.get("event_id"),
        },
        "message": "Compliance evidence bundle verified successfully.",
    }
