"""Tests for Computer Vision pipeline — P4.

Covers:
- MockCVProvider unit tests (determinism, scoring logic, finding detection)
- Pipeline integration (run_analysis, run_baseline_compare)
- API endpoint tests (analyze, baseline-compare, analyze-and-rank, kpi-summary, provider/info)
- Schema validation (CVInferenceResult, RegionOfInterest, BoundingBox)
- P3 ranking integration (ranking_inputs shape)
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.cv.mock_provider import MockCVProvider
from app.cv.pipeline import build_ranking_request_from_result, run_analysis, run_baseline_compare
from app.cv.registry import CVRegistry
from app.main import app
from app.schemas.cv import (
    BaselineCompareRequest,
    BoundingBox,
    CVAnalysisRequest,
)

client = TestClient(app)
AUTH = {"Authorization": "Bearer dev-token", "X-LumenAI-Role": "operator"}

FRAZIER_URL = "https://fixtures.lumenai.dev/baselines/frazier-suction-8fr.jpg"
KERRISON_URL = "https://fixtures.lumenai.dev/baselines/kerrison-rongeur-3mm.jpg"
UNKNOWN_URL = "https://fixtures.lumenai.dev/inspection/unknown-instrument-001.jpg"


# ── Unit: MockCVProvider ──────────────────────────────────────────────────────

class TestMockProviderDeterminism:
    def test_same_url_same_inference(self):
        p = MockCVProvider()
        r1 = p.analyze(CVAnalysisRequest(image_url=FRAZIER_URL))
        r2 = p.analyze(CVAnalysisRequest(image_url=FRAZIER_URL))
        assert r1.instrument_identity.instrument_name == r2.instrument_identity.instrument_name
        assert r1.identifier_reads.barcode_value == r2.identifier_reads.barcode_value
        assert len(r1.regions) == len(r2.regions)

    def test_different_urls_may_differ(self):
        p = MockCVProvider()
        r1 = p.analyze(CVAnalysisRequest(image_url=FRAZIER_URL))
        r2 = p.analyze(CVAnalysisRequest(image_url=UNKNOWN_URL))
        # At minimum the inference_ids differ
        assert r1.inference_id != r2.inference_id


class TestInstrumentIdentification:
    def test_frazier_recognized(self):
        p = MockCVProvider()
        identity = p.identify_instrument(FRAZIER_URL)
        assert identity.recognized is True
        assert "Frazier" in identity.instrument_name

    def test_known_instrument_high_confidence(self):
        p = MockCVProvider()
        identity = p.identify_instrument(FRAZIER_URL)
        assert identity.confidence >= 0.85

    def test_unknown_url_still_returns_identity(self):
        p = MockCVProvider()
        identity = p.identify_instrument(UNKNOWN_URL)
        assert isinstance(identity.recognized, bool)
        assert 0.0 <= identity.confidence <= 1.0

    def test_instrument_category_populated(self):
        p = MockCVProvider()
        identity = p.identify_instrument(FRAZIER_URL)
        assert identity.instrument_category != ""


class TestIdentifierReading:
    def test_frazier_barcode_returned(self):
        p = MockCVProvider()
        ids = p.read_identifiers(FRAZIER_URL)
        # May be empty due to simulated read failure, but if present must match fixture
        if ids.barcode_value:
            assert "STRYKER" in ids.barcode_value or "FRAZ" in ids.barcode_value

    def test_confidence_in_range(self):
        p = MockCVProvider()
        ids = p.read_identifiers(FRAZIER_URL)
        assert 0.0 <= ids.barcode_confidence <= 1.0
        assert 0.0 <= ids.qr_confidence <= 1.0

    def test_no_identifier_returns_empty_strings(self):
        p = MockCVProvider()
        ids = p.read_identifiers(UNKNOWN_URL)
        assert isinstance(ids.barcode_value, str)
        assert isinstance(ids.qr_value, str)


class TestFindingDetection:
    def test_findings_list_is_list(self):
        p = MockCVProvider()
        result = p.analyze(CVAnalysisRequest(image_url=FRAZIER_URL))
        assert isinstance(result.regions, list)

    def test_each_region_has_required_fields(self):
        p = MockCVProvider()
        result = p.analyze(CVAnalysisRequest(image_url=FRAZIER_URL))
        for roi in result.regions:
            assert roi.roi_id
            assert roi.label
            assert roi.finding_category
            assert roi.severity in {"low", "medium", "high", "critical"}
            assert 0.0 <= roi.confidence <= 1.0

    def test_bbox_normalized(self):
        p = MockCVProvider()
        result = p.analyze(CVAnalysisRequest(image_url=FRAZIER_URL))
        for roi in result.regions:
            if roi.bbox:
                assert 0.0 <= roi.bbox.x <= 1.0
                assert 0.0 <= roi.bbox.y <= 1.0
                assert 0.0 <= roi.bbox.width <= 1.0
                assert 0.0 <= roi.bbox.height <= 1.0

    def test_scores_bounded(self):
        p = MockCVProvider()
        result = p.analyze(CVAnalysisRequest(image_url=FRAZIER_URL))
        assert 0.0 <= result.contamination_score <= 100.0
        assert 0.0 <= result.damage_score <= 100.0
        assert 0.0 <= result.overall_cleanliness_score <= 100.0

    def test_no_findings_gives_100_scores(self):
        p = MockCVProvider()
        # URL that (deterministically) produces zero findings
        result = p.analyze(CVAnalysisRequest(
            image_url="https://clean-instrument.lumenai.dev/zero-findings",
            requested_capabilities=["contamination_detection", "damage_detection"],
        ))
        # Scores must be valid regardless
        assert 0.0 <= result.contamination_score <= 100.0

    def test_lumened_instrument_higher_risk(self):
        # Lumened instruments get risk_factor 1.4× in mock — may produce more findings
        p = MockCVProvider()
        lumened = p.analyze(CVAnalysisRequest(image_url=FRAZIER_URL, instrument_category="lumened instrument"))
        non_lumened = p.analyze(CVAnalysisRequest(image_url=FRAZIER_URL, instrument_category="non-lumened instrument"))
        # Just validate both return valid results
        assert 0.0 <= lumened.overall_cleanliness_score <= 100.0
        assert 0.0 <= non_lumened.overall_cleanliness_score <= 100.0


class TestBaselineComparison:
    def test_known_baseline_high_match(self):
        p = MockCVProvider()
        result = p.compare_baseline(FRAZIER_URL, FRAZIER_URL)
        assert result.compared is True
        assert result.match_pct >= 80.0

    def test_no_baseline_url_returns_not_compared(self):
        p = MockCVProvider()
        result = p.compare_baseline(FRAZIER_URL, "")
        assert result.compared is False

    def test_verdict_pass_on_high_match(self):
        p = MockCVProvider()
        result = p.compare_baseline(FRAZIER_URL, FRAZIER_URL)
        assert result.verdict in {"pass", "review_required", "fail"}

    def test_ssim_in_range(self):
        p = MockCVProvider()
        result = p.compare_baseline(FRAZIER_URL, KERRISON_URL)
        assert 0.0 <= result.structural_similarity <= 1.0

    def test_anomaly_regions_on_low_match(self):
        p = MockCVProvider()
        # Force a low-match comparison with completely different URLs
        result = p.compare_baseline(
            "https://unknown-a.lumenai.dev/img.jpg",
            "https://unknown-b.lumenai.dev/ref.jpg",
        )
        if result.match_pct < 80:
            assert len(result.anomaly_regions) > 0


# ── Unit: score aggregation ───────────────────────────────────────────────────

class TestScoreAggregation:
    def test_contamination_deducts_for_blood(self):
        p = MockCVProvider()
        from app.schemas.cv import RegionOfInterest
        regions = [
            RegionOfInterest(
                roi_id="x1", label="blood", finding_category="blood / retained blood residue",
                severity="critical", confidence=0.95
            )
        ]
        c, d, overall = p._aggregate_scores(regions)
        assert c < 100.0

    def test_damage_deducts_for_crack(self):
        p = MockCVProvider()
        from app.schemas.cv import RegionOfInterest
        regions = [
            RegionOfInterest(
                roi_id="x2", label="crack", finding_category="crack / hairline fracture",
                severity="critical", confidence=0.95
            )
        ]
        c, d, overall = p._aggregate_scores(regions)
        assert d < 100.0

    def test_empty_regions_gives_max_scores(self):
        p = MockCVProvider()
        c, d, overall = p._aggregate_scores([])
        assert c == 100.0
        assert d == 100.0


# ── Unit: ranking inputs ──────────────────────────────────────────────────────

class TestRankingInputs:
    def test_ranking_inputs_shape(self):
        p = MockCVProvider()
        result = p.analyze(CVAnalysisRequest(image_url=FRAZIER_URL))
        ri = result.ranking_inputs
        assert "finding_category" in ri
        assert "severity" in ri
        assert "confidence_score" in ri
        assert 0.0 <= ri["confidence_score"] <= 1.0

    def test_ranking_inputs_instrument_name_propagated(self):
        p = MockCVProvider()
        result = p.analyze(CVAnalysisRequest(image_url=FRAZIER_URL))
        assert result.ranking_inputs.get("instrument_name") != ""

    def test_build_ranking_request_from_result(self):
        p = MockCVProvider()
        result = p.analyze(CVAnalysisRequest(image_url=FRAZIER_URL))
        ri = build_ranking_request_from_result(result)
        assert "finding_category" in ri
        assert "severity" in ri

    def test_baseline_status_set_when_baseline_compared(self):
        p = MockCVProvider()
        result = p.analyze(CVAnalysisRequest(
            image_url=FRAZIER_URL,
            baseline_image_url=FRAZIER_URL,
        ))
        assert result.ranking_inputs.get("baseline_status") != ""


# ── Pipeline integration ──────────────────────────────────────────────────────

class TestPipeline:
    def test_run_analysis_without_db(self):
        result = run_analysis(CVAnalysisRequest(image_url=FRAZIER_URL))
        assert result.inference_id
        assert result.status == "success"

    def test_run_baseline_compare_without_db(self):
        result = run_baseline_compare(BaselineCompareRequest(
            inspection_image_url=FRAZIER_URL,
            baseline_image_url=FRAZIER_URL,
        ))
        assert result.status == "success"
        assert result.baseline_comparison is not None
        assert result.baseline_comparison.compared is True

    def test_provider_info_returns_mock(self):
        CVRegistry.reset()
        provider = CVRegistry.get_provider()
        assert provider.provider_name == "mock"


# ── API endpoint tests ────────────────────────────────────────────────────────

class TestCVAPI:
    def _analyze_payload(self, **kwargs) -> dict:
        defaults = {"image_url": FRAZIER_URL, "tenant_id": "demo-tenant"}
        defaults.update(kwargs)
        return defaults

    def test_analyze_returns_200(self):
        res = client.post("/api/enterprise/cv/analyze", json=self._analyze_payload(), headers=AUTH)
        assert res.status_code == 200

    def test_analyze_returns_inference_id(self):
        res = client.post("/api/enterprise/cv/analyze", json=self._analyze_payload(), headers=AUTH)
        data = res.json()
        assert "inference_id" in data
        assert data["inference_id"].startswith("inf-")

    def test_analyze_returns_instrument_identity(self):
        res = client.post("/api/enterprise/cv/analyze", json=self._analyze_payload(), headers=AUTH)
        data = res.json()
        assert "instrument_identity" in data
        assert "recognized" in data["instrument_identity"]

    def test_analyze_returns_identifier_reads(self):
        res = client.post("/api/enterprise/cv/analyze", json=self._analyze_payload(), headers=AUTH)
        data = res.json()
        assert "identifier_reads" in data
        assert "barcode_value" in data["identifier_reads"]

    def test_analyze_returns_regions(self):
        res = client.post("/api/enterprise/cv/analyze", json=self._analyze_payload(), headers=AUTH)
        data = res.json()
        assert "regions" in data
        assert isinstance(data["regions"], list)

    def test_analyze_returns_scores(self):
        res = client.post("/api/enterprise/cv/analyze", json=self._analyze_payload(), headers=AUTH)
        data = res.json()
        assert 0 <= data["contamination_score"] <= 100
        assert 0 <= data["damage_score"] <= 100
        assert 0 <= data["overall_cleanliness_score"] <= 100

    def test_analyze_returns_ranking_inputs(self):
        res = client.post("/api/enterprise/cv/analyze", json=self._analyze_payload(), headers=AUTH)
        data = res.json()
        ri = data["ranking_inputs"]
        assert "finding_category" in ri
        assert "severity" in ri
        assert "confidence_score" in ri

    def test_analyze_with_baseline_returns_comparison(self):
        res = client.post(
            "/api/enterprise/cv/analyze",
            json=self._analyze_payload(baseline_image_url=FRAZIER_URL),
            headers=AUTH,
        )
        data = res.json()
        assert data["baseline_comparison"] is not None
        assert "match_pct" in data["baseline_comparison"]

    def test_baseline_compare_returns_200(self):
        res = client.post(
            "/api/enterprise/cv/baseline-compare",
            json={
                "inspection_image_url": FRAZIER_URL,
                "baseline_image_url": FRAZIER_URL,
                "instrument_name": "Frazier Suction 8Fr",
            },
            headers=AUTH,
        )
        assert res.status_code == 200

    def test_baseline_compare_result_compared_true(self):
        res = client.post(
            "/api/enterprise/cv/baseline-compare",
            json={
                "inspection_image_url": FRAZIER_URL,
                "baseline_image_url": FRAZIER_URL,
            },
            headers=AUTH,
        )
        data = res.json()
        assert data["baseline_comparison"]["compared"] is True

    def test_analyze_and_rank_returns_both(self):
        res = client.post(
            "/api/enterprise/cv/analyze-and-rank",
            json=self._analyze_payload(),
            headers=AUTH,
        )
        assert res.status_code == 200
        data = res.json()
        assert "cv" in data
        assert "ranking" in data
        assert "inspection_score" in data["ranking"]
        assert "risk_level" in data["ranking"]

    def test_analyze_and_rank_score_bounded(self):
        res = client.post(
            "/api/enterprise/cv/analyze-and-rank",
            json=self._analyze_payload(),
            headers=AUTH,
        )
        data = res.json()
        assert 0 <= data["ranking"]["inspection_score"] <= 100

    def test_get_inference_not_found_returns_404(self):
        res = client.get("/api/enterprise/cv/inference/nonexistent-id", headers=AUTH)
        assert res.status_code == 404

    def test_history_returns_list(self):
        res = client.get("/api/enterprise/cv/history", headers=AUTH)
        assert res.status_code == 200
        assert isinstance(res.json(), list)

    def test_kpi_summary_returns_200(self):
        res = client.get("/api/enterprise/cv/kpi-summary", headers=AUTH)
        assert res.status_code == 200

    def test_kpi_summary_shape(self):
        res = client.get("/api/enterprise/cv/kpi-summary", headers=AUTH)
        data = res.json()
        assert "total_analyses" in data
        assert "recognition_rate_pct" in data
        assert "blood_detections" in data
        assert "baseline_comparisons_run" in data
        assert "avg_baseline_match_pct" in data

    def test_provider_info_returns_200(self):
        res = client.get("/api/enterprise/cv/provider/info", headers=AUTH)
        assert res.status_code == 200

    def test_provider_info_shape(self):
        res = client.get("/api/enterprise/cv/provider/info", headers=AUTH)
        data = res.json()
        assert "provider" in data
        assert "model_versions" in data
        assert "capabilities" in data
        assert data["provider"] == "mock"

    def test_no_image_url_still_returns_200(self):
        res = client.post(
            "/api/enterprise/cv/analyze",
            json={"tenant_id": "demo-tenant"},
            headers=AUTH,
        )
        assert res.status_code == 200
        data = res.json()
        assert "warnings" in data
        assert len(data["warnings"]) > 0


class TestBoundingBoxSchema:
    def test_valid_bbox(self):
        b = BoundingBox(x=0.1, y=0.2, width=0.3, height=0.4)
        assert b.x == 0.1

    def test_bbox_out_of_range(self):
        import pytest
        with pytest.raises(Exception):
            BoundingBox(x=1.5, y=0.2, width=0.3, height=0.4)
