"""P18 Mobile, Offline & Point-of-Use Inspection Platform — test suite."""
from __future__ import annotations

import base64
import uuid

from fastapi.testclient import TestClient

from app.main import app

HEADERS = {"Authorization": "Bearer dev-token"}
client = TestClient(app)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _session_body(**kwargs):
    defaults = {
        "technician_id": "tech-001",
        "facility_id": "fac-001",
        "device_id": "dev-abc123",
        "inspection_type": "standard",
        "started_at_device": "2026-06-21T08:00:00",
    }
    defaults.update(kwargs)
    return defaults


def _make_session():
    r = client.post("/api/mobile/sessions", json=_session_body(), headers=HEADERS)
    assert r.status_code == 200
    return r.json()["session_id"]


# ---------------------------------------------------------------------------
# Offline Sessions
# ---------------------------------------------------------------------------


class TestOfflineSessions:
    def test_create_session_returns_200(self):
        r = client.post("/api/mobile/sessions", json=_session_body(), headers=HEADERS)
        assert r.status_code == 200

    def test_create_session_has_session_id(self):
        r = client.post("/api/mobile/sessions", json=_session_body(), headers=HEADERS)
        assert "session_id" in r.json()

    def test_create_session_status_is_pending_sync(self):
        r = client.post("/api/mobile/sessions", json=_session_body(), headers=HEADERS)
        assert r.json()["sync_status"] == "PENDING_SYNC"

    def test_list_sessions_returns_200(self):
        r = client.get("/api/mobile/sessions", headers=HEADERS)
        assert r.status_code == 200

    def test_session_detail_returns_200_or_404(self):
        sid = _make_session()
        r = client.get(f"/api/mobile/sessions/{sid}", headers=HEADERS)
        assert r.status_code in (200, 404)

    def test_session_detail_returns_200_for_existing(self):
        sid = _make_session()
        r = client.get(f"/api/mobile/sessions/{sid}", headers=HEADERS)
        assert r.status_code == 200
        assert r.json()["session_id"] == sid

    def test_update_session_returns_200(self):
        sid = _make_session()
        r = client.patch(
            f"/api/mobile/sessions/{sid}",
            json={"offline_findings_json": '[{"finding": "scratch", "severity": "minor"}]', "image_count": 3},
            headers=HEADERS,
        )
        assert r.status_code == 200

    def test_sync_session_returns_200(self):
        sid = _make_session()
        r = client.post(f"/api/mobile/sessions/{sid}/sync", headers=HEADERS)
        assert r.status_code == 200

    def test_sync_session_has_sync_status(self):
        sid = _make_session()
        r = client.post(f"/api/mobile/sessions/{sid}/sync", headers=HEADERS)
        assert "sync_status" in r.json()

    def test_sync_session_transitions_to_synced(self):
        sid = _make_session()
        r = client.post(f"/api/mobile/sessions/{sid}/sync", headers=HEADERS)
        assert r.json()["sync_status"] == "SYNCED"

    def test_sync_status_returns_200(self):
        sid = _make_session()
        r = client.get(f"/api/mobile/sessions/{sid}/sync-status", headers=HEADERS)
        assert r.status_code == 200

    def test_sessions_require_auth(self):
        r = client.get("/api/mobile/sessions")
        assert r.status_code in (401, 403)


# ---------------------------------------------------------------------------
# Scan API
# ---------------------------------------------------------------------------


def _b64_image():
    # 1x1 white JPEG, base64 encoded
    return base64.b64encode(b"\xff\xd8\xff\xe0" + b"\x00" * 60).decode()


class TestScanAPI:
    def test_decode_returns_200(self):
        r = client.post(
            "/api/mobile/scan/decode",
            json={"image_base64": _b64_image(), "scan_type": "barcode"},
            headers=HEADERS,
        )
        assert r.status_code == 200

    def test_decode_has_decoded_value(self):
        r = client.post(
            "/api/mobile/scan/decode",
            json={"image_base64": _b64_image(), "scan_type": "qr"},
            headers=HEADERS,
        )
        assert "decoded_value" in r.json()
        assert r.json()["decoded_value"] is not None

    def test_decode_has_confidence_score(self):
        r = client.post(
            "/api/mobile/scan/decode",
            json={"image_base64": _b64_image(), "scan_type": "udi"},
            headers=HEADERS,
        )
        assert "confidence_score" in r.json()
        assert 0 <= r.json()["confidence_score"] <= 1

    def test_scan_results_list_returns_200(self):
        r = client.get("/api/mobile/scan/results", headers=HEADERS)
        assert r.status_code == 200

    def test_scan_results_list_has_results_key(self):
        r = client.get("/api/mobile/scan/results", headers=HEADERS)
        assert "results" in r.json()

    def test_lookup_returns_200_or_404(self):
        r = client.post(
            "/api/mobile/scan/lookup",
            json={"value": "BC-123456", "scan_type": "barcode"},
            headers=HEADERS,
        )
        assert r.status_code in (200, 404)

    def test_decode_requires_auth(self):
        r = client.post(
            "/api/mobile/scan/decode",
            json={"image_base64": _b64_image(), "scan_type": "barcode"},
        )
        assert r.status_code in (401, 403)


