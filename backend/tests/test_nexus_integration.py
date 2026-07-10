"""v3.2 — Project Nexus: Connected Healthcare Intelligence Platform tests."""
from __future__ import annotations

import time

from fastapi.testclient import TestClient

from app.db.session import SessionLocal
from app.main import app
from app.models.audit_log import AuditLog
from app.models.inspection import Inspection
from app.models.knowledge import APPROVED

client = TestClient(app)
AUTH_ADMIN = {"Authorization": "Bearer dev-token"}
AUTH_MGR = {"Authorization": "Bearer manager-token"}
AUTH_VIEWER = {"Authorization": "Bearer viewer-token"}
AUTH_VENDOR = {"Authorization": "Bearer vendor-token"}

_counter = [0]


def uid(prefix: str) -> str:
    _counter[0] += 1
    return f"{prefix}-{int(time.time() * 1000) % 1_000_000}-{_counter[0]}"


def _make_inspection(tenant_id: str, **overrides) -> int:
    db = SessionLocal()
    try:
        defaults = dict(
            tenant_id=tenant_id, file_name="x.jpg", instrument_type="kerrison_rongeur",
            has_image=True, image_sha256="b2" * 32, score_status="scored", risk_score=10,
            detected_issue="none", stain_detected=False, supervisor_review_required=False,
            qa_review_status="pending", status="pending", inspected_zones_json="null",
            coverage_pct=100, baseline_status="approved", disposition="PASS", technician="Alex Tech",
        )
        defaults.update(overrides)
        insp = Inspection(**defaults)
        db.add(insp)
        db.commit()
        db.refresh(insp)
        return insp.id
    finally:
        db.close()


def _make_article(tenant_id: str) -> int:
    from app.models.knowledge import KnowledgeArticle
    db = SessionLocal()
    try:
        row = KnowledgeArticle(tenant_id=tenant_id, category="best_practice", title="Nexus Test Article", body="Body.", author="a@x.org", approval_status=APPROVED)
        db.add(row)
        db.commit()
        db.refresh(row)
        return row.id
    finally:
        db.close()


def _register(tenant_id: str, connector_key: str, headers=AUTH_MGR) -> dict:
    res = client.post("/api/nexus/connectors", json={"connector_key": connector_key}, headers={**headers, "x-tenant-id": tenant_id})
    assert res.status_code == 200, res.text
    return res.json()


def _headers(base: dict, tenant_id: str) -> dict:
    return {**base, "x-tenant-id": tenant_id}


class TestConnectorRegistration:
    def test_catalog_lists_all_required_connector_types(self):
        res = client.get("/api/nexus/catalog", headers=AUTH_VIEWER)
        assert res.status_code == 200
        keys = {c["connector_key"] for c in res.json()["catalog"]}
        assert keys == {"censitrac", "spm", "epic", "cerner", "oracle_erp", "sap", "cmms", "active_directory", "sso_oidc", "sso_saml"}

    def test_register_connector_from_catalog(self):
        tenant_id = uid("tenant")
        row = _register(tenant_id, "epic")
        assert row["connector_key"] == "epic"
        assert row["category"] == "ehr"
        assert row["status"] == "disabled"

    def test_register_unknown_connector_key_rejected(self):
        tenant_id = uid("tenant")
        res = client.post("/api/nexus/connectors", json={"connector_key": "not_a_real_connector"}, headers=_headers(AUTH_MGR, tenant_id))
        assert res.status_code == 422

    def test_register_is_idempotent(self):
        tenant_id = uid("tenant")
        first = _register(tenant_id, "sap")
        second = _register(tenant_id, "sap")
        assert first["id"] == second["id"]

    def test_enable_disable_and_version_bump(self):
        tenant_id = uid("tenant")
        connector = _register(tenant_id, "cmms")
        cid = connector["id"]

        enabled = client.post(f"/api/nexus/connectors/{cid}/enable", headers=_headers(AUTH_MGR, tenant_id))
        assert enabled.status_code == 200
        assert enabled.json()["status"] == "enabled"

        disabled = client.post(f"/api/nexus/connectors/{cid}/disable", headers=_headers(AUTH_MGR, tenant_id))
        assert disabled.json()["status"] == "disabled"

        versioned = client.post(f"/api/nexus/connectors/{cid}/version", json={"version": "2.1.0"}, headers=_headers(AUTH_MGR, tenant_id))
        assert versioned.status_code == 200
        assert versioned.json()["version"] == "2.1.0"

    def test_unknown_connector_404s(self):
        tenant_id = uid("tenant")
        res = client.get("/api/nexus/connectors/999999", headers=_headers(AUTH_ADMIN, tenant_id))
        assert res.status_code == 404


