import pytest

from app.core.baseline_ranking_contract import apply_baseline_ranking_to_inspection_payload_if_present
assert result["baseline_review_reason"] == "Approved baseline matched."
assert result["baseline_confidence"] == "High"

@pytest.fixture(autouse=True)
def ensure_test_database_tables():
    yield


def test_approved_baseline_payload_returns_baseline_confirmed_ranking():
    result = apply_baseline_ranking_to_inspection_payload_if_present(
        {
            "instrument_match_status": "Matched",
            "baseline_status": "Approved Baseline Found",
            "baseline_confidence": "High",
            "capture_method": "Barcode",
            "barcode_value": "STRYKER-BARCODE-001",
        }
    )
assert result["final_ranking_allowed"] is False
assert result["baseline_review_reason"] == "Baseline pending approval; ranking remains provisional."
assert result["baseline_confidence"] == "Medium"
assert result["final_ranking_allowed"] is False
assert result["baseline_review_reason"] == "No approved baseline available for final ranking."
assert result["baseline_confidence"] == "Unknown"
   
 assert result["ranking_mode"] == "Baseline-confirmed ranking"
    assert result["baseline_review_required"] is False
    assert result["final_ranking_allowed"] is True
    assert result["baseline_review_reason"] == "Approved baseline matched."
    assert result["capture_method"] == "Barcode"
    assert result["barcode_value"] == "STRYKER-BARCODE-001"


def test_pending_baseline_payload_returns_provisional_ranking():
    result = apply_baseline_ranking_to_inspection_payload_if_present(
        {
            "instrument_match_status": "Partial Match",
            "baseline_status": "Pending Baseline Review",
            "baseline_confidence": "Medium",
        }
    )

    assert result["ranking_mode"] == "Provisional ranking"
    assert result["baseline_review_required"] is True
    assert result["final_ranking_allowed"] is False


def test_no_approved_baseline_payload_returns_manual_review_required():
    result = apply_baseline_ranking_to_inspection_payload_if_present(
        {
            "instrument_match_status": "Not Matched",
            "baseline_status": "No Approved Baseline",
            "baseline_confidence": "Unknown",
        }
    )

    assert result["ranking_mode"] == "Manual review required"
    assert result["baseline_review_required"] is True
    assert result["final_ranking_allowed"] is False


def test_missing_baseline_payload_preserves_existing_behavior():
    payload = {
        "file_name": "inspection.jpg",
        "vendor_name": "Stryker",
    }

    result = apply_baseline_ranking_to_inspection_payload_if_present(payload)

    assert result == payload
    assert result is not payload
    assert "ranking_mode" not in result
    assert "final_ranking_allowed" not in result
