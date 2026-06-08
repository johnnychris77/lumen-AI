import os
import time

from fastapi.testclient import TestClient

os.environ.setdefault("DATABASE_URL", "sqlite:///./lumenai.db")


def _client():
    from app.main import app

    return TestClient(app)


def _vendor_headers(actor="vendor-access-control"):
    return {
        "Authorization": "Bearer dev-token",
        "X-LumenAI-Role": "vendor",
        "X-LumenAI-Actor": actor,
        "Content-Type": "application/json",
    }


def _admin_headers(actor="hospital-access-control"):
    return {
        "Authorization": "Bearer dev-token",
        "X-LumenAI-Role": "hospital_admin",
        "X-LumenAI-Actor": actor,
        "Content-Type": "application/json",
    }


def _baseline_payload(unique: str):
    return {
        "vendor_name": "Stryker",
        "instrument_name": f"Access Control Kerrison {unique}",
        "instrument_category": "Orthopedic Instrument",
        "catalog_number": f"ACCESS-CAT-{unique}",
        "model_number": f"ACCESS-MODEL-{unique}",
        "barcode_value": f"ACCESS-BARCODE-{unique}",
        "qr_code_value": f"ACCESS-QR-{unique}",
        "key_dot_value": f"ACCESS-DOT-{unique}",
        "tray_name": "Access Control Tray",
        "baseline_image_url": "https://example.com/access-control-baseline.jpg",
        "acceptable_condition_notes": "Normal clean surface with no visible bioburden.",
        "unacceptable_condition_examples": "Bioburden, rust, pitting, retained tissue.",
        "ifu_reference": "Access Control IFU",
        "subscription_tier": "vendor_enterprise",
    }


def test_vendor_can_submit_but_cannot_approve_baseline():
    client = _client()
    unique = str(int(time.time() * 1000))

    create_response = client.post(
        "/api/enterprise/vendor-baseline-subscription/baselines",
        headers=_vendor_headers(),
        json=_baseline_payload(unique),
    )

    assert create_response.status_code == 200, create_response.text

    baseline_id = create_response.json()["baseline"]["baseline_id"]

    vendor_approve_response = client.post(
        f"/api/enterprise/vendor-baseline-subscription/baselines/{baseline_id}/approve",
        headers=_vendor_headers(),
        json={"approval_notes": "Vendor should not self-approve."},
    )

    assert vendor_approve_response.status_code in {401, 403}


def test_missing_auth_cannot_approve_vendor_baseline():
    client = _client()
    unique = str(int(time.time() * 1000))

    create_response = client.post(
        "/api/enterprise/vendor-baseline-subscription/baselines",
        headers=_vendor_headers(actor="vendor-missing-auth-setup"),
        json=_baseline_payload(unique),
    )

    assert create_response.status_code == 200, create_response.text

    baseline_id = create_response.json()["baseline"]["baseline_id"]

    missing_auth_response = client.post(
        f"/api/enterprise/vendor-baseline-subscription/baselines/{baseline_id}/approve",
        json={"approval_notes": "Missing auth should not approve."},
    )

    assert missing_auth_response.status_code in {401, 403}


def test_hospital_admin_can_approve_vendor_baseline():
    client = _client()
    unique = str(int(time.time() * 1000))

    create_response = client.post(
        "/api/enterprise/vendor-baseline-subscription/baselines",
        headers=_vendor_headers(actor="vendor-admin-approval-setup"),
        json=_baseline_payload(unique),
    )

    assert create_response.status_code == 200, create_response.text

    baseline_id = create_response.json()["baseline"]["baseline_id"]

    approve_response = client.post(
        f"/api/enterprise/vendor-baseline-subscription/baselines/{baseline_id}/approve",
        headers=_admin_headers(),
        json={"approval_notes": "Hospital admin approved."},
    )

    assert approve_response.status_code == 200, approve_response.text
    assert approve_response.json()["baseline"]["approval_status"] == "hospital_approved"
