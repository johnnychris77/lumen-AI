"""v4.0 — LumenAI OS: Project Genesis — Platform Core tests."""
from __future__ import annotations

import time

from fastapi.testclient import TestClient

from app.db.session import SessionLocal
from app.main import app
from app.models.inspection import Inspection
from app.models.knowledge import KnowledgeArticle
from app.models.mobile import MobileNotification
from app.models.or_connect import CaseNotification

client = TestClient(app)
AUTH_ADMIN = {"Authorization": "Bearer dev-token"}
AUTH_MGR = {"Authorization": "Bearer manager-token"}
AUTH_VIEWER = {"Authorization": "Bearer viewer-token"}

_counter = [0]


def uid(prefix: str) -> str:
    _counter[0] += 1
    return f"{prefix}-{int(time.time() * 1000) % 1_000_000}-{_counter[0]}"


def _headers(base: dict, tenant_id: str) -> dict:
    return {**base, "x-tenant-id": tenant_id}


def _make_inspection(tenant_id: str, *, file_name: str, instrument_type: str = "kerrison_rongeur") -> int:
    db = SessionLocal()
    try:
        insp = Inspection(tenant_id=tenant_id, file_name=file_name, instrument_type=instrument_type, status="pending")
        db.add(insp)
        db.commit()
        db.refresh(insp)
        return insp.id
    finally:
        db.close()


def _make_knowledge_article(tenant_id: str, *, title: str) -> int:
    db = SessionLocal()
    try:
        article = KnowledgeArticle(tenant_id=tenant_id, category="best_practice", title=title, body="body text")
        db.add(article)
        db.commit()
        db.refresh(article)
        return article.id
    finally:
        db.close()


def _make_case_notification(tenant_id: str, *, message: str, recipient_role: str = "spd_manager") -> None:
    db = SessionLocal()
    try:
        db.add(CaseNotification(tenant_id=tenant_id, case_id=1, notification_type="case_update", recipient_role=recipient_role, message=message))
        db.commit()
    finally:
        db.close()


def _make_mobile_notification(tenant_id: str, *, title: str) -> None:
    db = SessionLocal()
    try:
        db.add(MobileNotification(tenant_id=tenant_id, recipient_id="tech-1", notification_type="alert", title=title, body="detail"))
        db.commit()
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Section 3 — Module loading
# ---------------------------------------------------------------------------


def test_modules_load_all_ten_named_modules():
    res = client.get("/api/platform/modules", headers=AUTH_VIEWER)
    assert res.status_code == 200, res.text
    modules = res.json()["modules"]
    keys = {m["module_key"] for m in modules}
    assert keys == {
        "inspect", "twin", "knowledge", "analytics", "command",
        "connect", "academy", "research", "developer", "marketplace",
    }
    for m in modules:
        assert m["routes"], f"module {m['module_key']} has no routes"
        assert m["permissions"], f"module {m['module_key']} has no permissions"


def test_get_single_module_and_404_for_unknown():
    res = client.get("/api/platform/modules/inspect", headers=AUTH_VIEWER)
    assert res.status_code == 200, res.text
    assert res.json()["module_key"] == "inspect"

    res404 = client.get("/api/platform/modules/not_a_real_module", headers=AUTH_VIEWER)
    assert res404.status_code == 404


# ---------------------------------------------------------------------------
# Section 8 — Plugin registration
# ---------------------------------------------------------------------------


