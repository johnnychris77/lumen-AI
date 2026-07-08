"""LumenAI Inspect v2.2 — Vision Intelligence & Multi-Image Clinical
Reasoning ("Project Vision 360").

Covers: multiple image upload, anatomy grouping, image quality scoring,
duplicate detection, missing anatomy detection, cross-image reasoning,
inspection gallery, and evidence fusion.
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.db.session import SessionLocal
from app.main import app
from app.models.baseline_library import BaselineLibraryEntry
from app.models.inspection_image_tag import InspectionImageTag
from app.services.duplicate_detection_service import detect_all
from app.services.image_quality_engine import QUALITY_BANDS, score_image
from app.services.vision_session_engine import (
    cross_image_reasoning, evidence_fusion, image_timeline, missing_anatomy_prompts,
)

client = TestClient(app)
AUTH_ADMIN = {"Authorization": "Bearer dev-token"}
AUTH_VIEWER = {"Authorization": "Bearer viewer-token"}
SHA_A = "a1" * 32
SHA_B = "b2" * 32


def _baseline(itype: str) -> None:
    db = SessionLocal()
    try:
        db.query(BaselineLibraryEntry).filter(BaselineLibraryEntry.instrument_category == itype).delete()
        db.add(BaselineLibraryEntry(
            udi=f"v22-{itype}", instrument_category=itype, manufacturer_name="M",
            model_name="X", baseline_type="manufacturer", approval_status="approved",
        ))
        db.commit()
    finally:
        db.close()


def _create_session(instrument_type: str, tags: list[dict], finding_categories=None) -> dict:
    _baseline(instrument_type)
    r = client.post("/api/inspections", headers=AUTH_ADMIN, json={
        "instrument_type": instrument_type, "site_name": "Main OR", "has_image": True,
        "image_sha256": SHA_A, "file_name": "x.jpg",
        "finding_categories": finding_categories or [],
        "image_view_tags": tags,
    })
    assert r.status_code == 201, r.text
    return r.json()


class TestMultiImageUpload:
    def test_multiple_images_persist_as_separate_tags(self):
        insp = _create_session("kerrison_rongeur", [
            {"instrument_family": "kerrison_rongeur", "anatomy_zone": "jaw", "image_view": "jaw close-up",
             "image_sha256": SHA_A, "technician": "tech1"},
            {"instrument_family": "kerrison_rongeur", "anatomy_zone": "box lock", "image_view": "box lock open",
             "image_sha256": SHA_B, "technician": "tech1"},
        ])
        r = client.get(f"/api/inspections/{insp['id']}/vision-session", headers=AUTH_ADMIN)
        assert r.status_code == 200
        body = r.json()
        assert body["image_count"] == 2
        assert {i["anatomy_zone"] for i in body["images"]} == {"jaw", "box lock"}

    def test_each_image_carries_technician_and_sequence(self):
        insp = _create_session("scissors", [
            {"instrument_family": "scissors", "anatomy_zone": "blade", "image_view": "blade",
             "image_sha256": SHA_A, "technician": "jsmith", "sequence": 0},
            {"instrument_family": "scissors", "anatomy_zone": "box lock", "image_view": "box lock",
             "image_sha256": SHA_B, "technician": "jsmith", "sequence": 1},
        ])
        db = SessionLocal()
        try:
            rows = db.query(InspectionImageTag).filter(InspectionImageTag.inspection_id == insp["id"]).all()
        finally:
            db.close()
        assert all(r.technician == "jsmith" for r in rows)
        assert sorted(r.sequence for r in rows) == [0, 1]


class TestAnatomyGrouping:
    def test_gallery_groups_images_by_anatomy_zone(self):
        insp = _create_session("kerrison_rongeur", [
            {"instrument_family": "kerrison_rongeur", "anatomy_zone": "jaw", "image_view": "view a", "image_sha256": SHA_A},
            {"instrument_family": "kerrison_rongeur", "anatomy_zone": "jaw", "image_view": "view b", "image_sha256": SHA_B},
            {"instrument_family": "kerrison_rongeur", "anatomy_zone": "box lock", "image_view": "view c", "image_sha256": "c3" * 32},
        ])
        r = client.get(f"/api/inspections/{insp['id']}/gallery", headers=AUTH_ADMIN)
        assert r.status_code == 200
        body = r.json()
        by_zone = {g["anatomy_zone"]: g["images"] for g in body["groups"]}
        assert len(by_zone["jaw"]) == 2
        assert len(by_zone["box lock"]) == 1
        assert body["total_images"] == 3


class TestImageQualityScoring:
    def test_scores_are_deterministic_for_the_same_image(self):
        first = score_image(SHA_A)
        second = score_image(SHA_A)
        assert first == second

    def test_different_images_can_score_differently(self):
        a = score_image(SHA_A)
        b = score_image(SHA_B)
        assert a["metrics"] != b["metrics"] or a["overall_score"] != b["overall_score"]

    def test_all_eight_metrics_present(self):
        result = score_image(SHA_A)
        assert set(result["metrics"]) == {
            "focus", "blur", "lighting", "exposure", "glare",
            "field_coverage", "obstruction", "perspective",
        }

    def test_band_is_one_of_the_five_named_bands(self):
        result = score_image(SHA_A)
        assert result["quality_band"] in QUALITY_BANDS

    def test_quality_score_persisted_on_the_image_tag(self):
        insp = _create_session("scissors", [
            {"instrument_family": "scissors", "anatomy_zone": "blade", "image_view": "blade", "image_sha256": SHA_A},
        ])
        db = SessionLocal()
        try:
            tag = db.query(InspectionImageTag).filter(InspectionImageTag.inspection_id == insp["id"]).first()
        finally:
            db.close()
        assert tag.quality_score is not None
        assert tag.quality_band in QUALITY_BANDS

    def test_untagged_images_get_distinguishable_scores_via_fallback_seed(self):
        a = score_image(None, fallback_key="1:jaw:0")
        b = score_image(None, fallback_key="1:box lock:1")
        assert a != b


class TestDuplicateDetection:
    def test_identical_hash_flagged_as_duplicate(self):
        tags = [
            {"id": 1, "image_sha256": SHA_A, "anatomy_zone": "jaw", "instrument_family": "kerrison_rongeur"},
            {"id": 2, "image_sha256": SHA_A, "anatomy_zone": "jaw", "instrument_family": "kerrison_rongeur"},
        ]
        result = detect_all(tags)
        assert result["has_warnings"] is True
        assert any(f["type"] == "duplicate_image" for f in result["findings"])

    def test_wrong_anatomy_zone_flagged(self):
        tags = [
            {"id": 1, "image_sha256": SHA_A, "anatomy_zone": "not-a-real-zone", "instrument_family": "kerrison_rongeur"},
        ]
        result = detect_all(tags)
        assert any(f["type"] == "wrong_anatomy" for f in result["findings"])

    def test_mixed_instrument_families_flagged(self):
        tags = [
            {"id": 1, "image_sha256": SHA_A, "anatomy_zone": "jaw", "instrument_family": "kerrison_rongeur"},
            {"id": 2, "image_sha256": SHA_B, "anatomy_zone": "blade", "instrument_family": "scissors"},
        ]
        result = detect_all(tags)
        assert any(f["type"] == "wrong_instrument" for f in result["findings"])

    def test_no_warnings_for_a_clean_session(self):
        tags = [
            {"id": 1, "image_sha256": SHA_A, "anatomy_zone": "jaw", "instrument_family": "kerrison_rongeur"},
            {"id": 2, "image_sha256": SHA_B, "anatomy_zone": "box lock", "instrument_family": "kerrison_rongeur"},
        ]
        result = detect_all(tags)
        assert result["has_warnings"] is False

    def test_duplicate_detection_surfaced_on_the_vision_session_endpoint(self):
        insp = _create_session("kerrison_rongeur", [
            {"instrument_family": "kerrison_rongeur", "anatomy_zone": "jaw", "image_view": "a", "image_sha256": SHA_A},
            {"instrument_family": "kerrison_rongeur", "anatomy_zone": "jaw", "image_view": "b", "image_sha256": SHA_A},
        ])
        r = client.get(f"/api/inspections/{insp['id']}/vision-session", headers=AUTH_ADMIN)
        assert r.json()["duplicate_detection"]["has_warnings"] is True


class TestMissingAnatomyDetection:
    def test_prompts_name_every_missing_required_zone(self):
        tags = [{"id": 1, "anatomy_zone": "jaw", "image_view": "", "instrument_family": "kerrison_rongeur",
                 "image_sha256": None, "capture_quality": "good", "quality_score": None, "quality_band": None,
                 "technician": "", "sequence": 0, "flagged": False, "flag_reason": "", "created_at": None, "notes": ""}]
        result = missing_anatomy_prompts("kerrison rongeur", tags)
        assert any("serrations" in p["message"] for p in result["prompts"])
        assert result["suggested_next"] is not None

    def test_no_prompts_once_fully_captured(self):
        from app.services.instrument_anatomy import get_anatomy

        anatomy = get_anatomy("kerrison rongeur")
        tags = [
            {"id": i, "anatomy_zone": z, "image_view": "", "instrument_family": "kerrison_rongeur",
             "image_sha256": None, "capture_quality": "good", "quality_score": None, "quality_band": None,
             "technician": "", "sequence": i, "flagged": False, "flag_reason": "", "created_at": None, "notes": ""}
            for i, z in enumerate(anatomy["required_images"])
        ]
        result = missing_anatomy_prompts("kerrison rongeur", tags)
        assert result["prompts"] == []
        assert result["suggested_next"] is None

    def test_missing_anatomy_reachable_via_vision_session_endpoint(self):
        insp = _create_session("kerrison_rongeur", [
            {"instrument_family": "kerrison_rongeur", "anatomy_zone": "jaw", "image_view": "a", "image_sha256": SHA_A},
        ])
        r = client.get(f"/api/inspections/{insp['id']}/vision-session", headers=AUTH_ADMIN)
        prompts = r.json()["missing_anatomy"]["prompts"]
        assert any("You have not captured" in p["message"] for p in prompts)


class TestCrossImageReasoning:
    def test_finding_in_one_image_is_not_cancelled_by_a_clean_other(self):
        findings = [
            {"type": "blood", "instrument_zone": "jaw", "status": "escalate", "severity_index": 3},
            {"type": "blood", "instrument_zone": "box lock", "status": "clear", "severity_index": 0},
        ]
        tags = [
            {"id": 1, "anatomy_zone": "jaw"},
            {"id": 2, "anatomy_zone": "box lock"},
        ]
        result = cross_image_reasoning(findings, tags)
        assert result["contamination_found"] is True
        assert "contamination" in result["overall_result"].lower()

    def test_findings_matched_to_the_right_image_tag(self):
        findings = [{"type": "crack", "instrument_zone": "jaw", "status": "escalate", "severity_index": 3}]
        tags = [{"id": 42, "anatomy_zone": "jaw"}, {"id": 43, "anatomy_zone": "box lock"}]
        result = cross_image_reasoning(findings, tags)
        assert result["per_finding"][0]["matched_image_tag_ids"] == [42]

    def test_no_findings_reports_clean_result(self):
        result = cross_image_reasoning([], [{"id": 1, "anatomy_zone": "jaw"}])
        assert result["contamination_found"] is False
        assert result["structural_found"] is False


class TestInspectionGallery:
    def test_gallery_requires_authentication(self):
        r = client.get("/api/inspections/1/gallery")
        assert r.status_code in (401, 403)

    def test_flag_and_unflag_an_image(self):
        insp = _create_session("scissors", [
            {"instrument_family": "scissors", "anatomy_zone": "blade", "image_view": "blade", "image_sha256": SHA_A},
        ])
        gallery = client.get(f"/api/inspections/{insp['id']}/gallery", headers=AUTH_ADMIN).json()
        tag_id = gallery["groups"][0]["images"][0]["id"]

        r = client.post(
            f"/api/inspections/{insp['id']}/images/{tag_id}/flag",
            headers=AUTH_ADMIN, json={"flagged": True, "reason": "blurry"},
        )
        assert r.status_code == 200
        assert r.json()["flagged"] is True
        assert r.json()["flag_reason"] == "blurry"

        r2 = client.post(
            f"/api/inspections/{insp['id']}/images/{tag_id}/flag",
            headers=AUTH_ADMIN, json={"flagged": False},
        )
        assert r2.json()["flagged"] is False

    def test_flagging_unknown_image_404s(self):
        insp = _create_session("scissors", [
            {"instrument_family": "scissors", "anatomy_zone": "blade", "image_view": "blade", "image_sha256": SHA_A},
        ])
        r = client.post(
            f"/api/inspections/{insp['id']}/images/999999/flag",
            headers=AUTH_ADMIN, json={"flagged": True, "reason": "x"},
        )
        assert r.status_code == 404


class TestEvidenceFusion:
    def test_clean_session_with_full_coverage_recommends_pass(self):
        from app.services.instrument_anatomy import get_anatomy

        anatomy = get_anatomy("scissors")
        tags = [
            {"id": i, "anatomy_zone": z} for i, z in enumerate(anatomy["required_images"])
        ]
        coverage = {"quality": "complete"}
        result = evidence_fusion(
            predicted_findings=[], tag_dicts=tags, coverage=coverage,
            baseline_source="manufacturer", supervisor_reviews=[],
        )
        assert result["recommendation"] == "PASS"
        assert result["human_review_required"] is True

    def test_contamination_recommends_reprocess(self):
        findings = [{"type": "blood", "instrument_zone": "jaw", "status": "escalate", "severity_index": 3}]
        tags = [{"id": 1, "anatomy_zone": "jaw"}]
        result = evidence_fusion(
            predicted_findings=findings, tag_dicts=tags, coverage={"quality": "acceptable"},
            baseline_source="manufacturer", supervisor_reviews=[],
        )
        assert result["recommendation"] == "REPROCESS"

    def test_incomplete_coverage_routes_to_supervisor_review(self):
        result = evidence_fusion(
            predicted_findings=[], tag_dicts=[{"id": 1, "anatomy_zone": "jaw"}],
            coverage={"quality": "insufficient"}, baseline_source=None, supervisor_reviews=[],
        )
        assert result["recommendation"] == "SUPERVISOR REVIEW"

    def test_contributing_factors_include_all_five_evidence_sources(self):
        result = evidence_fusion(
            predicted_findings=[], tag_dicts=[], coverage={"quality": "not_assessed"},
            baseline_source="vendor", supervisor_reviews=[],
        )
        factors = result["contributing_factors"]
        for key in ("image_evidence", "baseline_comparison", "coverage", "average_confidence", "supervisor_agreement_rate"):
            assert key in factors

    def test_evidence_fusion_reachable_via_vision_session_endpoint(self):
        insp = _create_session("scissors", [
            {"instrument_family": "scissors", "anatomy_zone": "blade", "image_view": "blade", "image_sha256": SHA_A},
        ])
        r = client.get(f"/api/inspections/{insp['id']}/vision-session", headers=AUTH_ADMIN)
        fusion = r.json()["evidence_fusion"]
        assert fusion["recommendation"] in ("PASS", "MONITOR", "SUPERVISOR REVIEW", "REPROCESS", "REMOVE FROM SERVICE")
        assert fusion["human_review_required"] is True


class TestImageTimeline:
    def test_timeline_is_ordered_by_sequence(self):
        tags = [
            {"id": 2, "anatomy_zone": "box lock", "image_view": "b", "sequence": 1, "quality_band": "good", "flagged": False},
            {"id": 1, "anatomy_zone": "jaw", "image_view": "a", "sequence": 0, "quality_band": "acceptable", "flagged": False},
        ]
        timeline = image_timeline(tags)
        assert [t["tag_id"] for t in timeline] == [1, 2]
        assert timeline[0]["sequence"] == 1
        assert timeline[1]["sequence"] == 2