class TestConnectorCredentialsAndAuthentication:
    def test_issue_credential_returns_raw_key_once_and_never_again(self):
        tenant_id = uid("tenant")
        connector = _register(tenant_id, "oracle_erp")
        issued = client.post(f"/api/nexus/connectors/{connector['id']}/credentials", json={"scopes": ["sync:read"]}, headers=_headers(AUTH_MGR, tenant_id))
        assert issued.status_code == 200
        body = issued.json()
        assert "api_key" in body and len(body["api_key"]) > 20

        listed = client.get(f"/api/nexus/connectors/{connector['id']}/credentials", headers=_headers(AUTH_MGR, tenant_id)).json()["credentials"]
        assert all("api_key" not in c and "key_hash" not in c for c in listed)

    def test_revoke_credential(self):
        tenant_id = uid("tenant")
        connector = _register(tenant_id, "sap")
        issued = client.post(f"/api/nexus/connectors/{connector['id']}/credentials", json={}, headers=_headers(AUTH_MGR, tenant_id)).json()
        revoked = client.post(f"/api/nexus/connectors/{connector['id']}/credentials/{issued['id']}/revoke", headers=_headers(AUTH_MGR, tenant_id))
        assert revoked.status_code == 200
        assert revoked.json()["revoked"] is True


class TestConnectorHealthAndMonitoring:
    def test_health_check_without_credential(self):
        tenant_id = uid("tenant")
        connector = _register(tenant_id, "cerner")
        res = client.post(f"/api/nexus/connectors/{connector['id']}/health-check", headers=_headers(AUTH_MGR, tenant_id))
        assert res.status_code == 200
        assert "health_status" in res.json()
        assert res.json()["latency_ms"] is not None

    def test_health_check_with_credential(self):
        tenant_id = uid("tenant")
        connector = _register(tenant_id, "cerner")
        client.post(f"/api/nexus/connectors/{connector['id']}/credentials", json={}, headers=_headers(AUTH_MGR, tenant_id))
        res = client.post(f"/api/nexus/connectors/{connector['id']}/health-check", headers=_headers(AUTH_MGR, tenant_id))
        assert res.status_code == 200

    def test_monitoring_dashboard_reflects_auth_status(self):
        tenant_id = uid("tenant")
        connector = _register(tenant_id, "spm")
        dash = client.get("/api/nexus/dashboard", headers=_headers(AUTH_VIEWER, tenant_id)).json()
        row = next(c for c in dash["connectors"] if c["connector_id"] == connector["id"])
        assert row["authentication_status"] == "not_configured"

        client.post(f"/api/nexus/connectors/{connector['id']}/credentials", json={}, headers=_headers(AUTH_MGR, tenant_id))
        dash2 = client.get("/api/nexus/dashboard", headers=_headers(AUTH_VIEWER, tenant_id)).json()
        row2 = next(c for c in dash2["connectors"] if c["connector_id"] == connector["id"])
        assert row2["authentication_status"] == "configured"


