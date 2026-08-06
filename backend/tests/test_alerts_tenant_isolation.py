"""Tenant isolation + authentication for the alert list endpoints.

Regression coverage for a defect where:
  - GET /api/alerts/feed had no authentication dependency and no tenant filter,
    so an unauthenticated caller could read raw inspection data (file names,
    vendors, findings, owners, notes) across every tenant; and
  - GET /api/alerts/open was authenticated but had no tenant filter, so any
    authenticated viewer could read every tenant's open alerts.

Both now require an authenticated identity and are scoped to the caller's
tenant (platform admins still see all tenants), matching the tenant-isolation
pattern already enforced on the inspection resource routes.
"""
from fastapi.testclient import TestClient

from app.db import models
from app.db.session import SessionLocal
from app.main import app

client = TestClient(app)

AUTH_ADMIN = {"Authorization": "Bearer dev-token"}         # admin
AUTH_VIEWER = {"Authorization": "Bearer viewer-token"}     # viewer

TENANT_A = "alerts-iso-alpha"
TENANT_B = "alerts-iso-beta"
FILE_A = "alerts-iso-alpha-instrument.png"
FILE_B = "alerts-iso-beta-instrument.png"


def _seed_alert(tenant_id: str, file_name: str) -> None:
    """Insert an alert-worthy inspection (debris finding) for a tenant."""
    db = SessionLocal()
    try:
        db.query(models.Inspection).filter(models.Inspection.file_name == file_name).delete()
        db.add(models.Inspection(
            file_name=file_name,
            tenant_id=tenant_id,
            tenant_name=tenant_id,
            detected_issue="debris",   # triggers alert_needed in the feed
            risk_score=80,
            alert_status="open",
            instrument_type="forceps",
            vendor_name="acme",
        ))
        db.commit()
    finally:
        db.close()


def _cleanup() -> None:
    db = SessionLocal()
    try:
        db.query(models.Inspection).filter(
            models.Inspection.file_name.in_([FILE_A, FILE_B])
        ).delete(synchronize_session=False)
        db.commit()
    finally:
        db.close()


def setup_module(_module) -> None:
    _seed_alert(TENANT_A, FILE_A)
    _seed_alert(TENANT_B, FILE_B)


def teardown_module(_module) -> None:
    _cleanup()


def _file_names(payload: dict) -> set[str]:
    return {item["file_name"] for item in payload.get("items", [])}


class TestAlertsFeedRequiresAuth:
    def test_feed_rejects_unauthenticated_caller(self):
        r = client.get("/api/alerts/feed")
        assert r.status_code == 401, r.text

    def test_open_rejects_unauthenticated_caller(self):
        r = client.get("/api/alerts/open")
        assert r.status_code == 401, r.text


class TestAlertsFeedTenantScoping:
    def test_feed_scoped_to_caller_tenant_for_non_admin(self):
        r = client.get(
            "/api/alerts/feed",
            headers={**AUTH_VIEWER, "X-Tenant-Id": TENANT_B},
        )
        assert r.status_code == 200, r.text
        names = _file_names(r.json())
        assert FILE_B in names
        assert FILE_A not in names  # another tenant's data must not leak

    def test_open_scoped_to_caller_tenant_for_non_admin(self):
        r = client.get(
            "/api/alerts/open",
            headers={**AUTH_VIEWER, "X-Tenant-Id": TENANT_B},
        )
        assert r.status_code == 200, r.text
        names = _file_names(r.json())
        assert FILE_B in names
        assert FILE_A not in names

    def test_admin_sees_all_tenants(self):
        r = client.get("/api/alerts/feed", headers=AUTH_ADMIN)
        assert r.status_code == 200, r.text
        names = _file_names(r.json())
        assert FILE_A in names and FILE_B in names
