"""LumenAI Inspect v1.2 — Guided Capture & Coverage Workflow.

Covers the v1.2 scenario checklist:
  - missing high-risk zone warning
  - complete coverage allows final analysis
  - insufficient coverage requires warning
  - supervisor override requires reason
  - image view tags are included in AI context

Plus endpoint coverage for the new guided-capture panel, image-tag
persistence, and the coverage-override gate.
"""
from __future__ import annotations

import os

from fastapi.testclient import TestClient

from app.main import app
from app.db.session import SessionLocal
from app.models.baseline_library import BaselineLibraryEntry
from app.models.inspection_image_tag import InspectionImageTag
from app.services.guided_capture import coverage_readiness, guided_capture_panel
from app.services.instrument_anatomy import get_anatomy

client = TestClient(app)
AUTH_ADMIN = {"Authorization": "Bearer dev-token"}
AUTH_VIEWER = {"Authorization": "Bearer viewer-token"}
SHA = "beadfeed" + "0" * 56


def _baseline(itype: str) -> None:
    db = SessionLocal()
    try:
        db.query(BaselineLibraryEntry).filter(
            BaselineLibraryEntry.instrument_category == itype
        ).delete()
        db.add(BaselineLibraryEntry(
            udi=f"v12-{itype}", instrument_category=itype, manufacturer_name="M",
            model_name="X", baseline_type="manufacturer", approval_status="approved",
        ))
        db.commit()
    finally:
        db.close()


def _create_inspection(instrument_type: str, inspected_zones=None, image_view_tags=None, save_as_draft=False):
    _baseline(instrument_type)
    return client.post(
        "/api/inspections",
        headers=AUTH_ADMIN,
        json={
            "instrument_type": instrument_type,
            "site_name": "Main OR",
            "has_image": True,
            "image_sha256": SHA,
            "inspected_zones": inspected_zones,
            "image_view_tags": image_view_tags,
            "save_as_draft": save_as_draft,
        },
    )


class TestMissingHighRiskZoneWarning:
    def test_guided_capture_panel_flags_missing_high_risk_zone(self):
        r = client.get(
            "/api/guided-capture/kerrison%20rongeur?captured_zones=jaw",
            headers=AUTH_ADMIN,
        )
        assert r.status_code == 200
        body = r.json()
        assert body["missing_high_risk_zones"]
        assert set(body["missing_high_risk_zones"]) <= set(body["high_risk_zones"])

    def test_coverage_readiness_flags_missing_high_risk_zone(self):
        readiness = coverage_readiness("kerrison rongeur", ["jaw"])
        assert readiness["missing_high_risk_zones"]


class TestCompleteCoverageAllowsFinalAnalysis:
    def test_full_required_zones_ready_for_ai_analysis(self):
        anatomy = get_anatomy("kerrison rongeur")
        readiness = coverage_readiness("kerrison rongeur", anatomy["required_images"])
        assert readiness["ready_for_ai_analysis"] is True
        assert readiness["gate_status"] == "ready"

    def test_inspection_with_full_coverage_is_not_blocked(self):
        anatomy = get_anatomy("kerrison rongeur")
        r = _create_inspection("kerrison_rongeur", inspected_zones=anatomy["required_images"])
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["coverage_gate_status"] == "ready"
        assert body["is_draft"] is False


class TestInsufficientCoverageRequiresWarning:
    def test_guided_capture_panel_warns_when_gate_not_ready(self, monkeypatch):
        monkeypatch.setenv("REQUIRE_FULL_COVERAGE_BEFORE_FINAL_DECISION", "true")

        r = client.get(
            "/api/guided-capture/kerrison%20rongeur?captured_zones=jaw",
            headers=AUTH_ADMIN,
        )
        assert r.status_code == 200
        body = r.json()
        assert body["ready_for_ai_analysis"] is False
        assert body["gate_status"] == "blocked_pending_override"
        monkeypatch.delenv("REQUIRE_FULL_COVERAGE_BEFORE_FINAL_DECISION", raising=False)

    def test_inspection_blocked_pending_override_when_policy_requires_coverage(self, monkeypatch):
        monkeypatch.setenv("REQUIRE_FULL_COVERAGE_BEFORE_FINAL_DECISION", "true")
        r = _create_inspection("kerrison_rongeur", inspected_zones=["jaw"])
        monkeypatch.delenv("REQUIRE_FULL_COVERAGE_BEFORE_FINAL_DECISION", raising=False)
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["coverage_gate_status"] == "blocked_pending_override"
        assert body["is_draft"] is True

    def test_save_as_draft_flags_inspection_regardless_of_policy(self):
        r = _create_inspection("kerrison_rongeur", inspected_zones=["jaw"], save_as_draft=True)
        assert r.status_code == 201, r.text
        assert r.json()["is_draft"] is True


