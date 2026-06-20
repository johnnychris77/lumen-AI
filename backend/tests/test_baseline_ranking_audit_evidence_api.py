import os

os.environ.setdefault("DATABASE_URL", "sqlite:///./lumenai.db")

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

ENDPOINT = "/api/baseline-ranking/audit-evidence"


def test_approved_payload_returns_audit_evidence():
    response = client.post(
        ENDPOINT,
        json={
            "instrument_match_status": "Matched",
            "baseline_status": "Approved Baseline Found",
            "baseline_confidence": "High",
            "capture_method": "Barcode",
            "barcode_value": "STRYKER-BARCODE-001",
            "instrument_name": "Kerrison Rongeur",
            "model_number": "KR-45",
            "instrument_category": "Spine",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "instrument_match_status": "Matched",
        "baseline_status": "Approved Baseline Found",
        "baseline_confidence": "High",
        "ranking_mode": "Baseline-confirmed ranking",
        "baseline_review_required": False,
        "final_ranking_allowed": True,
        "baseline_review_reason": "Approved baseline matched.",
        "capture_method": "Barcode",
        "barcode_value": "STRYKER-BARCODE-001",
        "instrument_name": "Kerrison Rongeur",
        "model_number": "KR-45",
        "instrument_category": "Spine",
    }


def test_pending_payload_returns_review_required_audit_evidence():
    response = client.post(
        ENDPOINT,
        json={
            "instrument_match_status": "Partial Match",
            "baseline_status": "Pending Baseline Review",
            "baseline_confidence": "Medium",
            "capture_method": "Manual Entry",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "instrument_match_status": "Partial Match",
        "baseline_status": "Pending Baseline Review",
        "baseline_confidence": "Medium",
        "ranking_mode": "Provisional ranking",
        "baseline_review_required": True,
        "final_ranking_allowed": False,
        "baseline_review_reason": "Baseline pending approval; ranking remains provisional.",
        "capture_method": "Manual Entry",
    }


def test_manual_review_payload_returns_manual_review_audit_evidence():
    response = client.post(
        ENDPOINT,
        json={
            "instrument_match_status": "Not Matched",
            "baseline_status": "No Approved Baseline",
            "baseline_confidence": "Unknown",
            "instrument_name": "Forceps",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "instrument_match_status": "Not Matched",
        "baseline_status": "No Approved Baseline",
        "baseline_confidence": "Unknown",
        "ranking_mode": "Manual review required",
        "baseline_review_required": True,
        "final_ranking_allowed": False,
        "baseline_review_reason": "No approved baseline available for final ranking.",
        "instrument_name": "Forceps",
    }


def test_malformed_payload_returns_safe_review_required_audit_evidence():
    response = client.post(
        ENDPOINT,
        json={
            "instrument_match_status": ["Matched"],
            "baseline_status": {"value": "Approved Baseline Found"},
            "baseline_confidence": 100,
            "capture_method": "Barcode",
            "barcode_value": "STRYKER-BARCODE-001",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "instrument_match_status": "",
        "baseline_status": "",
        "baseline_confidence": "",
        "ranking_mode": "Pending baseline check",
        "baseline_review_required": True,
        "final_ranking_allowed": False,
        "baseline_review_reason": "Baseline status has not been confirmed.",
        "capture_method": "Barcode",
        "barcode_value": "STRYKER-BARCODE-001",
    }


def test_unsafe_override_payload_returns_backend_decision_audit_evidence():
    response = client.post(
        ENDPOINT,
        json={
            "instrument_match_status": "Not Matched",
            "baseline_status": "Approved Baseline Found",
            "baseline_confidence": "High",
            "ranking_mode": "Baseline-confirmed ranking",
            "baseline_review_required": False,
            "final_ranking_allowed": True,
            "baseline_review_reason": "client supplied",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "instrument_match_status": "Not Matched",
        "baseline_status": "Approved Baseline Found",
        "baseline_confidence": "High",
        "ranking_mode": "Pending baseline check",
        "baseline_review_required": True,
        "final_ranking_allowed": False,
        "baseline_review_reason": "Baseline status has not been confirmed.",
    }
