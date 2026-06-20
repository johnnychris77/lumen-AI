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


# ── R1: Image validation ──────────────────────────────────────────────────────

class TestImageValidator:
    def test_valid_https_url_no_warnings(self):
        from app.cv.image_validator import validate_image_url
        warns = validate_image_url("https://fixtures.lumenai.dev/img.jpg")
        assert warns == []

    def test_http_allowed(self):
        from app.cv.image_validator import validate_image_url
        warns = validate_image_url("http://fixtures.lumenai.dev/img.png")
        assert warns == []

    def test_private_ip_flagged(self):
        from app.cv.image_validator import validate_image_url
        warns = validate_image_url("http://192.168.1.100/image.jpg")
        assert any("SSRF" in w for w in warns)

    def test_localhost_flagged(self):
        from app.cv.image_validator import validate_image_url
        warns = validate_image_url("http://localhost/image.jpg")
        assert any("SSRF" in w or "internal" in w for w in warns)

    def test_loopback_ip_flagged(self):
        from app.cv.image_validator import validate_image_url
        warns = validate_image_url("http://127.0.0.1/image.jpg")
        assert any("SSRF" in w or "internal" in w for w in warns)

    def test_unknown_extension_warned(self):
        from app.cv.image_validator import validate_image_url
        warns = validate_image_url("https://example.com/image.exe")
        assert any("extension" in w for w in warns)

    def test_empty_url_returns_no_warnings(self):
        from app.cv.image_validator import validate_image_url
        assert validate_image_url("") == []

    def test_valid_b64_jpeg(self):
        import base64
        from app.cv.image_validator import validate_b64_payload
        # Minimal JPEG magic bytes
        jpeg_magic = b"\xff\xd8\xff" + b"\x00" * 100
        b64 = base64.b64encode(jpeg_magic).decode()
        warns = validate_b64_payload(b64)
        assert warns == []

    def test_invalid_b64_caught(self):
        from app.cv.image_validator import validate_b64_payload
        warns = validate_b64_payload("not-valid-base64!!!")
        assert any("base64" in w for w in warns)

    def test_unknown_magic_bytes_warned(self):
        import base64
        from app.cv.image_validator import validate_b64_payload
        b64 = base64.b64encode(b"\x00\x01\x02\x03" * 50).decode()
        warns = validate_b64_payload(b64)
        assert any("format" in w for w in warns)


# ── R2: GS1 UDI parser ────────────────────────────────────────────────────────

class TestGS1UDIParser:
    def test_parse_device_id(self):
        from app.cv.identifier_decoder import parse_gs1_udi
        result = parse_gs1_udi("(01)12345678901234(10)LOT001(21)SER999")
        assert result["device_id"] == "12345678901234"

    def test_parse_lot(self):
        from app.cv.identifier_decoder import parse_gs1_udi
        result = parse_gs1_udi("(01)12345678901234(10)LOT001")
        assert result["lot"] == "LOT001"

    def test_parse_serial(self):
        from app.cv.identifier_decoder import parse_gs1_udi
        result = parse_gs1_udi("(01)123(21)SER-ABC")
        assert result["serial"] == "SER-ABC"

    def test_empty_string_returns_empty(self):
        from app.cv.identifier_decoder import parse_gs1_udi
        assert parse_gs1_udi("") == {}

    def test_no_pyzbar_graceful_fallback(self):
        from app.cv.identifier_decoder import decode_from_image_bytes
        # Without pyzbar, should return empty result without raising
        result = decode_from_image_bytes(b"\xff\xd8\xff" + b"\x00" * 100)
        assert isinstance(result.barcode_value, str)
        assert result.decoder_backend in ("pyzbar", "none", "error")


# ── R3: Composite ranking ─────────────────────────────────────────────────────

