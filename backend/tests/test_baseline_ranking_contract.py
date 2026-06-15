import pytest

from app.core.baseline_ranking_contract import (
    apply_baseline_ranking_to_inspection_payload,
    resolve_baseline_ranking_contract,
)


@pytest.fixture(autouse=True)
def ensure_test_database_tables():
    yield


def test_approved_baseline_returns_baseline_confirmed_ranking():
    result = resolve_baseline_ranking_contract(
        instrument_match_status="Matched",
        baseline_status="Approved Baseline Found",
        baseline_confidence="High",
    )

    assert result["ranking_mode"] == "Baseline-confirmed ranking"
    assert result["baseline_review_required"] is False
    assert result["final_ranking_allowed"] is True
    assert result["review_reason"] == "Approved baseline matched."
    assert result["baseline_confidence"] == "High"


def test_pending_baseline_returns_provisional_ranking():
    result = resolve_baseline_ranking_contract(
        instrument_match_status="Partial Match",
        baseline_status="Pending Baseline Review",
        baseline_confidence="Medium",
    )

    assert result["ranking_mode"] == "Provisional ranking"
    assert result["baseline_review_required"] is True
    assert result["final_ranking_allowed"] is False
    assert result["review_reason"] == "Baseline pending approval; ranking remains provisional."


def test_no_approved_baseline_returns_manual_review_required():
    result = resolve_baseline_ranking_contract(
        instrument_match_status="Not Matched",
        baseline_status="No Approved Baseline",
    )

    assert result["ranking_mode"] == "Manual review required"
    assert result["baseline_review_required"] is True
    assert result["final_ranking_allowed"] is False
    assert result["review_reason"] == "No approved baseline available for final ranking."


def test_baseline_not_available_returns_manual_review_required():
    result = resolve_baseline_ranking_contract(
        instrument_match_status="Not Matched",
        baseline_status="Baseline Not Available",
    )

    assert result["ranking_mode"] == "Manual review required"
    assert result["baseline_review_required"] is True
    assert result["final_ranking_allowed"] is False


def test_missing_baseline_returns_pending_baseline_check():
    result = resolve_baseline_ranking_contract(
        instrument_match_status=None,
        baseline_status=None,
    )

    assert result["ranking_mode"] == "Pending baseline check"
    assert result["baseline_review_required"] is True
    assert result["final_ranking_allowed"] is False
    assert result["review_reason"] == "Baseline status has not been confirmed."


def test_casing_underscore_and_hyphen_normalization_works():
    result = resolve_baseline_ranking_contract(
        instrument_match_status="MATCHED",
        baseline_status="approved-baseline_found",
        baseline_confidence="HIGH",
    )

    assert result["ranking_mode"] == "Baseline-confirmed ranking"
    assert result["baseline_review_required"] is False
    assert result["final_ranking_allowed"] is True


def test_payload_helper_does_not_mutate_original_payload():
    payload = {
        "instrument_match_status": "Matched",
        "baseline_status": "Approved Baseline Found",
        "ranking_mode": "client supplied",
    }

    result = apply_baseline_ranking_to_inspection_payload(payload)

    assert payload["ranking_mode"] == "client supplied"
    assert "final_ranking_allowed" not in payload
    assert result is not payload


def test_approved_baseline_payload_gets_final_ranking_allowed():
    result = apply_baseline_ranking_to_inspection_payload(
        {
            "instrument_match_status": "Matched",
            "baseline_status": "Approved Baseline Found",
            "baseline_confidence": "High",
        }
    )

    assert result["ranking_mode"] == "Baseline-confirmed ranking"
    assert result["baseline_review_required"] is False
    assert result["final_ranking_allowed"] is True
    assert result["baseline_review_reason"] == "Approved baseline matched."


def test_pending_baseline_payload_gets_provisional_ranking():
    result = apply_baseline_ranking_to_inspection_payload(
        {
            "instrument_match_status": "Partial Match",
            "baseline_status": "Pending Baseline Review",
        }
    )

    assert result["ranking_mode"] == "Provisional ranking"
    assert result["baseline_review_required"] is True
    assert result["final_ranking_allowed"] is False


def test_no_approved_baseline_payload_gets_manual_review_required():
    result = apply_baseline_ranking_to_inspection_payload(
        {
            "instrument_match_status": "Not Matched",
            "baseline_status": "No Approved Baseline",
        }
    )

    assert result["ranking_mode"] == "Manual review required"
    assert result["baseline_review_required"] is True
    assert result["final_ranking_allowed"] is False


def test_missing_baseline_payload_gets_pending_baseline_check():
    result = apply_baseline_ranking_to_inspection_payload({})

    assert result["ranking_mode"] == "Pending baseline check"
    assert result["baseline_review_required"] is True
    assert result["final_ranking_allowed"] is False


def test_payload_helper_preserves_identity_fields():
    payload = {
        "capture_method": "Barcode",
        "barcode_value": "STRYKER-BARCODE-001",
        "qr_code_value": "",
        "keydot_value": "",
        "catalog_number": "STR-KR-001",
        "model_number": "KR-45",
        "manufacturer": "Stryker",
        "vendor": "Stryker",
        "instrument_name": "Kerrison Rongeur",
        "instrument_category": "Spine",
        "instrument_match_status": "Matched",
        "baseline_status": "Approved Baseline Found",
    }

    result = apply_baseline_ranking_to_inspection_payload(payload)

    for field in [
        "capture_method",
        "barcode_value",
        "qr_code_value",
        "keydot_value",
        "catalog_number",
        "model_number",
        "manufacturer",
        "vendor",
        "instrument_name",
        "instrument_category",
    ]:
        assert result[field] == payload[field]