class TestSynchronizationLogic:
    def test_sync_assets_creates_records_and_links_digital_twin(self):
        tenant_id = uid("tenant")
        connector = _register(tenant_id, "censitrac")
        res = client.post(f"/api/nexus/connectors/{connector['id']}/sync/assets", json={
            "asset_type": "instrument",
            "external_records": [
                {"external_id": "INST-1", "manufacturer": "Acme", "model": "X1", "repair_status": "none", "location": "OR-3", "digital_twin_instrument_id": "twin-inst-1"},
            ],
        }, headers=_headers(AUTH_MGR, tenant_id))
        assert res.status_code == 200
        body = res.json()
        assert body["processed"] == 1
        assert body["failed"] == 0

        assets = client.get(f"/api/nexus/connectors/{connector['id']}/synced-assets", headers=_headers(AUTH_VIEWER, tenant_id)).json()["assets"]
        assert len(assets) == 1
        assert assets[0]["source_system"] == "censitrac"
        assert assets[0]["digital_twin_instrument_id"] == "twin-inst-1"

    def test_sync_assets_without_external_id_counts_as_failed(self):
        tenant_id = uid("tenant")
        connector = _register(tenant_id, "spm")
        res = client.post(f"/api/nexus/connectors/{connector['id']}/sync/assets", json={
            "asset_type": "tray", "external_records": [{"manufacturer": "NoId"}],
        }, headers=_headers(AUTH_MGR, tenant_id))
        assert res.status_code == 200
        assert res.json()["failed"] == 1
        assert res.json()["processed"] == 0

    def test_sync_assets_upsert_detects_conflict(self):
        tenant_id = uid("tenant")
        connector = _register(tenant_id, "censitrac")
        client.post(f"/api/nexus/connectors/{connector['id']}/sync/assets", json={
            "asset_type": "instrument", "external_records": [{"external_id": "INST-2", "manufacturer": "Acme"}],
        }, headers=_headers(AUTH_MGR, tenant_id))
        second = client.post(f"/api/nexus/connectors/{connector['id']}/sync/assets", json={
            "asset_type": "instrument", "external_records": [{"external_id": "INST-2", "manufacturer": "OtherCo"}],
        }, headers=_headers(AUTH_MGR, tenant_id))
        assert second.json()["conflicts"] == 1

        assets = client.get(f"/api/nexus/connectors/{connector['id']}/synced-assets", headers=_headers(AUTH_VIEWER, tenant_id)).json()["assets"]
        assert len(assets) == 1
        assert assets[0]["manufacturer"] == "OtherCo"
        assert assets[0]["conflict_resolution"] == "external_wins"


class TestWorkQueueSynchronization:
    def test_sync_work_queue_requires_real_internal_record(self):
        tenant_id = uid("tenant")
        connector = _register(tenant_id, "cmms")
        res = client.post(f"/api/nexus/connectors/{connector['id']}/sync/work-queue", json={
            "queue_type": "inspection", "internal_ref_id": "999999",
        }, headers=_headers(AUTH_MGR, tenant_id))
        assert res.status_code == 404

    def test_sync_work_queue_links_real_inspection(self):
        tenant_id = uid("tenant")
        connector = _register(tenant_id, "cmms")
        inspection_id = _make_inspection(tenant_id)
        res = client.post(f"/api/nexus/connectors/{connector['id']}/sync/work-queue", json={
            "queue_type": "inspection", "internal_ref_id": str(inspection_id), "external_ref_id": "CMMS-77",
        }, headers=_headers(AUTH_MGR, tenant_id))
        assert res.status_code == 200
        assert res.json()["external_ref_id"] == "CMMS-77"
        assert res.json()["sync_direction"] == "import_only"

        links = client.get(f"/api/nexus/connectors/{connector['id']}/work-queue-links", headers=_headers(AUTH_VIEWER, tenant_id)).json()["links"]
        assert len(links) == 1

    def test_invalid_queue_type_rejected(self):
        tenant_id = uid("tenant")
        connector = _register(tenant_id, "cmms")
        res = client.post(f"/api/nexus/connectors/{connector['id']}/sync/work-queue", json={
            "queue_type": "not_a_queue", "internal_ref_id": "1",
        }, headers=_headers(AUTH_MGR, tenant_id))
        assert res.status_code == 422


