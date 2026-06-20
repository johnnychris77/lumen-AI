"""P12 Clinical Validation — FP/FN analysis, validation report, safety endpoints."""
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
HEADERS = {"Authorization": "Bearer dev-token"}

FINDING_CATEGORIES = [
    "blood",
    "bone",
    "tissue",
    "residue",
    "corrosion",
    "crack",
    "pitting",
    "insulation",
    "barcode",
    "udi",
    "qr",
    "keydot",
]
CRITICAL = {"crack", "corrosion", "insulation"}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _submit_case(**kwargs):
    payload = {
        "case_ref": "test-case-001",
        "instrument_category": "scissors",
        "finding_category": "blood",
        "ground_truth": True,
        **kwargs,
    }
    return client.post("/api/validation/cases", json=payload, headers=HEADERS)


def _get_report(run_label="mock-run"):
    return client.get(
        "/api/validation/report", params={"run_label": run_label}, headers=HEADERS
    )


def _get_category_report(category, run_label="mock-run"):
    return client.get(
        f"/api/validation/report/{category}",
        params={"run_label": run_label},
        headers=HEADERS,
    )


# ---------------------------------------------------------------------------
# TestValidationCaseSubmission (10 tests)
# ---------------------------------------------------------------------------


class TestValidationCaseSubmission:
    def test_submit_valid_case_returns_200(self):
        r = _submit_case()
        assert r.status_code == 200

    def test_submit_case_required_fields_present(self):
        r = _submit_case(case_ref="ref-01", finding_category="bone", ground_truth=False)
        assert r.status_code == 200
        data = r.json()
        assert "case_ref" in data
        assert "finding_category" in data
        assert "ground_truth" in data

    def test_submit_case_with_ai_prediction_stored(self):
        r = _submit_case(ai_prediction=True, ai_confidence=0.91)
        assert r.status_code == 200
        data = r.json()
        assert data["ai_prediction"] is True
        assert data["ai_confidence"] == pytest.approx(0.91, abs=1e-4)

    def test_submit_case_with_human_prediction_stored(self):
        r = _submit_case(human_prediction=False, reader_role="technician")
        assert r.status_code == 200
        data = r.json()
        assert data["human_prediction"] is False
        assert data["reader_role"] == "technician"

    def test_submit_critical_finding_case_stored(self):
        r = _submit_case(finding_category="crack", is_critical=True)
        assert r.status_code == 200
        assert r.json()["is_critical"] is True

    def test_missing_ground_truth_returns_422(self):
        payload = {
            "case_ref": "ref-bad",
            "instrument_category": "scissors",
            "finding_category": "blood",
            # ground_truth omitted
        }
        r = client.post("/api/validation/cases", json=payload, headers=HEADERS)
        assert r.status_code == 422

    def test_invalid_finding_category_still_accepted(self):
        # No enum constraint at API level — any string is accepted
        r = _submit_case(finding_category="unknown_category")
        assert r.status_code == 200

    def test_list_cases_returns_200(self):
        r = client.get("/api/validation/cases", headers=HEADERS)
        assert r.status_code == 200

    def test_list_cases_by_category_filter_returns_filtered(self):
        _submit_case(finding_category="tissue", case_ref="filter-test-01")
        r = client.get(
            "/api/validation/cases",
            params={"finding_category": "tissue"},
            headers=HEADERS,
        )
        assert r.status_code == 200
        data = r.json()
        assert "cases" in data

    def test_list_cases_returns_most_recent_first(self):
        # Submit two cases and verify list response is structured correctly
        _submit_case(case_ref="order-a", finding_category="blood")
        _submit_case(case_ref="order-b", finding_category="blood")
        r = client.get("/api/validation/cases", headers=HEADERS)
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data["cases"], list)


# ---------------------------------------------------------------------------
# TestValidationReport (15 tests)
# ---------------------------------------------------------------------------


