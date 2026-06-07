import os
import time

from fastapi.testclient import TestClient

os.environ.setdefault("DATABASE_URL", "sqlite:///./lumenai.db")


def test_vendor_baseline_persistent_audit_workflow():
    from app.main import app

    client = TestClient(app)

    unique = str(int(time.time()))

    vendor_headers = {
        "Authorization": "Bearer dev-token",
        "X-LumenAI-Role": "vendor",
        "X-LumenAI-Actor": "pytest-vendor",
        "Content-Type": "application/json",
    }

    reviewer_headers = {
        "Authorization": "Bearer dev-token",
        "X-LumenAI-Role": "hospital_admin",
        "X-LumenAI-Actor": "pytest-reviewer",
    }

    payload = {
        "vendor_name": "Stryker",
        "instrument_name": f"Pytest Kerrison Rongeur {unique}",
        "instrument_category": "Orthopedic Instrument",
        "catalog_number": f"PYTEST-CAT-{unique}",
        "model_number": f"PYTEST-MODEL-{unique}",
        "barcode_value": f"PYTEST-BARCODE-{unique}",
        "qr_code_value": f"PYTEST-QR-{unique}",
        "key_dot_value": f"PYTEST-DOT-{unique}",
        "tray_name": "Pytest Ortho Tray",
        "baseline_image_url": "https://example.com/pytest-baseline.jpg",
        "acceptable_condition_notes": "Normal clean surface with no visible bioburden.",
        "unacceptable_condition_examples": "Bioburden, rust, pitting, retained tissue.",
        "ifu_reference": "Pytest IFU",
        "subscription_tier": "vendor_enterprise",
    }

    create_response = client.post(
        "/api/enterprise/vendor-baseline-subscription/baselines",
        headers=vendor_headers,
        json=payload,
    )

    assert create_response.status_code == 200, create_response.text
    create_data = create_response.json()

    assert create_data["status"] == "success"
    baseline_id = create_data["baseline"]["baseline_id"]
    assert baseline_id

    pre_approval_audit = client.get(
        f"/api/enterprise/vendor-baseline-subscription/baselines/{baseline_id}/audit",
        headers=reviewer_headers,
    )

    assert pre_approval_audit.status_code == 200, pre_approval_audit.text
    pre_audit_data = pre_approval_audit.json()

    assert pre_audit_data["audit_source"] == "persistent_table"
    assert pre_audit_data["audit_event_count"] == 1
    assert [event["event_type"] for event in pre_audit_data["events"]] == [
        "baseline_submitted"
    ]

    approve_response = client.post(
        f"/api/enterprise/vendor-baseline-subscription/baselines/{baseline_id}/approve",
        headers=reviewer_headers,
        json={"approval_notes": "Approved during pytest workflow validation."},
    )

    assert approve_response.status_code == 200, approve_response.text
    approve_data = approve_response.json()

    assert approve_data["status"] == "success"
    assert approve_data["baseline"]["baseline_status"] == "approved"
    assert approve_data["baseline"]["approval_status"] == "hospital_approved"

    post_approval_audit = client.get(
        f"/api/enterprise/vendor-baseline-subscription/baselines/{baseline_id}/audit",
        headers=reviewer_headers,
    )

    assert post_approval_audit.status_code == 200, post_approval_audit.text
    audit_data = post_approval_audit.json()

    assert audit_data["audit_source"] == "persistent_table"
    assert audit_data["audit_event_count"] == 3

    event_types = [event["event_type"] for event in audit_data["events"]]

    assert event_types == [
        "baseline_submitted",
        "baseline_approved",
        "baseline_used_in_scoring",
    ]

    # Duplicate approval should not create duplicate persistent audit events.
    duplicate_approval = client.post(
        f"/api/enterprise/vendor-baseline-subscription/baselines/{baseline_id}/approve",
        headers=reviewer_headers,
        json={"approval_notes": "Duplicate approval should not duplicate events."},
    )

    assert duplicate_approval.status_code == 200, duplicate_approval.text

    duplicate_audit = client.get(
        f"/api/enterprise/vendor-baseline-subscription/baselines/{baseline_id}/audit",
        headers=reviewer_headers,
    )

    assert duplicate_audit.status_code == 200, duplicate_audit.text
    duplicate_audit_data = duplicate_audit.json()

    assert duplicate_audit_data["audit_source"] == "persistent_table"
    assert duplicate_audit_data["audit_event_count"] == 3

    duplicate_event_types = [
        event["event_type"] for event in duplicate_audit_data["events"]
    ]

    assert duplicate_event_types == [
        "baseline_submitted",
        "baseline_approved",
        "baseline_used_in_scoring",
    ]