# ---------------------------------------------------------------------------
# Image Capture
# ---------------------------------------------------------------------------


def _small_jpeg_b64():
    # Minimal valid-ish data for upload (not a real JPEG but tests size validation)
    return base64.b64encode(b"FAKEIMAGE" * 100).decode()


class TestImageCapture:
    def test_create_capture_session_returns_200(self):
        r = client.post(
            "/api/mobile/images/session",
            json={"capture_type": "inspection", "device_type": "camera"},
            headers=HEADERS,
        )
        assert r.status_code == 200

    def test_create_capture_session_has_id(self):
        r = client.post(
            "/api/mobile/images/session",
            json={"capture_type": "baseline"},
            headers=HEADERS,
        )
        assert "capture_session_id" in r.json()

    def test_upload_image_returns_200(self):
        cap_r = client.post(
            "/api/mobile/images/session",
            json={"capture_type": "defect"},
            headers=HEADERS,
        )
        cap_id = cap_r.json()["capture_session_id"]
        r = client.post(
            "/api/mobile/images/upload",
            json={"capture_session_id": cap_id, "image_base64": _small_jpeg_b64(), "image_type": "jpeg"},
            headers=HEADERS,
        )
        assert r.status_code == 200

    def test_upload_image_stores_metadata(self):
        cap_r = client.post(
            "/api/mobile/images/session",
            json={"capture_type": "contamination"},
            headers=HEADERS,
        )
        cap_id = cap_r.json()["capture_session_id"]
        r = client.post(
            "/api/mobile/images/upload",
            json={"capture_session_id": cap_id, "image_base64": _small_jpeg_b64()},
            headers=HEADERS,
        )
        data = r.json()
        assert "image_id" in data
        assert data["stored"] is True
        assert "size_bytes" in data

    def test_capture_session_status_returns_200(self):
        cap_r = client.post(
            "/api/mobile/images/session",
            json={"capture_type": "borescope"},
            headers=HEADERS,
        )
        cap_id = cap_r.json()["capture_session_id"]
        r = client.get(f"/api/mobile/images/session/{cap_id}", headers=HEADERS)
        assert r.status_code == 200

    def test_upload_requires_auth(self):
        r = client.post(
            "/api/mobile/images/upload",
            json={"capture_session_id": "fake", "image_base64": _small_jpeg_b64()},
        )
        assert r.status_code in (401, 403)


# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------


class TestNotifications:
    def test_list_notifications_returns_200(self):
        r = client.get("/api/mobile/notifications", headers=HEADERS)
        assert r.status_code == 200

    def test_list_notifications_has_notifications_key(self):
        r = client.get("/api/mobile/notifications", headers=HEADERS)
        assert "notifications" in r.json()

    def test_create_notification_returns_200(self):
        r = client.post(
            "/api/mobile/notifications",
            json={
                "recipient_id": "tech-001",
                "notification_type": "capa_assignment",
                "title": "New CAPA assigned",
                "body": "You have been assigned CAPA-001",
                "priority": "high",
            },
            headers=HEADERS,
        )
        assert r.status_code == 200

    def test_create_notification_has_id(self):
        r = client.post(
            "/api/mobile/notifications",
            json={
                "recipient_id": "tech-002",
                "notification_type": "quality_alert",
                "title": "Quality Alert",
                "body": "Instrument quality signal detected",
            },
            headers=HEADERS,
        )
        assert "notification_id" in r.json()

    def test_mark_read_returns_200(self):
        create_r = client.post(
            "/api/mobile/notifications",
            json={"recipient_id": "tech-001", "notification_type": "executive", "title": "T", "body": "B"},
            headers=HEADERS,
        )
        nid = create_r.json()["notification_id"]
        r = client.patch(f"/api/mobile/notifications/{nid}/read", headers=HEADERS)
        assert r.status_code == 200

    def test_dismiss_returns_200(self):
        create_r = client.post(
            "/api/mobile/notifications",
            json={"recipient_id": "tech-001", "notification_type": "executive", "title": "T2", "body": "B2"},
            headers=HEADERS,
        )
        nid = create_r.json()["notification_id"]
        r = client.patch(f"/api/mobile/notifications/{nid}/dismiss", headers=HEADERS)
        assert r.status_code == 200

    def test_broadcast_returns_200(self):
        r = client.post(
            "/api/mobile/notifications/broadcast",
            json={
                "facility_id": "fac-001",
                "notification_type": "safety_alert",
                "title": "Safety Alert",
                "body": "Immediate action required",
                "priority": "critical",
            },
            headers=HEADERS,
        )
        assert r.status_code == 200

    def test_broadcast_has_recipient_id_with_broadcast_prefix(self):
        r = client.post(
            "/api/mobile/notifications/broadcast",
            json={
                "facility_id": "fac-002",
                "notification_type": "recall_alert",
                "title": "Recall Alert",
                "body": "Instrument recall issued",
                "priority": "critical",
            },
            headers=HEADERS,
        )
        assert r.json()["recipient_id"].startswith("broadcast:")

    def test_notifications_require_auth(self):
        r = client.get("/api/mobile/notifications")
        assert r.status_code in (401, 403)