def test_plugin_registration_lifecycle():
    plugin_key = uid("acme-plugin")
    res = client.post(
        "/api/platform/plugins",
        json={"plugin_key": plugin_key, "name": "Acme Plugin", "routes": ["/acme"], "widgets": ["acme-widget"]},
        headers=AUTH_ADMIN,
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["status"] == "draft"
    assert body["registered_routes"] == ["/acme"]

    dup = client.post("/api/platform/plugins", json={"plugin_key": plugin_key, "name": "Dup"}, headers=AUTH_ADMIN)
    assert dup.status_code == 409

    activate = client.post(f"/api/platform/plugins/{plugin_key}/activate", headers=AUTH_ADMIN)
    assert activate.status_code == 200
    assert activate.json()["status"] == "active"

    listing = client.get("/api/platform/plugins", params={"status": "active"}, headers=AUTH_VIEWER)
    assert listing.status_code == 200
    assert any(p["plugin_key"] == plugin_key for p in listing.json()["plugins"])

    disable = client.post(f"/api/platform/plugins/{plugin_key}/disable", headers=AUTH_ADMIN)
    assert disable.status_code == 200
    assert disable.json()["status"] == "disabled"


def test_plugin_activate_unknown_key_404():
    res = client.post(f"/api/platform/plugins/{uid('missing')}/activate", headers=AUTH_ADMIN)
    assert res.status_code == 404


def test_plugin_registration_requires_admin_role():
    res = client.post(
        "/api/platform/plugins", json={"plugin_key": uid("blocked"), "name": "Blocked"}, headers=AUTH_VIEWER,
    )
    assert res.status_code == 403


# ---------------------------------------------------------------------------
# Section 1 — Licensing
# ---------------------------------------------------------------------------


def test_module_unlicensed_by_default_is_enabled():
    tenant_id = uid("hospital")
    res = client.get("/api/platform/licenses", headers=_headers(AUTH_ADMIN, tenant_id))
    assert res.status_code == 200, res.text
    licenses = res.json()["licenses"]
    assert licenses["inspect"]["status"] == "enabled"
    assert licenses["inspect"].get("implicit") is True


def test_disabling_a_module_license_removes_it_from_launcher():
    tenant_id = uid("hospital")
    disable = client.post(
        "/api/platform/licenses", json={"module_key": "marketplace", "status": "disabled"}, headers=_headers(AUTH_ADMIN, tenant_id),
    )
    assert disable.status_code == 200, disable.text

    launcher = client.get("/api/platform/navigation/launcher", headers=_headers(AUTH_ADMIN, tenant_id))
    assert launcher.status_code == 200, launcher.text
    module_keys = {m["module_key"] for m in launcher.json()["modules"]}
    assert "marketplace" not in module_keys
    assert "inspect" in module_keys


def test_set_license_rejects_unknown_module_and_status():
    tenant_id = uid("hospital")
    bad_module = client.post(
        "/api/platform/licenses", json={"module_key": "not_a_module", "status": "enabled"}, headers=_headers(AUTH_ADMIN, tenant_id),
    )
    assert bad_module.status_code == 422

    bad_status = client.post(
        "/api/platform/licenses", json={"module_key": "inspect", "status": "not_a_status"}, headers=_headers(AUTH_ADMIN, tenant_id),
    )
    assert bad_status.status_code == 422


# ---------------------------------------------------------------------------
# Section 1/4 — Permissions (role-gated module visibility)
# ---------------------------------------------------------------------------


def test_developer_module_hidden_from_non_admin_role():
    tenant_id = uid("hospital")
    launcher_viewer = client.get("/api/platform/navigation/launcher", headers=_headers(AUTH_VIEWER, tenant_id))
    assert launcher_viewer.status_code == 200
    viewer_keys = {m["module_key"] for m in launcher_viewer.json()["modules"]}
    assert "developer" not in viewer_keys  # developer module permissions = ["admin"] only

    launcher_admin = client.get("/api/platform/navigation/launcher", headers=_headers(AUTH_ADMIN, tenant_id))
    admin_keys = {m["module_key"] for m in launcher_admin.json()["modules"]}
    assert "developer" in admin_keys


def test_identity_and_roles_endpoints():
    me = client.get("/api/platform/identity/me", headers=AUTH_MGR)
    assert me.status_code == 200, me.text
    assert me.json()["role"] == "spd_manager"

    roles = client.get("/api/platform/identity/roles", headers=AUTH_VIEWER)
    assert roles.status_code == 200
    assert "spd_manager" in roles.json()["roles"]
    assert "enterprise_admin" in roles.json()["roles"]


# ---------------------------------------------------------------------------
# Section 4 — Navigation (favorites / recents)
# ---------------------------------------------------------------------------


def test_favorites_and_recents_appear_in_launcher():
    tenant_id = uid("hospital")
    fav = client.post("/api/platform/navigation/favorites/knowledge", headers=_headers(AUTH_ADMIN, tenant_id))
    assert fav.status_code == 200, fav.text

    recent = client.post("/api/platform/navigation/recent", json={"module_key": "analytics"}, headers=_headers(AUTH_ADMIN, tenant_id))
    assert recent.status_code == 200

    launcher = client.get("/api/platform/navigation/launcher", headers=_headers(AUTH_ADMIN, tenant_id))
    assert launcher.status_code == 200
    body = launcher.json()
    assert any(m["module_key"] == "knowledge" for m in body["favorites"])
    assert any(m["module_key"] == "analytics" for m in body["recent"])

    unfav = client.delete("/api/platform/navigation/favorites/knowledge", headers=_headers(AUTH_ADMIN, tenant_id))
    assert unfav.status_code == 200
    unfav_again = client.delete("/api/platform/navigation/favorites/knowledge", headers=_headers(AUTH_ADMIN, tenant_id))
    assert unfav_again.status_code == 404


# ---------------------------------------------------------------------------
# Section 1 — Notification Engine (unified feed)
# ---------------------------------------------------------------------------


def test_unified_notifications_compose_all_three_sources():
    tenant_id = uid("hospital")
    _make_case_notification(tenant_id, message="Case notification X")
    _make_mobile_notification(tenant_id, title="Mobile notification Y")

    res = client.get("/api/platform/notifications", headers=_headers(AUTH_ADMIN, tenant_id))
    assert res.status_code == 200, res.text
    messages = [n["message"] for n in res.json()["notifications"]]
    assert "Case notification X" in messages
    assert "Mobile notification Y" in messages


# ---------------------------------------------------------------------------
# Section 1 — Configuration
# ---------------------------------------------------------------------------


def test_configuration_set_and_get_tenant_override():
    tenant_id = uid("hospital")
    global_set = client.post(
        "/api/platform/configuration", json={"config_key": "theme", "config_value": "light", "scope": "global"}, headers=AUTH_ADMIN,
    )
    assert global_set.status_code == 200, global_set.text

    tenant_set = client.post(
        "/api/platform/configuration", json={"config_key": "theme", "config_value": "dark"}, headers=_headers(AUTH_ADMIN, tenant_id),
    )
    assert tenant_set.status_code == 200, tenant_set.text

    configs = client.get("/api/platform/configuration", headers=_headers(AUTH_ADMIN, tenant_id))
    assert configs.status_code == 200
    theme_values = {c["config_key"]: c["config_value"] for c in configs.json()["configuration"]}
    assert theme_values["theme"] == "dark"


# ---------------------------------------------------------------------------
# Section 5 — Global Search
# ---------------------------------------------------------------------------


def test_global_search_finds_inspection_and_knowledge_grouped_by_module():
    tenant_id = uid("hospital")
    unique_term = uid("Zorblatt")
    _make_inspection(tenant_id, file_name=f"{unique_term}.jpg")
    _make_knowledge_article(tenant_id, title=f"Guidance about {unique_term}")

    res = client.get("/api/platform/search", params={"q": unique_term}, headers=_headers(AUTH_ADMIN, tenant_id))
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["total"] >= 2
    assert "inspect" in body["results"]
    assert "knowledge" in body["results"]


def test_global_search_too_short_query_returns_empty():
    res = client.get("/api/platform/search", params={"q": "a"}, headers=AUTH_ADMIN)
    assert res.status_code == 200
    assert res.json()["total"] == 0


# ---------------------------------------------------------------------------
# Section 1/8 — Event Bus
# ---------------------------------------------------------------------------


def test_license_change_and_plugin_registration_publish_events():
    tenant_id = uid("hospital")
    client.post("/api/platform/licenses", json={"module_key": "academy", "status": "trial"}, headers=_headers(AUTH_ADMIN, tenant_id))
    plugin_key = uid("event-plugin")
    client.post("/api/platform/plugins", json={"plugin_key": plugin_key, "name": "Event Plugin"}, headers=_headers(AUTH_ADMIN, tenant_id))

    from app.services import nexus_event_bus_service
    db = SessionLocal()
    try:
        events = nexus_event_bus_service.list_events(db, tenant_id)
        event_types = {e["event_type"] for e in events}
        assert "ModuleLicenseChanged" in event_types
        assert "PluginRegistered" in event_types
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Section 6 — Universal Activity Feed
# ---------------------------------------------------------------------------


def test_activity_feed_includes_platform_actions():
    tenant_id = uid("hospital")
    client.post("/api/platform/licenses", json={"module_key": "research", "status": "disabled"}, headers=_headers(AUTH_ADMIN, tenant_id))

    res = client.get("/api/platform/activity-feed", headers=_headers(AUTH_ADMIN, tenant_id))
    assert res.status_code == 200, res.text
    action_types = [a["action_type"] for a in res.json()["activity"]]
    assert "platform.license_changed" in action_types


# ---------------------------------------------------------------------------
# Section 2 — Shared Intelligence Layer
# ---------------------------------------------------------------------------


def test_intelligence_services_registry():
    res = client.get("/api/platform/intelligence/services", headers=AUTH_VIEWER)
    assert res.status_code == 200, res.text
    body = res.json()
    assert "digital_twin_engine" in body["shared_services"]
    assert "knowledge_graph" in body["shared_services"]
    assert "sentinel" in body["recommendation_engines"]


# ---------------------------------------------------------------------------
# Section 7/9 — Platform APIs + Admin console
# ---------------------------------------------------------------------------


def test_organizations_tree_endpoint():
    res = client.get("/api/platform/organizations/tree", headers=AUTH_VIEWER)
    assert res.status_code == 200, res.text
    body = res.json()
    assert "health_systems" in body and "facilities" in body and "counts" in body


def test_admin_dashboard_requires_admin_role():
    res = client.get("/api/platform/admin/dashboard", headers=AUTH_VIEWER)
    assert res.status_code == 403


def test_admin_dashboard_composes_every_section():
    tenant_id = uid("hospital")
    res = client.get("/api/platform/admin/dashboard", headers=_headers(AUTH_ADMIN, tenant_id))
    assert res.status_code == 200, res.text
    body = res.json()
    for key in ("organizations", "modules", "licenses", "roles", "feature_flags", "api_keys", "integrations", "plugins", "recent_audit_logs"):
        assert key in body


def test_admin_api_keys_never_expose_hash():
    tenant_id = uid("hospital")
    issue = client.post(
        "/api/infrastructure/api-credentials",
        json={"consumer_type": "hospital", "scopes": ["read"]},
        headers=_headers(AUTH_ADMIN, tenant_id),
    )
    assert issue.status_code == 200, issue.text

    admin_keys = client.get("/api/platform/admin/api-keys", headers=_headers(AUTH_ADMIN, tenant_id))
    assert admin_keys.status_code == 200, admin_keys.text
    for key in admin_keys.json()["api_keys"]:
        assert "api_key_hash" not in key


def test_admin_users_never_expose_password_hash():
    res = client.get("/api/platform/admin/users", headers=AUTH_ADMIN)
    assert res.status_code == 200, res.text
    for user in res.json()["users"]:
        assert "hashed_password" not in user


def test_admin_audit_logs_endpoint():
    tenant_id = uid("hospital")
    client.post("/api/platform/licenses", json={"module_key": "connect", "status": "enabled"}, headers=_headers(AUTH_ADMIN, tenant_id))
    res = client.get("/api/platform/admin/audit-logs", headers=_headers(AUTH_ADMIN, tenant_id))
    assert res.status_code == 200, res.text
    assert len(res.json()["audit_logs"]) >= 1
