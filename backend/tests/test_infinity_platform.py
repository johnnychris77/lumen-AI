"""v5.0 — LumenAI OS: Project Infinity — Healthcare AI Platform &
Developer Ecosystem tests.

Covers: SDK, Plugins, Marketplace, Security, API Versioning, Licensing,
Certification, and Sandbox.
"""
from __future__ import annotations

import time

from fastapi.testclient import TestClient

from app.db import models
from app.db.session import SessionLocal
from app.main import app
from app.services import (
    infinity_billing_service,
    infinity_certification_service,
    infinity_developer_portal_service,
    infinity_developer_service,
    infinity_extension_service,
    infinity_marketplace_service,
    infinity_sandbox_service,
)

client = TestClient(app)
AUTH_ADMIN = {"Authorization": "Bearer dev-token"}
AUTH_MGR = {"Authorization": "Bearer manager-token"}
AUTH_VIEWER = {"Authorization": "Bearer viewer-token"}

_counter = [0]


def uid(prefix: str) -> str:
    _counter[0] += 1
    return f"{prefix}-{int(time.time() * 1000) % 1_000_000}-{_counter[0]}"


def _seed_membership(db, tenant_id: str, *, role: str = "admin") -> None:
    db.add(models.TenantMembership(tenant_id=tenant_id, user_email=f"{role}@local.dev", role=role, is_enabled=True))
    db.commit()


def _headers(base: dict, tenant_id: str) -> dict:
    return {**base, "x-tenant-id": tenant_id}


def _make_developer(db) -> dict:
    return infinity_developer_service.create_developer_account(
        db, email=f"dev-{uid('e')}@example.com", organization_name="Acme Repairs", developer_type="repair_vendor",
        approved_by="admin@local.dev",
    )


# ── 1. SDK (Plugin SDK extension types) ───────────────────────────────────────

def test_sdk_extension_types_map_to_plugin_columns():
    db = SessionLocal()
    try:
        plugin = infinity_extension_service.register_plugin(db, plugin_key=uid("plugin"), name="Test Plugin", registered_by="admin")
        result = infinity_extension_service.register_extension(
            db, plugin["plugin_key"], extension_type="ai_skills", location="copilot",
            item={"skill_key": "forecast-helper"},
        )
    finally:
        db.close()
    assert result["ai_skills"][0]["skill_key"] == "forecast-helper"
    assert result["ai_skills"][0]["location"] == "copilot"


def test_sdk_rejects_unknown_extension_type():
    db = SessionLocal()
    try:
        plugin = infinity_extension_service.register_plugin(db, plugin_key=uid("plugin-bad"), name="Bad Plugin", registered_by="admin")
        try:
            infinity_extension_service.register_extension(db, plugin["plugin_key"], extension_type="not_a_type", location="menu", item={})
            assert False, "expected InvalidExtensionTypeError"
        except infinity_extension_service.InvalidExtensionTypeError:
            pass
    finally:
        db.close()


def test_developer_portal_api_explorer_lists_v1_endpoints():
    catalog = infinity_developer_portal_service.api_explorer_catalog()
    paths = {e["path"] for e in catalog}
    for expected in ("/api/v1/phoenix", "/api/v1/athena", "/api/v1/apollo", "/api/v1/identity"):
        assert expected in paths


# ── 2. Plugins ─────────────────────────────────────────────────────────────────

def test_register_and_activate_plugin():
    db = SessionLocal()
    try:
        plugin = infinity_extension_service.register_plugin(db, plugin_key=uid("plugin-activate"), name="Widget Pack", registered_by="admin")
        assert plugin["status"] == "draft"
        activated = infinity_extension_service.activate_plugin(db, plugin["plugin_key"])
        assert activated["status"] == "active"
        disabled = infinity_extension_service.disable_plugin(db, plugin["plugin_key"])
        assert disabled["status"] == "disabled"
    finally:
        db.close()


def test_plugin_route_requires_membership():
    tenant_id = uid("infinity-plugin-route")
    resp_denied = client.get("/api/infinity/plugins", headers=_headers(AUTH_VIEWER, tenant_id))
    assert resp_denied.status_code == 403

    db = SessionLocal()
    try:
        _seed_membership(db, tenant_id, role="viewer")
    finally:
        db.close()
    resp = client.get("/api/infinity/plugins", headers=_headers(AUTH_VIEWER, tenant_id))
    assert resp.status_code == 200


# ── 3. Marketplace ─────────────────────────────────────────────────────────────