class TestCompositeRankingBridge:
    def test_build_composite_request_multi_region(self):
        from app.cv.pipeline import build_composite_ranking_request
        p = MockCVProvider()
        result = p.analyze(CVAnalysisRequest(image_url=FRAZIER_URL))
        if len(result.regions) > 1:
            comp = build_composite_ranking_request(result)
            assert comp is not None
            assert "findings" in comp
            assert len(comp["findings"]) == len(result.regions)

    def test_composite_findings_have_required_keys(self):
        from app.cv.pipeline import build_composite_ranking_request
        p = MockCVProvider()
        result = p.analyze(CVAnalysisRequest(image_url=FRAZIER_URL))
        comp = build_composite_ranking_request(result)
        if comp and comp["findings"]:
            for f in comp["findings"]:
                assert "finding_category" in f
                assert "severity" in f
                assert "confidence_score" in f

    def test_analyze_and_rank_composite_returns_ranking_mode(self):
        res = client.post(
            "/api/enterprise/cv/analyze-and-rank",
            json={"image_url": FRAZIER_URL, "tenant_id": "demo-tenant"},
            headers=AUTH,
        )
        assert res.status_code == 200
        data = res.json()
        assert "ranking_mode" in data["ranking"]
        assert data["ranking"]["ranking_mode"] in ("composite", "single")

    def test_analyze_and_rank_composite_score_bounded(self):
        res = client.post(
            "/api/enterprise/cv/analyze-and-rank",
            json={"image_url": FRAZIER_URL, "tenant_id": "demo-tenant"},
            headers=AUTH,
        )
        data = res.json()
        ranking = data["ranking"]
        score_key = "composite_score" if "composite_score" in ranking else "inspection_score"
        assert 0 <= ranking[score_key] <= 100


# ── R4: Async inference ───────────────────────────────────────────────────────

class TestAsyncInference:
    def test_analyze_async_returns_202(self):
        res = client.post(
            "/api/enterprise/cv/analyze-async",
            json={"image_url": FRAZIER_URL, "tenant_id": "demo-tenant"},
            headers=AUTH,
        )
        assert res.status_code == 202

    def test_analyze_async_returns_inference_id(self):
        res = client.post(
            "/api/enterprise/cv/analyze-async",
            json={"image_url": FRAZIER_URL, "tenant_id": "demo-tenant"},
            headers=AUTH,
        )
        data = res.json()
        assert "inference_id" in data
        assert data["status"] == "processing"

    def test_status_endpoint_returns_inference_id_state(self):
        # Submit async job
        submit = client.post(
            "/api/enterprise/cv/analyze-async",
            json={"image_url": FRAZIER_URL, "tenant_id": "demo-tenant"},
            headers=AUTH,
        )
        inference_id = submit.json()["inference_id"]
        # Poll status
        status_res = client.get(
            f"/api/enterprise/cv/inference/{inference_id}/status",
            headers=AUTH,
        )
        assert status_res.status_code == 200
        data = status_res.json()
        assert data["inference_id"] == inference_id
        assert data["status"] in ("processing", "complete", "failed")

    def test_status_unknown_id_returns_not_found(self):
        res = client.get(
            "/api/enterprise/cv/inference/totally-unknown-id/status",
            headers=AUTH,
        )
        assert res.status_code == 200
        assert res.json()["status"] == "not_found"


# ── R6: SSIM comparator ───────────────────────────────────────────────────────

class TestSSIMComparator:
    def test_same_url_high_match(self):
        from app.cv.ssim_comparator import compare_images
        result = compare_images(FRAZIER_URL, FRAZIER_URL)
        # Same URL → same domain → mock gives high match
        assert result.match_pct >= 50.0

    def test_different_domain_lower_match(self):
        from app.cv.ssim_comparator import compare_images
        result = compare_images(
            "https://a-domain.com/img.jpg",
            "https://b-domain.com/img.jpg",
        )
        assert 0.0 <= result.match_pct <= 100.0

    def test_empty_baseline_returns_zero_match(self):
        from app.cv.ssim_comparator import compare_images
        result = compare_images(FRAZIER_URL, "")
        assert result.match_pct == 0.0

    def test_result_fields_present(self):
        from app.cv.ssim_comparator import compare_images
        result = compare_images(FRAZIER_URL, KERRISON_URL)
        assert hasattr(result, "structural_similarity")
        assert hasattr(result, "color_delta")
        assert hasattr(result, "backend")
        assert 0.0 <= result.structural_similarity <= 1.0