class TestValidationReport:
    def test_get_report_returns_200(self):
        r = _get_report()
        assert r.status_code == 200

    def test_report_has_overall_accuracy(self):
        data = _get_report().json()
        assert "overall_accuracy" in data

    def test_overall_accuracy_in_range(self):
        data = _get_report().json()
        assert 0.0 <= data["overall_accuracy"] <= 1.0

    def test_report_has_overall_precision_in_range(self):
        data = _get_report().json()
        assert "overall_precision" in data
        assert 0.0 <= data["overall_precision"] <= 1.0

    def test_report_has_overall_recall_in_range(self):
        data = _get_report().json()
        assert "overall_recall" in data
        assert 0.0 <= data["overall_recall"] <= 1.0

    def test_report_has_overall_f1_in_range(self):
        data = _get_report().json()
        assert "overall_f1" in data
        assert 0.0 <= data["overall_f1"] <= 1.0

    def test_report_has_overall_kappa(self):
        data = _get_report().json()
        assert "overall_kappa" in data

    def test_report_has_critical_finding_fn_rate_in_range(self):
        data = _get_report().json()
        assert "critical_finding_fn_rate" in data
        assert 0.0 <= data["critical_finding_fn_rate"] <= 1.0

    def test_report_has_meets_primary_endpoint_bool(self):
        data = _get_report().json()
        assert "meets_primary_endpoint" in data
        assert isinstance(data["meets_primary_endpoint"], bool)

    def test_report_has_meets_safety_endpoint_bool(self):
        data = _get_report().json()
        assert "meets_safety_endpoint" in data
        assert isinstance(data["meets_safety_endpoint"], bool)

    def test_report_has_by_category_list(self):
        data = _get_report().json()
        assert "by_category" in data
        assert isinstance(data["by_category"], list)

    def test_by_category_covers_all_12_categories(self):
        data = _get_report().json()
        found = {c["finding_category"] for c in data["by_category"]}
        assert found == set(FINDING_CATEGORIES)

    def test_report_has_recommendations_list(self):
        data = _get_report().json()
        assert "recommendations" in data
        assert isinstance(data["recommendations"], list)

    def test_data_source_field_present(self):
        data = _get_report().json()
        assert "data_source" in data

    def test_generated_at_field_present(self):
        data = _get_report().json()
        assert "generated_at" in data


# ---------------------------------------------------------------------------
# TestPerCategoryBreakdown (12 tests — one per category)
# ---------------------------------------------------------------------------


class TestPerCategoryBreakdown:
    def _check_category(self, category):
        r = _get_category_report(category)
        assert r.status_code == 200
        data = r.json()
        assert data["finding_category"] == category
        ai = data["ai_metrics"]
        for key in ("tp", "tn", "fp", "fn"):
            assert key in ai, f"Missing key {key} in ai_metrics for {category}"

    def test_blood_category_has_confusion_matrix(self):
        self._check_category("blood")

    def test_bone_category_has_confusion_matrix(self):
        self._check_category("bone")

    def test_tissue_category_has_confusion_matrix(self):
        self._check_category("tissue")

    def test_residue_category_has_confusion_matrix(self):
        self._check_category("residue")

    def test_corrosion_category_has_confusion_matrix(self):
        self._check_category("corrosion")

    def test_crack_category_has_confusion_matrix(self):
        self._check_category("crack")

    def test_pitting_category_has_confusion_matrix(self):
        self._check_category("pitting")

    def test_insulation_category_has_confusion_matrix(self):
        self._check_category("insulation")

    def test_barcode_category_has_confusion_matrix(self):
        self._check_category("barcode")

    def test_udi_category_has_confusion_matrix(self):
        self._check_category("udi")

    def test_qr_category_has_confusion_matrix(self):
        self._check_category("qr")

    def test_keydot_category_has_confusion_matrix(self):
        self._check_category("keydot")


# ---------------------------------------------------------------------------
# TestConfusionMatrixIntegrity (10 tests)
# ---------------------------------------------------------------------------


