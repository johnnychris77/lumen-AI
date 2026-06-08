import os
import time

from fastapi.testclient import TestClient

os.environ.setdefault("DATABASE_URL", "sqlite:///./lumenai.db")


def test_vendor_baseline_audit_events_are_append_only_and_stable():
    from app.main import app

    client = TestClient(app)

    unique = str(int(time.time()))

    vendor_headers = {
        "Authorization": "Bearer dev-token",
        "X-LumenAI-Role": "vendor",
        "X-LumenAI-Actor": "audit-immutability-vendor",
        "Content-Type": "application/json",
    }

    reviewer_headers = {
        "Authorization": "Bearer dev-token",
        "X-LumenAI-Role": "hospital_admin",
        "X-LumenAI-Actor": "audit-immutability-reviewer",
    }

    payload = {
        "vendor_name": "Stryker",
        "instrument_name": f"Audit Immutability Kerrison {unique}",
        "instrument_category": "Orthopedic Instrument",
        "catalog_number": f"AUDIT-IMMUTABLE-CAT-{unique}",
        "model_number": f"AUDIT-IMMUTABLE-MODEL-{unique}",
        "barcode_value": f"AUDIT-IMMUTABLE-BARCODE-{unique}",
        "qr_code_value": f"AUDIT-IMMUTABLE-QR-{unique}",
        "key_dot_value": f"AUDIT-IMMUTABLE-DOT-{unique}",
        "tray_name": "Audit Immutability Tray",
        "baseline_image_url": "https://example.com/audit-immutability-baseline.jpg",
        "acceptable_condition_notes": "Normal clean surface with no visible bioburden.",
        "unacceptable_condition_examples": "Bioburden, rust, pitting, retained tissue.",
        "ifu_reference": "Audit Immutability IFU",
        "subscription_tier": "vendor_enterprise",
    }

    create_response = client.post(
        "/api/enterprise/vendor-baseline-subscription/baselines",
        headers=vendor_headers,
        json=payload,
    )

    assert create_response.status_code == 200, create_response.text

    baseline_id = create_response.json()["baseline"]["baseline_id"]

    initial_audit_response = client.get(
        f"/api/enterprise/vendor-baseline-subscription/baselines/{baseline_id}/audit",
        headers=reviewer_headers,
    )

    assert initial_audit_response.status_code == 200, initial_audit_response.text

    initial_audit = initial_audit_response.json()

    assert initial_audit["audit_source"] == "persistent_table"
    assert initial_audit["audit_event_count"] == 1

    initial_events = initial_audit["events"]
    initial_event_ids = [event["event_id"] for event in initial_events]
    initial_event_fingerprints = [
        (
            event["event_id"],
            event["event_type"],
            event["actor"],
            event["decision"],
            event["new_status"],
            event["created_at"],
        )
        for event in initial_events
    ]

    assert [event["event_type"] for event in initial_events] == ["baseline_submitted"]

    approve_response = client.post(
        f"/api/enterprise/vendor-baseline-subscription/baselines/{baseline_id}/approve",
        headers=reviewer_headers,
        json={"approval_notes": "Approved during audit immutability validation."},
    )

    assert approve_response.status_code == 200, approve_response.text

    approved_audit_response = client.get(
        f"/api/enterprise/vendor-baseline-subscription/baselines/{baseline_id}/audit",
        headers=reviewer_headers,
    )

    assert approved_audit_response.status_code == 200, approved_audit_response.text

    approved_audit = approved_audit_response.json()

    assert approved_audit["audit_source"] == "persistent_table"
    assert approved_audit["audit_event_count"] == 3

    approved_events = approved_audit["events"]
    approved_event_ids = [event["event_id"] for event in approved_events]

    # Existing audit event IDs must remain present after later workflow actions.
    for event_id in initial_event_ids:
        assert event_id in approved_event_ids

    # Existing event content must not be overwritten.
    approved_fingerprints_by_id = {
        event["event_id"]: (
            event["event_id"],
            event["event_type"],
            event["actor"],
            event["decision"],
            event["new_status"],
            event["created_at"],
        )
        for event in approved_events
    }

    for fingerprint in initial_event_fingerprints:
        event_id = fingerprint[0]
        assert approved_fingerprints_by_id[event_id] == fingerprint

    assert [event["event_type"] for event in approved_events] == [
        "baseline_submitted",
        "baseline_approved",
        "baseline_used_in_scoring",
    ]

    # Repeating approval should not mutate or duplicate the approved/scoring chain.
    duplicate_approval_response = client.post(
        f"/api/enterprise/vendor-baseline-subscription/baselines/{baseline_id}/approve",
        headers=reviewer_headers,
        json={"approval_notes": "Duplicate approval should not mutate audit chain."},
    )

    assert duplicate_approval_response.status_code == 200, duplicate_approval_response.text

    final_audit_response = client.get(
        f"/api/enterprise/vendor-baseline-subscription/baselines/{baseline_id}/audit",
        headers=reviewer_headers,
    )

    assert final_audit_response.status_code == 200, final_audit_response.text

    final_audit = final_audit_response.json()

    assert final_audit["audit_source"] == "persistent_table"
    assert final_audit["audit_event_count"] == 3

    final_events = final_audit["events"]
    final_event_ids = [event["event_id"] for event in final_events]

    assert final_event_ids == approved_event_ids

    final_fingerprints = [
        (
            event["event_id"],
            event["event_type"],
            event["actor"],
            event["decision"],
            event["new_status"],
            event["created_at"],
        )
        for event in final_events
    ]

    approved_fingerprints = [
        (
            event["event_id"],
            event["event_type"],
            event["actor"],
            event["decision"],
            event["new_status"],
            event["created_at"],
        )
        for event in approved_events
    ]

    assert final_fingerprints == approved_fingerprints