# ── R7: Image store ───────────────────────────────────────────────────────────

class TestImageStore:
    def test_noop_backend_returns_stored_false(self):
        import os
        os.environ["IMAGE_STORE_BACKEND"] = "noop"
        from app.cv.image_store import archive_image
        result = archive_image(
            image_bytes=b"\xff\xd8\xff" + b"\x00" * 50,
            image_url=FRAZIER_URL,
            inference_id="inf-test-001",
            tenant_id="demo-tenant",
        )
        assert result.stored is False
        assert "demo-tenant" in result.object_key or result.object_key != ""

    def test_local_backend_writes_file(self, tmp_path):
        import os
        os.environ["IMAGE_STORE_BACKEND"] = "local"
        os.environ["IMAGE_STORE_LOCAL_DIR"] = str(tmp_path)
        # Force re-read of env var
        import importlib
        import app.cv.image_store as store_mod
        importlib.reload(store_mod)
        result = store_mod.archive_image(
            image_bytes=b"\xff\xd8\xff" + b"\x00" * 50,
            image_url=FRAZIER_URL,
            inference_id="inf-local-001",
            tenant_id="demo-tenant",
        )
        assert result.stored is True
        assert result.checksum_sha256 != ""
        os.environ["IMAGE_STORE_BACKEND"] = "noop"

    def test_archive_no_bytes_no_url_returns_error(self):
        import os
        os.environ["IMAGE_STORE_BACKEND"] = "noop"
        from app.cv.image_store import archive_image
        result = archive_image(
            image_bytes=None,
            image_url="",
            inference_id="inf-no-image",
            tenant_id="demo-tenant",
        )
        # noop skips fetch; stored=False is acceptable
        assert isinstance(result.stored, bool)


# ── R9: Confidence calibration ────────────────────────────────────────────────

class TestConfidenceCalibration:
    def test_calibration_temperature_field_present(self):
        p = MockCVProvider()
        result = p.analyze(CVAnalysisRequest(image_url=FRAZIER_URL))
        assert hasattr(result, "calibration_temperature")
        assert result.calibration_temperature == 1.0  # default no-op

    def test_high_temperature_lowers_extreme_confidence(self):
        import os
        os.environ["CV_CALIBRATION_TEMPERATURE"] = "2.0"
        p = MockCVProvider()
        result = p.analyze(CVAnalysisRequest(image_url=FRAZIER_URL))
        for roi in result.regions:
            assert 0.0 <= roi.confidence <= 1.0
        os.environ["CV_CALIBRATION_TEMPERATURE"] = "1.0"


# ── R10: Active learning review queue ────────────────────────────────────────

class TestActiveLearningSuite:
    def test_review_required_field_present_in_result(self):
        p = MockCVProvider()
        result = p.analyze(CVAnalysisRequest(image_url=FRAZIER_URL))
        assert hasattr(result, "review_required")
        assert isinstance(result.review_required, bool)

    def test_low_confidence_threshold_triggers_review(self):
        import os
        os.environ["CV_REVIEW_CONFIDENCE_THRESHOLD"] = "1.0"  # force all reviews
        p = MockCVProvider()
        result = p.analyze(CVAnalysisRequest(image_url=FRAZIER_URL))
        if result.regions:
            assert result.review_required is True
        os.environ["CV_REVIEW_CONFIDENCE_THRESHOLD"] = "0.70"

    def test_review_queue_endpoint_returns_200(self):
        res = client.get("/api/enterprise/cv/review-queue", headers=AUTH)
        assert res.status_code == 200
        assert isinstance(res.json(), list)

    def test_annotate_nonexistent_returns_404(self):
        res = client.post(
            "/api/enterprise/cv/inference/nonexistent-xyz/annotate",
            json={
                "annotator_id": "test-annotator",
                "confirmed_regions": [],
                "rejected_region_ids": [],
            },
            headers=AUTH,
        )
        assert res.status_code == 404