class TestSupervisorOverrideRequiresReason:
    def test_override_without_reason_rejected(self):
        os.environ["REQUIRE_FULL_COVERAGE_BEFORE_FINAL_DECISION"] = "true"
        try:
            r = _create_inspection("kerrison_rongeur", inspected_zones=["jaw"])
        finally:
            os.environ.pop("REQUIRE_FULL_COVERAGE_BEFORE_FINAL_DECISION", None)
        iid = r.json()["id"]

        override = client.post(
            f"/api/inspections/{iid}/coverage-override",
            headers=AUTH_ADMIN,
            json={"reason": "too short"},
        )
        # "too short" is 9 chars — below the 10-char minimum.
        assert override.status_code == 422

    def test_override_with_reason_unlocks_gate(self):
        os.environ["REQUIRE_FULL_COVERAGE_BEFORE_FINAL_DECISION"] = "true"
        try:
            r = _create_inspection("kerrison_rongeur", inspected_zones=["jaw"])
        finally:
            os.environ.pop("REQUIRE_FULL_COVERAGE_BEFORE_FINAL_DECISION", None)
        iid = r.json()["id"]
        assert r.json()["coverage_gate_status"] == "blocked_pending_override"

        override = client.post(
            f"/api/inspections/{iid}/coverage-override",
            headers=AUTH_ADMIN,
            json={"reason": "Supervisor confirmed adequate coverage via manual inspection."},
        )
        assert override.status_code == 200, override.text
        body = override.json()
        assert body["coverage_gate_status"] == "ready"
        assert body["coverage_override_by"]
        assert body["coverage_override_reason"]

    def test_viewer_cannot_apply_override(self):
        r = _create_inspection("kerrison_rongeur", inspected_zones=["jaw"])
        iid = r.json()["id"]
        override = client.post(
            f"/api/inspections/{iid}/coverage-override",
            headers=AUTH_VIEWER,
            json={"reason": "Attempting override without authorization."},
        )
        assert override.status_code == 403


class TestImageViewTagsIncludedInAIContext:
    def test_analysis_result_includes_image_view_tags(self):
        tags = [{
            "instrument_family": "kerrison_rongeur",
            "anatomy_zone": "jaw",
            "image_view": "jaw close-up",
            "capture_quality": "good",
            "notes": "clear view of serrations",
        }]
        r = _create_inspection("kerrison_rongeur", inspected_zones=["jaw"], image_view_tags=tags)
        assert r.status_code == 201, r.text
        analysis = r.json()["analysis"]
        # v2.2 additively echoes back image_sha256/technician/sequence
        # alongside the original v1.2 fields — check those, not exact equality.
        echoed = analysis["image_view_tags"][0]
        assert all(echoed[k] == v for k, v in tags[0].items())

    def test_image_tags_persisted_and_listable(self):
        tags = [{
            "instrument_family": "kerrison_rongeur",
            "anatomy_zone": "jaw",
            "image_view": "jaw close-up",
            "capture_quality": "good",
            "notes": "",
        }]
        r = _create_inspection("kerrison_rongeur", inspected_zones=["jaw"], image_view_tags=tags)
        iid = r.json()["id"]

        listing = client.get(f"/api/inspections/{iid}/image-tags", headers=AUTH_ADMIN)
        assert listing.status_code == 200
        body = listing.json()
        assert body["count"] == 1
        assert body["tags"][0]["anatomy_zone"] == "jaw"
        assert body["tags"][0]["capture_quality"] == "good"

        db = SessionLocal()
        try:
            row = db.query(InspectionImageTag).filter(InspectionImageTag.inspection_id == iid).first()
            assert row is not None
            assert row.image_view == "jaw close-up"
        finally:
            db.close()


class TestGuidedCapturePanelService:
    def test_panel_prioritizes_high_risk_zone_next(self):
        panel = guided_capture_panel("kerrison rongeur", ["jaw"])
        assert panel["current_zone"] in panel["high_risk_zones"]

    def test_panel_reports_all_required_captured(self):
        anatomy = get_anatomy("kerrison rongeur")
        panel = guided_capture_panel("kerrison rongeur", anatomy["required_images"])
        assert panel["all_required_captured"] is True
        assert panel["current_zone"] is None