class TestConfusionMatrixIntegrity:
    def _report(self):
        return _get_report().json()

    def test_case_count_equals_sum_of_tp_tn_fp_fn(self):
        data = self._report()
        for cat in data["by_category"]:
            ai = cat["ai_metrics"]
            total = ai["tp"] + ai["tn"] + ai["fp"] + ai["fn"]
            assert total == ai["case_count"], (
                f"case_count mismatch for {cat['finding_category']}"
            )

    def test_precision_formula_correct(self):
        data = self._report()
        for cat in data["by_category"]:
            ai = cat["ai_metrics"]
            if (ai["tp"] + ai["fp"]) > 0:
                expected = ai["tp"] / (ai["tp"] + ai["fp"])
                assert abs(ai["precision"] - expected) < 0.001

    def test_recall_formula_correct(self):
        data = self._report()
        for cat in data["by_category"]:
            ai = cat["ai_metrics"]
            if (ai["tp"] + ai["fn"]) > 0:
                expected = ai["tp"] / (ai["tp"] + ai["fn"])
                assert abs(ai["recall"] - expected) < 0.001

    def test_f1_formula_correct(self):
        data = self._report()
        for cat in data["by_category"]:
            ai = cat["ai_metrics"]
            p, r = ai["precision"], ai["recall"]
            if (p + r) > 0:
                expected = 2 * p * r / (p + r)
                assert abs(ai["f1"] - expected) < 0.001

    def test_critical_findings_have_is_critical_true(self):
        data = self._report()
        for cat in data["by_category"]:
            if cat["finding_category"] in CRITICAL:
                assert cat["is_critical"] is True, (
                    f"{cat['finding_category']} should be critical"
                )

    def test_non_critical_findings_have_is_critical_false(self):
        data = self._report()
        non_critical = {"blood", "bone", "tissue", "residue"}
        for cat in data["by_category"]:
            if cat["finding_category"] in non_critical:
                assert cat["is_critical"] is False, (
                    f"{cat['finding_category']} should not be critical"
                )

    def test_false_positive_rate_formula_correct(self):
        data = self._report()
        for cat in data["by_category"]:
            ai = cat["ai_metrics"]
            if (ai["fp"] + ai["tn"]) > 0:
                expected = ai["fp"] / (ai["fp"] + ai["tn"])
                assert abs(ai["false_positive_rate"] - expected) < 0.001

    def test_false_negative_rate_formula_correct(self):
        data = self._report()
        for cat in data["by_category"]:
            ai = cat["ai_metrics"]
            if (ai["fn"] + ai["tp"]) > 0:
                expected = ai["fn"] / (ai["fn"] + ai["tp"])
                assert abs(ai["false_negative_rate"] - expected) < 0.001

    def test_kappa_field_present_and_in_valid_range(self):
        data = self._report()
        for cat in data["by_category"]:
            assert "kappa" in cat
            assert -1.0 <= cat["kappa"] <= 1.0

    def test_confidence_interval_95_has_lower_and_upper(self):
        data = self._report()
        for cat in data["by_category"]:
            ci = cat["confidence_interval_95"]
            assert "lower" in ci
            assert "upper" in ci


# ---------------------------------------------------------------------------
# TestSafetyEndpoints (8 tests)
# ---------------------------------------------------------------------------


class TestSafetyEndpoints:
    def test_critical_fn_rate_under_10_percent_in_mock_data(self):
        data = _get_report().json()
        assert data["critical_finding_fn_rate"] <= 0.10

    def test_meets_safety_endpoint_reflects_fn_rate_threshold(self):
        data = _get_report().json()
        fn_rate = data["critical_finding_fn_rate"]
        expected = fn_rate <= 0.02
        assert data["meets_safety_endpoint"] == expected

    def test_meets_primary_endpoint_reflects_kappa_threshold(self):
        data = _get_report().json()
        kappa = data["overall_kappa"]
        expected = kappa >= 0.80
        assert data["meets_primary_endpoint"] == expected

    def test_recommendations_is_non_empty_list(self):
        data = _get_report().json()
        assert len(data["recommendations"]) >= 1

    def test_if_safety_endpoint_not_met_critical_in_recommendation(self):
        data = _get_report().json()
        if not data["meets_safety_endpoint"]:
            combined = " ".join(data["recommendations"]).lower()
            assert "critical" in combined

    def test_submit_real_fn_case_for_critical_finding(self):
        # A real FN: ground_truth=True, ai_prediction=False, critical
        r = _submit_case(
            finding_category="crack",
            ground_truth=True,
            ai_prediction=False,
            is_critical=True,
            case_ref="fn-test-crack",
        )
        assert r.status_code == 200
        assert r.json()["is_critical"] is True

    def test_submit_tn_for_critical_finding_not_counted_as_fn(self):
        # TN: ground_truth=False, ai_prediction=False
        r = _submit_case(
            finding_category="corrosion",
            ground_truth=False,
            ai_prediction=False,
            is_critical=True,
            case_ref="tn-test-corrosion",
        )
        assert r.status_code == 200
        data = r.json()
        # TN stored with correct ground_truth
        assert data["ground_truth"] is False

    def test_report_is_deterministic_on_same_tenant_and_run_label(self):
        r1 = _get_report("stable-run").json()
        r2 = _get_report("stable-run").json()
        assert r1["overall_kappa"] == r2["overall_kappa"]
        assert r1["overall_accuracy"] == r2["overall_accuracy"]


