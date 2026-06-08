import os
import time

from fastapi.testclient import TestClient

os.environ.setdefault("DATABASE_URL", "sqlite:///./lumenai.db")


def _client():
    from app.main import app

    return TestClient(app)


def _vendor_headers(actor="vendor-audit-access"):
    return {
        "Authorization": "Bearer dev-token",
        "X-LumenAI-Role": "vendor",
        "X-LumenAI-Actor": actor,
        "Content-Type": "application/json",
    }


def _admin_headers(actor="hospital-audit-access"):
    return {
        "Authorization": "Bearer dev-token",
        "X-LumenAI-Role": "hospital_admin",
        "X-LumenAI-Actor": actor,
        "Content-Type": "application/json",
    }


def _baseline_payload(unique: str):
    return {
        "vendor_name": "Stryker",
        "instrument_name": f"Audit Access Kerrison {unique}",
        "instrument_category": "Orthopedic Instrument",
        "catalog_number": f"AUDIT-ACCESS-CAT-{unique}",
        "model_number": f"AUDIT-ACCESS-MODEL-{unique}",
        "barcode_value": f"AUDIT-ACCESS-BARCODE-{unique}",
        "qr_code_value": f"AUDIT-ACCESS-QR-{unique}",
        "key_dot_value": f"AUDIT-ACCESS-DOT-{unique}",
        "tray_name": "Audit Access Tray",
        "baseline_image_url": "https://example.com/audit-access-baseline.jpg",
        "acceptable_condition_notes": "Normal clean surface with no visible bioburden.",
        "unacceptable_condition_examples": "Bioburden, rust, pitting, retained tissue.",
        "ifu_reference": "Audit Access IFU",
        "subscription_tier": "vendor_enterprise",
    }


def _create_baseline(client):
    unique = str(int(time.time() * 1000))

    response = client.post(
        "/api/enterprise/vendor-baseline-subscription/baselines",
        headers=_vendor_headers(actor=f"vendor-audit-access-{unique}"),
        json=_baseline_payload(unique),
    )

    assert response.status_code == 200, response.text
    return response.json()["baseline"]["baseline_id"]


def test_hospital_admin_can_view_vendor_baseline_audit():
    client = _client()
    baseline_id = _create_baseline(client)

    response = client.get(
        f"/api/enterprise/vendor-baseline-subscription/baselines/{baseline_id}/audit",
        headers=_admin_headers(),
    )

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "success"
    assert response.json()["baseline_id"] == baseline_id


def test_vendor_cannot_view_vendor_baseline_audit():
    client = _client()
    baseline_id = _create_baseline(client)

    response = client.get(
        f"/api/enterprise/vendor-baseline-subscription/baselines/{baseline_id}/audit",
        headers=_vendor_headers(),
    )

    assert response.status_code in {401, 403}


def test_missing_auth_cannot_view_vendor_baseline_audit():
    client = _client()
    baseline_id = _create_baseline(client)

    response = client.get(
        f"/api/enterprise/vendor-baseline-subscription/baselines/{baseline_id}/audit"
    )

    assert response.status_code in {401, 403}