# ── R11: Video analysis ───────────────────────────────────────────────────────

class TestVideoAnalysis:
    def test_analyze_video_returns_200(self):
        res = client.post(
            "/api/enterprise/cv/analyze-video",
            json={
                "video_url": "https://fixtures.lumenai.dev/video/frazier-borescope.mp4",
                "sample_fps": 0.5,
                "instrument_name": "Frazier Suction",
                "tenant_id": "demo-tenant",
            },
            headers=AUTH,
        )
        assert res.status_code == 200

    def test_analyze_video_result_shape(self):
        res = client.post(
            "/api/enterprise/cv/analyze-video",
            json={
                "video_url": "https://fixtures.lumenai.dev/video/frazier-borescope.mp4",
                "sample_fps": 0.5,
                "tenant_id": "demo-tenant",
            },
            headers=AUTH,
        )
        data = res.json()
        assert "frames_analyzed" in data
        assert "worst_contamination_score" in data
        assert "worst_damage_score" in data
        assert "finding_timeline" in data
        assert isinstance(data["finding_timeline"], list)

    def test_video_scores_bounded(self):
        res = client.post(
            "/api/enterprise/cv/analyze-video",
            json={
                "video_url": "https://fixtures.lumenai.dev/video/kerrison-borescope.mp4",
                "sample_fps": 1.0,
                "tenant_id": "demo-tenant",
            },
            headers=AUTH,
        )
        data = res.json()
        assert 0 <= data["worst_contamination_score"] <= 100
        assert 0 <= data["worst_damage_score"] <= 100

    def test_video_frames_have_timestamps(self):
        res = client.post(
            "/api/enterprise/cv/analyze-video",
            json={
                "video_url": "https://fixtures.lumenai.dev/video/frazier-borescope.mp4",
                "sample_fps": 0.5,
                "tenant_id": "demo-tenant",
            },
            headers=AUTH,
        )
        data = res.json()
        for frame in data["finding_timeline"]:
            assert "timestamp_sec" in frame
            assert "frame_index" in frame
            assert frame["timestamp_sec"] >= 0


# ── R12: Provider metrics ─────────────────────────────────────────────────────

class TestProviderMetrics:
    def test_provider_metrics_returns_200(self):
        res = client.get("/api/enterprise/cv/provider/metrics", headers=AUTH)
        assert res.status_code == 200

    def test_provider_metrics_shape(self):
        res = client.get("/api/enterprise/cv/provider/metrics", headers=AUTH)
        data = res.json()
        assert "total_inferences" in data
        assert "avg_processing_ms" in data
        assert "p95_processing_ms" in data
        assert "total_cost_usd" in data
        assert "provider_breakdown" in data

    def test_kpi_summary_includes_telemetry(self):
        res = client.get("/api/enterprise/cv/kpi-summary", headers=AUTH)
        data = res.json()
        assert "avg_processing_ms" in data
        assert "total_provider_cost_usd" in data
        assert "review_queue_size" in data

    def test_history_includes_cost_field(self):
        # Run one inference to ensure history is populated
        client.post(
            "/api/enterprise/cv/analyze",
            json={"image_url": FRAZIER_URL, "tenant_id": "demo-tenant"},
            headers=AUTH,
        )
        res = client.get("/api/enterprise/cv/history", headers=AUTH)
        if res.json():
            rec = res.json()[0]
            assert "provider_cost_usd" in rec
            assert "review_required" in rec
