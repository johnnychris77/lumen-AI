import pytest
from fastapi import HTTPException

from app.core.evidence_authorization import (
    EvidenceBundle,
    build_manifest_hash,
    create_evidence_audit_event,
    require_evidence_permission,
    verify_evidence_manifest_hash,
)
from app.core.principal import Principal


def test_customer_admin_can_download_own_tenant_evidence():
    principal = Principal(user_id="u1", tenant_id="tenant_a", roles=["customer_admin"])
    bundle = EvidenceBundle(
        bundle_id="bundle_1",
        tenant_id="tenant_a",
        workflow_type="capa",
        manifest_hash="abc",
    )

    require_evidence_permission(principal, bundle, action="download")


def test_cross_tenant_evidence_download_returns_404():
    principal = Principal(user_id="u1", tenant_id="tenant_a", roles=["customer_admin"])
    bundle = EvidenceBundle(
        bundle_id="bundle_1",
        tenant_id="tenant_b",
        workflow_type="capa",
        manifest_hash="abc",
    )

    with pytest.raises(HTTPException) as exc:
        require_evidence_permission(principal, bundle, action="download")

    assert exc.value.status_code == 404


def test_auditor_can_verify_evidence():
    principal = Principal(user_id="u1", tenant_id="tenant_a", roles=["auditor"])
    bundle = EvidenceBundle(
        bundle_id="bundle_1",
        tenant_id="tenant_a",
        workflow_type="evidence",
        manifest_hash="abc",
    )

    require_evidence_permission(principal, bundle, action="verify")


def test_auditor_cannot_generate_evidence():
    principal = Principal(user_id="u1", tenant_id="tenant_a", roles=["auditor"])
    bundle = EvidenceBundle(
        bundle_id="bundle_1",
        tenant_id="tenant_a",
        workflow_type="evidence",
        manifest_hash="abc",
    )

    with pytest.raises(HTTPException) as exc:
        require_evidence_permission(principal, bundle, action="generate")

    assert exc.value.status_code == 403


def test_vendor_user_can_access_assigned_vendor_evidence():
    principal = Principal(user_id="u1", tenant_id="tenant_a", roles=["vendor_user"])
    bundle = EvidenceBundle(
        bundle_id="bundle_1",
        tenant_id="tenant_a",
        workflow_type="vendor",
        vendor_id="vendor_a",
        manifest_hash="abc",
    )

    require_evidence_permission(
        principal,
        bundle,
        action="download",
        principal_vendor_id="vendor_a",
    )


def test_vendor_user_cannot_access_other_vendor_evidence():
    principal = Principal(user_id="u1", tenant_id="tenant_a", roles=["vendor_user"])
    bundle = EvidenceBundle(
        bundle_id="bundle_1",
        tenant_id="tenant_a",
        workflow_type="vendor",
        vendor_id="vendor_b",
        manifest_hash="abc",
    )

    with pytest.raises(HTTPException) as exc:
        require_evidence_permission(
            principal,
            bundle,
            action="download",
            principal_vendor_id="vendor_a",
        )

    assert exc.value.status_code == 404


def test_evidence_audit_event_created_for_download():
    principal = Principal(user_id="u1", tenant_id="tenant_a", roles=["customer_admin"])
    bundle = EvidenceBundle(
        bundle_id="bundle_1",
        tenant_id="tenant_a",
        workflow_type="capa",
        manifest_hash="abc",
    )

    event = create_evidence_audit_event(
        principal,
        bundle,
        action="download",
        authorization_result="allowed",
    )

    assert event.actor_user_id == "u1"
    assert event.tenant_id == "tenant_a"
    assert event.evidence_bundle_id == "bundle_1"
    assert event.action == "download"
    assert event.authorization_result == "allowed"


def test_manifest_hash_verification_detects_tampering():
    manifest = {"bundle_id": "bundle_1", "records": ["a", "b"]}
    valid_hash = build_manifest_hash(manifest)

    bundle = EvidenceBundle(
        bundle_id="bundle_1",
        tenant_id="tenant_a",
        workflow_type="capa",
        manifest_hash=valid_hash,
    )

    assert verify_evidence_manifest_hash(bundle, manifest)

    tampered_manifest = {"bundle_id": "bundle_1", "records": ["a", "b", "c"]}
    assert not verify_evidence_manifest_hash(bundle, tampered_manifest)