def test_marketplace_listing_lifecycle_requires_certification_before_publish():
    db = SessionLocal()
    try:
        developer = _make_developer(db)
        listing = infinity_marketplace_service.create_listing(
            db, developer["id"], listing_type="ai_skill", name="Forecast Pro", category="forecast",
        )
        assert listing["status"] == "private"

        try:
            infinity_marketplace_service.publish_listing(db, listing["id"])
            assert False, "expected ListingNotCertifiedError"
        except infinity_marketplace_service.ListingNotCertifiedError:
            pass

        infinity_certification_service.start_certification(db, listing["id"])
        for gate in ["security", "performance", "clinical_safety", "explainability", "accessibility", "documentation", "governance"]:
            infinity_certification_service.advance_certification(
                db, listing["id"], decided_by="admin@local.dev", decided_role=gate, decision="approved",
            )
        published = infinity_marketplace_service.publish_listing(db, listing["id"])
        assert published["status"] == "published"
    finally:
        db.close()


def test_marketplace_install_requires_published_listing():
    db = SessionLocal()
    try:
        developer = _make_developer(db)
        listing = infinity_marketplace_service.create_listing(db, developer["id"], listing_type="application", name="Unpublished App")
        try:
            infinity_marketplace_service.install_listing(db, uid("tenant"), listing["id"], installed_by="admin")
            assert False, "expected ValueError"
        except ValueError:
            pass
    finally:
        db.close()


def test_marketplace_route_install_and_uninstall():
    tenant_id = uid("infinity-marketplace-route")
    db = SessionLocal()
    try:
        _seed_membership(db, tenant_id, role="admin")
        developer = _make_developer(db)
        listing = infinity_marketplace_service.create_listing(db, developer["id"], listing_type="ai_skill", name="Route Skill", category="education")
        infinity_certification_service.start_certification(db, listing["id"])
        for gate in ["security", "performance", "clinical_safety", "explainability", "accessibility", "documentation", "governance"]:
            infinity_certification_service.advance_certification(db, listing["id"], decided_by="admin", decided_role=gate, decision="approved")
        infinity_marketplace_service.publish_listing(db, listing["id"])
        listing_id = listing["id"]
    finally:
        db.close()

    resp = client.post("/api/infinity/marketplace/installations", json={"listing_id": listing_id}, headers=_headers(AUTH_ADMIN, tenant_id))
    assert resp.status_code == 201
    installation_id = resp.json()["id"]

    resp_uninstall = client.post(f"/api/infinity/marketplace/installations/{installation_id}/uninstall", headers=_headers(AUTH_ADMIN, tenant_id))
    assert resp_uninstall.status_code == 200
    assert resp_uninstall.json()["status"] == "disabled"


# ── 4. Security (developer API keys + tenant-membership auth) ────────────────

def test_developer_api_key_issuance_and_authentication():
    db = SessionLocal()
    try:
        developer = _make_developer(db)
        issued = infinity_developer_service.issue_api_key(db, developer["id"], scopes=["marketplace:read"])
        assert "api_key" in issued
        raw_key = issued["api_key"]

        authenticated = infinity_developer_service.authenticate_api_key(db, raw_key)
        assert authenticated is not None
        assert authenticated.developer_account_id == developer["id"]

        revoked = infinity_developer_service.revoke_api_key(db, developer["id"], issued["id"])
        assert revoked["revoked"] is True
        assert infinity_developer_service.authenticate_api_key(db, raw_key) is None
    finally:
        db.close()


def test_developer_portal_me_requires_developer_key():
    resp_missing = client.get("/api/infinity/developer-portal/me")
    assert resp_missing.status_code == 401

    resp_invalid = client.get("/api/infinity/developer-portal/me", headers={"X-Infinity-Developer-Key": "not-a-real-key"})
    assert resp_invalid.status_code == 401

    db = SessionLocal()
    try:
        developer = _make_developer(db)
        issued = infinity_developer_service.issue_api_key(db, developer["id"])
        raw_key = issued["api_key"]
    finally:
        db.close()

    resp_valid = client.get("/api/infinity/developer-portal/me", headers={"X-Infinity-Developer-Key": raw_key})
    assert resp_valid.status_code == 200
    assert resp_valid.json()["account"]["id"] == developer["id"]


def test_developer_account_route_requires_leadership_membership():
    tenant_id = uid("infinity-security")
    resp_no_member = client.post(
        "/api/infinity/developer-accounts", json={"email": "x@example.com", "organization_name": "X", "developer_type": "hospital"},
        headers=_headers(AUTH_ADMIN, tenant_id),
    )
    assert resp_no_member.status_code == 403


# ── 5. API Versioning ──────────────────────────────────────────────────────────