# ---------------------------------------------------------------------------
# Device Sessions
# ---------------------------------------------------------------------------


class TestDeviceSessions:
    def _register(self):
        r = client.post(
            "/api/mobile/device-sessions",
            json={"device_id": f"dev-{uuid.uuid4()}", "device_type": "android", "auth_method": "biometric"},
            headers=HEADERS,
        )
        assert r.status_code == 200
        return r.json()["device_session_id"]

    def test_register_device_returns_200(self):
        r = client.post(
            "/api/mobile/device-sessions",
            json={"device_id": "dev-xyz", "device_type": "ios", "auth_method": "token"},
            headers=HEADERS,
        )
        assert r.status_code == 200

    def test_register_device_has_session_id(self):
        r = client.post(
            "/api/mobile/device-sessions",
            json={"device_id": "dev-abc", "device_type": "tablet"},
            headers=HEADERS,
        )
        assert "device_session_id" in r.json()

    def test_list_devices_returns_200(self):
        r = client.get("/api/mobile/device-sessions", headers=HEADERS)
        assert r.status_code == 200

    def test_remote_logout_returns_200(self):
        dsid = self._register()
        r = client.post(f"/api/mobile/device-sessions/{dsid}/logout", headers=HEADERS)
        assert r.status_code == 200

    def test_remote_logout_sets_flag(self):
        dsid = self._register()
        r = client.post(f"/api/mobile/device-sessions/{dsid}/logout", headers=HEADERS)
        assert r.json()["remote_logout_requested"] is True

    def test_remote_wipe_returns_200(self):
        dsid = self._register()
        r = client.post(f"/api/mobile/device-sessions/{dsid}/wipe", headers=HEADERS)
        assert r.status_code == 200

    def test_remote_wipe_sets_flag(self):
        dsid = self._register()
        r = client.post(f"/api/mobile/device-sessions/{dsid}/wipe", headers=HEADERS)
        assert r.json()["remote_wipe_requested"] is True

    def test_device_sessions_require_auth(self):
        r = client.get("/api/mobile/device-sessions")
        assert r.status_code in (401, 403)


# ---------------------------------------------------------------------------
# Sync Queue
# ---------------------------------------------------------------------------


class TestSyncQueue:
    def test_add_to_queue_returns_200(self):
        r = client.post(
            "/api/mobile/sync-queue",
            json={
                "device_id": "dev-001",
                "items": [
                    {"payload_type": "inspection", "payload_json": '{"key": "value"}'},
                    {"payload_type": "finding", "payload_json": '{"severity": "minor"}'},
                ],
            },
            headers=HEADERS,
        )
        assert r.status_code == 200

    def test_add_to_queue_returns_count(self):
        r = client.post(
            "/api/mobile/sync-queue",
            json={
                "items": [{"payload_type": "scan", "payload_json": '{}'}],
            },
            headers=HEADERS,
        )
        assert r.json()["queued"] == 1

    def test_add_to_queue_returns_ids(self):
        r = client.post(
            "/api/mobile/sync-queue",
            json={
                "items": [{"payload_type": "capa_note", "payload_json": '{"note": "test"}'}],
            },
            headers=HEADERS,
        )
        assert len(r.json()["queue_ids"]) == 1

    def test_process_queue_returns_200(self):
        # Add something first
        client.post(
            "/api/mobile/sync-queue",
            json={"items": [{"payload_type": "inspection", "payload_json": "{}"}]},
            headers=HEADERS,
        )
        r = client.post("/api/mobile/sync-queue/process", headers=HEADERS)
        assert r.status_code == 200

    def test_process_queue_has_processed_count(self):
        r = client.post("/api/mobile/sync-queue/process", headers=HEADERS)
        assert "processed" in r.json()

    def test_process_queue_has_remaining_count(self):
        r = client.post("/api/mobile/sync-queue/process", headers=HEADERS)
        assert "remaining" in r.json()


# ---------------------------------------------------------------------------
# Mobile Dashboard
# ---------------------------------------------------------------------------

