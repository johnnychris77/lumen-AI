import os

import pytest
from fastapi import HTTPException
from starlette.requests import Request

os.environ.setdefault("DATABASE_URL", "sqlite:///./lumenai.db")


def _request(headers: list[tuple[bytes, bytes]]) -> Request:
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/test",
            "headers": headers,
        }
    )


def test_hospital_admin_has_governance_packet_export_permission(monkeypatch):
    from app.enterprise_auth import require_permission

    monkeypatch.setenv("AUTH_MODE", "dev")
    monkeypatch.setenv("DEV_AUTH_TOKEN", "dev-token")

    request = _request(
        [
            (b"authorization", b"Bearer dev-token"),
            (b"x-lumenai-role", b"hospital_admin"),
            (b"x-lumenai-actor", b"permission-hospital-admin"),
        ]
    )

    context = require_permission(
        request,
        permission="governance_packet:export",
    )

    assert context.role == "hospital_admin"
    assert context.has_permission("governance_packet:export") is True


def test_vendor_does_not_have_governance_packet_export_permission(monkeypatch):
    from app.enterprise_auth import require_permission

    monkeypatch.setenv("AUTH_MODE", "dev")
    monkeypatch.setenv("DEV_AUTH_TOKEN", "dev-token")

    request = _request(
        [
            (b"authorization", b"Bearer dev-token"),
            (b"x-lumenai-role", b"vendor"),
            (b"x-lumenai-actor", b"permission-vendor"),
        ]
    )

    with pytest.raises(HTTPException) as exc:
        require_permission(
            request,
            permission="governance_packet:export",
        )

    assert exc.value.status_code == 403


def test_vendor_has_vendor_baseline_submit_permission(monkeypatch):
    from app.enterprise_auth import require_permission

    monkeypatch.setenv("AUTH_MODE", "dev")
    monkeypatch.setenv("DEV_AUTH_TOKEN", "dev-token")

    request = _request(
        [
            (b"authorization", b"Bearer dev-token"),
            (b"x-lumenai-role", b"vendor"),
            (b"x-lumenai-actor", b"permission-vendor"),
        ]
    )

    context = require_permission(
        request,
        permission="vendor_baseline:submit",
    )

    assert context.role == "vendor"
    assert context.has_permission("vendor_baseline:submit") is True


def test_viewer_does_not_have_vendor_baseline_approve_permission(monkeypatch):
    from app.enterprise_auth import require_permission

    monkeypatch.setenv("AUTH_MODE", "dev")
    monkeypatch.setenv("DEV_AUTH_TOKEN", "dev-token")

    request = _request(
        [
            (b"authorization", b"Bearer dev-token"),
            (b"x-lumenai-role", b"viewer"),
            (b"x-lumenai-actor", b"permission-viewer"),
        ]
    )

    with pytest.raises(HTTPException) as exc:
        require_permission(
            request,
            permission="vendor_baseline:approve",
        )

    assert exc.value.status_code == 403


def test_missing_token_cannot_use_permission_helper(monkeypatch):
    from app.enterprise_auth import require_permission

    monkeypatch.setenv("AUTH_MODE", "dev")
    monkeypatch.setenv("DEV_AUTH_TOKEN", "dev-token")

    request = _request(
        [
            (b"x-lumenai-role", b"hospital_admin"),
            (b"x-lumenai-actor", b"permission-missing-token"),
        ]
    )

    with pytest.raises(HTTPException) as exc:
        require_permission(
            request,
            permission="governance_packet:export",
        )

    assert exc.value.status_code == 401


def test_named_permission_helpers_allow_expected_admin_permissions(monkeypatch):
    from app.enterprise_auth import (
        require_audit_chain_verify,
        require_governance_packet_certificate,
        require_governance_packet_export,
        require_governance_packet_verify,
        require_vendor_baseline_approve,
        require_vendor_baseline_audit_read,
        require_vendor_baseline_library_read,
    )

    monkeypatch.setenv("AUTH_MODE", "dev")
    monkeypatch.setenv("DEV_AUTH_TOKEN", "dev-token")

    request = _request(
        [
            (b"authorization", b"Bearer dev-token"),
            (b"x-lumenai-role", b"hospital_admin"),
            (b"x-lumenai-actor", b"permission-helper-admin"),
        ]
    )

    assert require_governance_packet_export(request).role == "hospital_admin"
    assert require_governance_packet_verify(request).role == "hospital_admin"
    assert require_governance_packet_certificate(request).role == "hospital_admin"
    assert require_vendor_baseline_approve(request).role == "hospital_admin"
    assert require_vendor_baseline_audit_read(request).role == "hospital_admin"
    assert require_vendor_baseline_library_read(request).role == "hospital_admin"
    assert require_audit_chain_verify(request).role == "hospital_admin"


def test_named_permission_helper_allows_vendor_submission_only(monkeypatch):
    from app.enterprise_auth import (
        require_governance_packet_export,
        require_vendor_baseline_submit,
    )

    monkeypatch.setenv("AUTH_MODE", "dev")
    monkeypatch.setenv("DEV_AUTH_TOKEN", "dev-token")

    request = _request(
        [
            (b"authorization", b"Bearer dev-token"),
            (b"x-lumenai-role", b"vendor"),
            (b"x-lumenai-actor", b"permission-helper-vendor"),
        ]
    )

    assert require_vendor_baseline_submit(request).role == "vendor"

    with pytest.raises(HTTPException) as exc:
        require_governance_packet_export(request)

    assert exc.value.status_code == 403