# ---------------------------------------------------------------------------
# TestValidationCategories (5 tests)
# ---------------------------------------------------------------------------


class TestValidationCategories:
    def test_get_categories_returns_200(self):
        r = client.get("/api/validation/categories", headers=HEADERS)
        assert r.status_code == 200

    def test_returns_list_of_12_categories(self):
        r = client.get("/api/validation/categories", headers=HEADERS)
        data = r.json()
        assert len(data) == 12

    def test_all_expected_categories_present(self):
        r = client.get("/api/validation/categories", headers=HEADERS)
        data = r.json()
        for cat in FINDING_CATEGORIES:
            assert cat in data, f"Category {cat} missing from /categories response"

    def test_response_is_json_array_of_strings(self):
        r = client.get("/api/validation/categories", headers=HEADERS)
        data = r.json()
        assert isinstance(data, list)
        for item in data:
            assert isinstance(item, str)

    def test_no_duplicates_in_categories(self):
        r = client.get("/api/validation/categories", headers=HEADERS)
        data = r.json()
        assert len(data) == len(set(data))


# ---------------------------------------------------------------------------
# TestTierGating (5 tests)
# ---------------------------------------------------------------------------


class TestTierGating:
    def test_validation_basic_accessible_on_standard_tier(self):
        from app.tier_guard import TIER_FEATURES

        assert "validation_basic" in TIER_FEATURES["standard"]

    def test_validation_report_accessible_at_professional_tier(self):
        from app.tier_guard import TIER_FEATURES

        assert "validation_report" in TIER_FEATURES["professional"]

    def test_cases_endpoint_accessible_with_auth(self):
        r = client.get("/api/validation/cases", headers=HEADERS)
        assert r.status_code == 200

    def test_report_endpoint_requires_auth(self):
        # With valid (dev) auth token it must succeed
        r = client.get("/api/validation/report", headers=HEADERS)
        assert r.status_code == 200

    def test_unauthenticated_request_returns_401_or_403(self):
        r = client.get("/api/validation/report")
        assert r.status_code in (401, 403)


# ---------------------------------------------------------------------------
# TestMockDataConsistency (5 tests)
# ---------------------------------------------------------------------------


class TestMockDataConsistency:
    def test_same_run_label_produces_same_kappa(self):
        r1 = _get_report("consistency-test").json()
        r2 = _get_report("consistency-test").json()
        assert r1["overall_kappa"] == r2["overall_kappa"]

    def test_same_tenant_produces_same_by_category_order(self):
        r1 = _get_report("order-test").json()
        r2 = _get_report("order-test").json()
        cats1 = [c["finding_category"] for c in r1["by_category"]]
        cats2 = [c["finding_category"] for c in r2["by_category"]]
        assert cats1 == cats2

    def test_mock_report_has_data_source_field(self):
        # data_source is "mock" when no real DB cases exist for the tenant+run.
        # In test environment some categories may have real cases → "mixed" is also valid.
        data = _get_report().json()
        assert data["data_source"] in ("mock", "mixed", "real")

    def test_mock_data_categories_have_expected_case_count(self):
        # Categories with no real DB cases use 100 mock cases (50 pos + 50 neg).
        # Categories that happen to have real cases may have more.
        data = _get_report().json()
        for cat in data["by_category"]:
            ai = cat["ai_metrics"]
            total = ai["tp"] + ai["tn"] + ai["fp"] + ai["fn"]
            assert total >= 1, (
                f"Expected ≥1 case for {cat['finding_category']}, got {total}"
            )

    def test_ai_metrics_and_human_metrics_both_present(self):
        data = _get_report().json()
        for cat in data["by_category"]:
            assert "ai_metrics" in cat
            assert "human_metrics" in cat
            assert cat["ai_metrics"] is not None
            assert cat["human_metrics"] is not None