class TestIdentityIntegrationAndRoleMapping:
    def test_create_and_resolve_role_mapping(self):
        tenant_id = uid("tenant")
        connector = _register(tenant_id, "active_directory")
        client.post(f"/api/nexus/connectors/{connector['id']}/identity-mappings", json={
            "external_group": "SPD-Supervisors", "mapped_role": "supervisor",
        }, headers=_headers(AUTH_MGR, tenant_id))

        resolved = client.post("/api/nexus/identity/resolve-role", json={
            "connector_id": connector["id"], "external_groups": ["SPD-Supervisors", "Some-Other-Group"],
        }, headers=_headers(AUTH_ADMIN, tenant_id))
        assert resolved.status_code == 200
        assert resolved.json()["mapped_role"] == "supervisor"

    def test_resolve_role_defaults_to_least_privilege_viewer(self):
        tenant_id = uid("tenant")
        connector = _register(tenant_id, "sso_oidc")
        resolved = client.post("/api/nexus/identity/resolve-role", json={
            "connector_id": connector["id"], "external_groups": ["Unmapped-Group"],
        }, headers=_headers(AUTH_ADMIN, tenant_id))
        assert resolved.json()["mapped_role"] == "viewer"
        assert resolved.json()["matched_groups"] == []

    def test_invalid_mapped_role_rejected(self):
        tenant_id = uid("tenant")
        connector = _register(tenant_id, "active_directory")
        res = client.post(f"/api/nexus/connectors/{connector['id']}/identity-mappings", json={
            "external_group": "X", "mapped_role": "superuser",
        }, headers=_headers(AUTH_MGR, tenant_id))
        assert res.status_code == 422

    def test_higher_precedence_role_wins_on_multiple_matches(self):
        tenant_id = uid("tenant")
        connector = _register(tenant_id, "sso_saml")
        client.post(f"/api/nexus/connectors/{connector['id']}/identity-mappings", json={"external_group": "Techs", "mapped_role": "technician"}, headers=_headers(AUTH_MGR, tenant_id))
        client.post(f"/api/nexus/connectors/{connector['id']}/identity-mappings", json={"external_group": "Admins", "mapped_role": "administrator"}, headers=_headers(AUTH_MGR, tenant_id))

        resolved = client.post("/api/nexus/identity/resolve-role", json={
            "connector_id": connector["id"], "external_groups": ["Techs", "Admins"],
        }, headers=_headers(AUTH_ADMIN, tenant_id))
        assert resolved.json()["mapped_role"] == "administrator"


class TestEventBus:
    def test_publish_and_list_events(self):
        tenant_id = uid("tenant")
        res = client.post("/api/nexus/events/publish", json={
            "event_type": "InspectionCompleted", "payload": {"inspection_id": 1},
        }, headers=_headers(AUTH_ADMIN, tenant_id))
        assert res.status_code == 200
        assert res.json()["event_type"] == "InspectionCompleted"

        listed = client.get("/api/nexus/events", headers=_headers(AUTH_VIEWER, tenant_id)).json()["events"]
        assert len(listed) == 1

    def test_invalid_event_type_rejected(self):
        tenant_id = uid("tenant")
        res = client.post("/api/nexus/events/publish", json={"event_type": "NotARealEvent", "payload": {}}, headers=_headers(AUTH_ADMIN, tenant_id))
        assert res.status_code == 422

    def test_internal_subscription_receives_delivery_count(self):
        tenant_id = uid("tenant")
        client.post("/api/nexus/events/subscriptions", json={
            "event_type": "KnowledgeUpdated", "target_type": "internal", "target": "internal-handler",
        }, headers=_headers(AUTH_MGR, tenant_id))

        published = client.post("/api/nexus/events/publish", json={
            "event_type": "KnowledgeUpdated", "payload": {"article_id": 5},
        }, headers=_headers(AUTH_ADMIN, tenant_id))
        assert published.json()["subscriber_delivery_count"] == 1

    def test_deactivated_subscription_not_delivered(self):
        tenant_id = uid("tenant")
        sub = client.post("/api/nexus/events/subscriptions", json={
            "event_type": "BaselinePublished", "target_type": "internal", "target": "handler",
        }, headers=_headers(AUTH_MGR, tenant_id)).json()
        client.post(f"/api/nexus/events/subscriptions/{sub['id']}/deactivate", headers=_headers(AUTH_MGR, tenant_id))

        published = client.post("/api/nexus/events/publish", json={
            "event_type": "BaselinePublished", "payload": {},
        }, headers=_headers(AUTH_ADMIN, tenant_id))
        assert published.json()["subscriber_delivery_count"] == 0