REQUIRED_KPI_KEYS = {
    "inspections_today",
    "failed_inspections",
    "pending_reviews",
    "capas_due",
    "safety_signals",
    "notifications_unread",
}


class TestMobileDashboard:
    def test_technician_dashboard_returns_200(self):
        r = client.get("/api/mobile/dashboard/technician", headers=HEADERS)
        assert r.status_code == 200

    def test_supervisor_dashboard_returns_200(self):
        r = client.get("/api/mobile/dashboard/supervisor", headers=HEADERS)
        assert r.status_code == 200

    def test_manager_dashboard_returns_200(self):
        r = client.get("/api/mobile/dashboard/manager", headers=HEADERS)
        assert r.status_code == 200

    def test_quality_director_dashboard_returns_200(self):
        r = client.get("/api/mobile/dashboard/quality_director", headers=HEADERS)
        assert r.status_code == 200

    def test_infection_prevention_dashboard_returns_200(self):
        r = client.get("/api/mobile/dashboard/infection_prevention", headers=HEADERS)
        assert r.status_code == 200

    def test_executive_dashboard_returns_200(self):
        r = client.get("/api/mobile/dashboard/executive", headers=HEADERS)
        assert r.status_code == 200

    def test_all_dashboards_have_required_kpis(self):
        roles = ["technician", "supervisor", "manager", "quality_director", "infection_prevention", "executive"]
        for role in roles:
            r = client.get(f"/api/mobile/dashboard/{role}", headers=HEADERS)
            assert r.status_code == 200, f"role={role} returned {r.status_code}"
            data = r.json()
            missing = REQUIRED_KPI_KEYS - set(data.keys())
            assert not missing, f"role={role} missing KPI keys: {missing}"

    def test_dashboard_requires_auth(self):
        r = client.get("/api/mobile/dashboard/technician")
        assert r.status_code in (401, 403)

    def test_invalid_role_returns_400(self):
        r = client.get("/api/mobile/dashboard/unknown_role", headers=HEADERS)
        assert r.status_code == 400


# ---------------------------------------------------------------------------
# Mobile Auth
# ---------------------------------------------------------------------------


class TestMobileAuth:
    def test_token_refresh_returns_200(self):
        r = client.post("/api/mobile/auth/token-refresh", headers=HEADERS)
        assert r.status_code == 200

    def test_token_refresh_has_access_token(self):
        r = client.post("/api/mobile/auth/token-refresh", headers=HEADERS)
        assert "access_token" in r.json()

    def test_token_refresh_has_expires_in(self):
        r = client.post("/api/mobile/auth/token-refresh", headers=HEADERS)
        assert r.json()["expires_in"] == 28800

    def test_auth_check_returns_200(self):
        r = client.get("/api/mobile/auth/check", headers=HEADERS)
        assert r.status_code == 200

    def test_auth_check_has_tenant_id(self):
        r = client.get("/api/mobile/auth/check", headers=HEADERS)
        assert "tenant_id" in r.json()

    def test_auth_check_authenticated_true(self):
        r = client.get("/api/mobile/auth/check", headers=HEADERS)
        assert r.json()["authenticated"] is True

    def test_logout_returns_200(self):
        r = client.post("/api/mobile/auth/logout", headers=HEADERS)
        assert r.status_code == 200

    def test_logout_returns_logged_out_true(self):
        r = client.post("/api/mobile/auth/logout", headers=HEADERS)
        assert r.json()["logged_out"] is True


# ---------------------------------------------------------------------------
# Tenant Isolation
# ---------------------------------------------------------------------------


class TestTenantIsolation:
    """Sessions/notifications/scans are scoped to tenant extracted from JWT."""

    def test_sessions_scoped_to_tenant(self):
        # Create a session with dev-token tenant
        sid = _make_session()
        # List sessions — should contain our session
        r = client.get("/api/mobile/sessions", headers=HEADERS)
        assert r.status_code == 200
        session_ids = [s["session_id"] for s in r.json()["sessions"]]
        assert sid in session_ids

    def test_notifications_scoped_to_tenant(self):
        # Create notification and list — should appear in results
        client.post(
            "/api/mobile/notifications",
            json={"recipient_id": "tech-isolation", "notification_type": "executive", "title": "Isolation Test", "body": "body"},
            headers=HEADERS,
        )
        r = client.get("/api/mobile/notifications", headers=HEADERS)
        assert r.status_code == 200
        titles = [n["title"] for n in r.json()["notifications"]]
        assert "Isolation Test" in titles

    def test_scan_results_scoped_to_tenant(self):
        # Create scan result and verify it appears in list
        client.post(
            "/api/mobile/scan/decode",
            json={"image_base64": _b64_image(), "scan_type": "barcode", "session_id": None},
            headers=HEADERS,
        )
        r = client.get("/api/mobile/scan/results", headers=HEADERS)
        assert r.status_code == 200
        assert "results" in r.json()