def test_v1_gateway_new_infinity_endpoints_require_auth():
    resp = client.get("/api/v1/phoenix")
    assert resp.status_code == 401


def test_v1_gateway_new_endpoints_return_api_version():
    tenant_id = uid("infinity-v1")
    for path in ("/api/v1/identity", "/api/v1/users", "/api/v1/athena", "/api/v1/apollo"):
        resp = client.get(path, headers=_headers(AUTH_VIEWER, tenant_id))
        assert resp.status_code == 200, path
        assert resp.json()["api_version"] == "v1"


# ── 6. Licensing ───────────────────────────────────────────────────────────────

def test_module_licensing_summary_composes_genesis_licensing():
    tenant_id = uid("infinity-license")
    db = SessionLocal()
    try:
        result = infinity_billing_service.module_licensing_summary(db, tenant_id)
    finally:
        db.close()
    assert result["tenant_id"] == tenant_id
    assert "licenses" in result


def test_partner_license_create_and_revoke():
    db = SessionLocal()
    try:
        developer = _make_developer(db)
        license_row = infinity_billing_service.create_partner_license(
            db, license_type="partner", developer_account_id=developer["id"], revenue_share_pct=80.0,
        )
        assert license_row["status"] == "active"
        revoked = infinity_billing_service.revoke_partner_license(db, license_row["id"])
        assert revoked["status"] == "revoked"
    finally:
        db.close()


def test_revenue_event_splits_gross_amount():
    db = SessionLocal()
    try:
        developer = _make_developer(db)
        listing = infinity_marketplace_service.create_listing(db, developer["id"], listing_type="application", name="Revenue Test App")
        event = infinity_billing_service.record_revenue_event(
            db, listing["id"], uid("tenant"), event_type="subscription_charge", gross_amount_cents=10000, developer_share_pct=70.0,
        )
        assert event["developer_share_cents"] == 7000
        assert event["platform_share_cents"] == 3000

        summary = infinity_billing_service.revenue_summary_for_listing(db, listing["id"])
        assert summary["total_gross_cents"] == 10000
    finally:
        db.close()


# ── 7. Certification ───────────────────────────────────────────────────────────

def test_certification_reuses_forge_approval_chain():
    db = SessionLocal()
    try:
        developer = _make_developer(db)
        listing = infinity_marketplace_service.create_listing(db, developer["id"], listing_type="ai_skill", name="Cert Test Skill")
        started = infinity_certification_service.start_certification(db, listing["id"])
        assert started["chain"]["steps"] == [
            "security", "performance", "clinical_safety", "explainability", "accessibility", "documentation", "governance",
        ]

        status = infinity_certification_service.get_certification_status(db, listing["id"])
        assert status["certification_status"] == "in_progress"
    finally:
        db.close()


def test_certification_rejection_stops_the_chain():
    db = SessionLocal()
    try:
        developer = _make_developer(db)
        listing = infinity_marketplace_service.create_listing(db, developer["id"], listing_type="ai_skill", name="Rejected Skill")
        infinity_certification_service.start_certification(db, listing["id"])
        result = infinity_certification_service.advance_certification(
            db, listing["id"], decided_by="admin", decided_role="security", decision="rejected", notes="Fails security scan.",
        )
        assert result["certification_status"] == "rejected"
    finally:
        db.close()


# ── 8. Sandbox ──────────────────────────────────────────────────────────────────

def test_sandbox_session_scoped_to_synthetic_tenant():
    db = SessionLocal()
    try:
        developer = _make_developer(db)
        session = infinity_sandbox_service.create_sandbox_session(db, developer["id"], purpose="development")
        assert infinity_sandbox_service.is_sandbox_tenant(session["sandbox_tenant_id"])
        assert session["status"] == "active"

        terminated = infinity_sandbox_service.terminate_sandbox_session(db, session["id"])
        assert terminated["status"] == "terminated"
    finally:
        db.close()


def test_sandbox_session_rejects_invalid_purpose():
    db = SessionLocal()
    try:
        developer = _make_developer(db)
        try:
            infinity_sandbox_service.create_sandbox_session(db, developer["id"], purpose="not_a_purpose")
            assert False, "expected ValueError"
        except ValueError:
            pass
    finally:
        db.close()


def test_expire_stale_sandbox_sessions():
    db = SessionLocal()
    try:
        developer = _make_developer(db)
        session = infinity_sandbox_service.create_sandbox_session(db, developer["id"], purpose="testing", lifetime_hours=-1)
        expired = infinity_sandbox_service.expire_stale_sessions(db)
    finally:
        db.close()
    assert any(s["id"] == session["id"] for s in expired)