class TestAPIGatewayVersioningAndAuth:
    def test_v1_instruments_requires_authentication(self):
        res = client.get("/api/v1/instruments")
        assert res.status_code == 401

    def test_v1_instruments_with_bearer_token(self):
        tenant_id = uid("tenant")
        _make_inspection(tenant_id)
        res = client.get("/api/v1/instruments", headers=_headers(AUTH_VIEWER, tenant_id))
        assert res.status_code == 200
        body = res.json()
        assert body["api_version"] == "v1"
        assert len(body["instruments"]) == 1

    def test_v1_gateway_with_connector_api_key(self):
        tenant_id = uid("tenant")
        _make_inspection(tenant_id)
        connector = _register(tenant_id, "epic")
        issued = client.post(f"/api/nexus/connectors/{connector['id']}/credentials", json={}, headers=_headers(AUTH_MGR, tenant_id)).json()

        res = client.get("/api/v1/inspections", headers={"X-Nexus-Api-Key": issued["api_key"]})
        assert res.status_code == 200
        assert res.json()["tenant_id"] == tenant_id

    def test_v1_gateway_rejects_revoked_key(self):
        tenant_id = uid("tenant")
        connector = _register(tenant_id, "epic")
        issued = client.post(f"/api/nexus/connectors/{connector['id']}/credentials", json={}, headers=_headers(AUTH_MGR, tenant_id)).json()
        client.post(f"/api/nexus/connectors/{connector['id']}/credentials/{issued['id']}/revoke", headers=_headers(AUTH_MGR, tenant_id))

        res = client.get("/api/v1/inspections", headers={"X-Nexus-Api-Key": issued["api_key"]})
        assert res.status_code == 401

    def test_v1_knowledge_returns_only_approved_articles(self):
        tenant_id = uid("tenant")
        _make_article(tenant_id)
        res = client.get("/api/v1/knowledge", headers=_headers(AUTH_VIEWER, tenant_id))
        assert res.status_code == 200
        assert len(res.json()["knowledge"]) == 1

    def test_v1_enterprise_requires_system_id(self):
        tenant_id = uid("tenant")
        res = client.get("/api/v1/enterprise", headers=_headers(AUTH_VIEWER, tenant_id))
        assert res.status_code == 422


class TestAuditLogging:
    def test_connector_registration_is_audited(self):
        tenant_id = uid("tenant")
        connector = _register(tenant_id, "sap")
        db = SessionLocal()
        try:
            entry = db.query(AuditLog).filter(
                AuditLog.tenant_id == tenant_id, AuditLog.action_type == "nexus.connector_registered",
                AuditLog.resource_id == str(connector["id"]),
            ).first()
            assert entry is not None
        finally:
            db.close()

    def test_credential_issuance_is_audited(self):
        tenant_id = uid("tenant")
        connector = _register(tenant_id, "cmms")
        client.post(f"/api/nexus/connectors/{connector['id']}/credentials", json={}, headers=_headers(AUTH_MGR, tenant_id))
        db = SessionLocal()
        try:
            entry = db.query(AuditLog).filter(
                AuditLog.tenant_id == tenant_id, AuditLog.action_type == "nexus.credential_issued",
            ).first()
            assert entry is not None
        finally:
            db.close()
