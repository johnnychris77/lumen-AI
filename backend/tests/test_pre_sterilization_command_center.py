"""Pre-Sterilization Command Center tests: readiness classification, the ten
dashboard modules, and role gating."""
from __future__ import annotations

import json

from fastapi.testclient import TestClient

from app.db.session import SessionLocal
from app.main import app
from app.models.baseline_library import BaselineLibraryEntry
from app.models.inspection import Inspection
from app.services.pre_sterilization_command_center_service import (
    PENDING_ANALYSIS,
    READY_FOR_PACKAGING,
    REMOVED_FROM_SERVICE,
    REQUIRES_RECLEANING,
    REQUIRES_REPAIR,
    REQUIRES_SUPERVISOR_REVIEW,
    classify_readiness,
)

client = TestClient(app)
AUTH_ADMIN = {"Authorization": "Bearer dev-token"}
AUTH_MGR = {"Authorization": "Bearer manager-token"}
AUTH_VIEWER = {"Authorization": "Bearer viewer-token"}
SHA = "c0ffee00" + "0" * 56


def _make_inspection(db, **overrides) -> Inspection:
    defaults = dict(
        tenant_id="default-tenant", file_name="x.jpg", instrument_type="scissors",
        has_image=True, image_sha256=SHA, score_status="scored", risk_score=10,
        detected_issue="none", stain_detected=False, supervisor_review_required=False,
        qa_review_status="pending", status="pending",
        inspected_zones_json="null",
    )
    defaults.update(overrides)
    insp = Inspection(**defaults)
    db.add(insp)
    db.commit()
    db.refresh(insp)
    return insp


class TestClassifyReadiness:
    def test_pass_action_is_ready_for_packaging(self):
        db = SessionLocal()
        try:
            insp = _make_inspection(db, recommended_action="Pass — no high-risk findings. Release for use.")
            assert classify_readiness(insp)["readiness_state"] == READY_FOR_PACKAGING
        finally:
            db.close()

    def test_monitor_action_is_ready_for_packaging(self):
        db = SessionLocal()
        try:
            insp = _make_inspection(db, recommended_action="Monitor — low-risk findings only. Continue routine processing.")
            assert classify_readiness(insp)["readiness_state"] == READY_FOR_PACKAGING
        finally:
            db.close()

    def test_reprocess_action_requires_recleaning(self):
        db = SessionLocal()
        try:
            insp = _make_inspection(db, recommended_action="Reprocess — blood. Return for complete cleaning.", detected_issue="blood")
            result = classify_readiness(insp)
            assert result["readiness_state"] == REQUIRES_RECLEANING
            assert result["is_critical_finding"] is True
        finally:
            db.close()

    def test_supervisor_review_action(self):
        db = SessionLocal()
        try:
            insp = _make_inspection(db, recommended_action="Supervisor review recommended before release — baseline mismatch.")
            assert classify_readiness(insp)["readiness_state"] == REQUIRES_SUPERVISOR_REVIEW
        finally:
            db.close()

    def test_remove_from_service_with_repairable_issue_is_repair_candidate(self):
        db = SessionLocal()
        try:
            insp = _make_inspection(
                db, recommended_action="Remove from service — crack. Supervisor review required.",
                detected_issue="crack",
            )
            result = classify_readiness(insp)
            assert result["readiness_state"] == REQUIRES_REPAIR
            assert result["repair_candidate"] is True
        finally:
            db.close()

    def test_remove_from_service_with_contamination_is_removed_not_repaired(self):
        db = SessionLocal()
        try:
            insp = _make_inspection(
                db, recommended_action="Remove from service — severe corrosion.",
                detected_issue="blood",
            )
            result = classify_readiness(insp)
            assert result["readiness_state"] == REMOVED_FROM_SERVICE
            assert result["repair_candidate"] is False
        finally:
            db.close()

    def test_unscored_inspection_is_pending_analysis(self):
        db = SessionLocal()
        try:
            insp = _make_inspection(db, score_status="pending", recommended_action=None)
            assert classify_readiness(insp)["readiness_state"] == PENDING_ANALYSIS
        finally:
            db.close()

    def test_readiness_score_is_inverse_of_risk_score(self):
        db = SessionLocal()
        try:
            insp = _make_inspection(db, risk_score=30, recommended_action="Pass — clean.")
            assert classify_readiness(insp)["readiness_score"] == 70
        finally:
            db.close()


class TestClinicalInspectionReadinessAPI:
    def test_returns_200_with_required_keys(self):
        res = client.get("/api/pre-sterilization-command-center/clinical-inspection-readiness", headers=AUTH_ADMIN)
        assert res.status_code == 200
        data = res.json()
        for key in ("total_inspections", "ready_for_packaging", "readiness_rate", "by_state", "human_review_required"):
            assert key in data

    def test_unauthenticated_rejected(self):
        res = client.get("/api/pre-sterilization-command-center/clinical-inspection-readiness")
        assert res.status_code in (401, 403)

    def test_viewer_can_read(self):
        res = client.get("/api/pre-sterilization-command-center/clinical-inspection-readiness", headers=AUTH_VIEWER)
        assert res.status_code == 200


class TestTrayReadiness:
    def test_weakest_link_blocks_the_tray(self):
        db = SessionLocal()
        try:
            _make_inspection(
                db, tray_id="tray-42", instrument_barcode="bc-1",
                recommended_action="Pass — clean.",
            )
            _make_inspection(
                db, tray_id="tray-42", instrument_barcode="bc-2",
                recommended_action="Reprocess — blood.", detected_issue="blood",
            )
        finally:
            db.close()

        res = client.get("/api/pre-sterilization-command-center/tray-readiness", headers=AUTH_MGR)
        assert res.status_code == 200
        trays = {t["tray_id"]: t for t in res.json()["trays"]}
        assert trays["tray-42"]["tray_readiness_state"] == REQUIRES_RECLEANING
        assert trays["tray-42"]["ready_for_packaging"] is False
        assert trays["tray-42"]["instrument_count"] == 2


class TestInstrumentReadiness:
    def test_latest_inspection_wins_for_same_instrument(self):
        db = SessionLocal()
        try:
            _make_inspection(
                db, instrument_barcode="bc-repeat", instrument_type="forceps",
                recommended_action="Reprocess — blood.", detected_issue="blood",
            )
            _make_inspection(
                db, instrument_barcode="bc-repeat", instrument_type="forceps",
                recommended_action="Pass — clean.",
            )
        finally:
            db.close()

        res = client.get("/api/pre-sterilization-command-center/instrument-readiness", headers=AUTH_MGR)
        assert res.status_code == 200
        matches = [i for i in res.json()["instruments"] if i["instrument_identity"] == "barcode:bc-repeat"]
        assert len(matches) == 1
        assert matches[0]["readiness_state"] == READY_FOR_PACKAGING


class TestFacilityReadiness:
    def test_facility_readiness_returns_rate_and_trend(self):
        db = SessionLocal()
        try:
            _make_inspection(db, facility_name="Mercy West", recommended_action="Pass — clean.")
        finally:
            db.close()

        res = client.get("/api/pre-sterilization-command-center/facility-readiness", headers=AUTH_MGR)
        assert res.status_code == 200
        facilities = {f["facility"]: f for f in res.json()["facilities"]}
        assert "Mercy West" in facilities
        assert facilities["Mercy West"]["readiness_rate"] is not None
        assert facilities["Mercy West"]["trend"] in ("improving", "declining", "stable", "insufficient_data")


class TestHighRiskFindingsQueue:
    def test_unconfirmed_critical_finding_appears_in_queue(self):
        db = SessionLocal()
        try:
            insp = _make_inspection(
                db, recommended_action="Reprocess — blood.", detected_issue="blood", risk_score=60,
            )
        finally:
            db.close()

        res = client.get("/api/pre-sterilization-command-center/high-risk-findings", headers=AUTH_MGR)
        assert res.status_code == 200
        ids = [i["inspection_id"] for i in res.json()["items"]]
        assert insp.id in ids


class TestSupervisorReviewQueue:
    def test_pending_supervisor_review_appears_in_queue(self):
        db = SessionLocal()
        try:
            insp = _make_inspection(
                db, recommended_action="Supervisor review recommended before release — baseline mismatch.",
                supervisor_review_required=True,
            )
        finally:
            db.close()

        res = client.get("/api/pre-sterilization-command-center/supervisor-review-queue", headers=AUTH_MGR)
        assert res.status_code == 200
        ids = [i["inspection_id"] for i in res.json()["items"]]
        assert insp.id in ids


class TestMissingZoneCoverage:
    def test_untagged_zones_appear_as_not_assessed(self):
        db = SessionLocal()
        try:
            insp = _make_inspection(
                db, instrument_type="kerrison rongeur", inspected_zones_json="null",
                recommended_action="Pass — clean.",
            )
        finally:
            db.close()

        res = client.get("/api/pre-sterilization-command-center/missing-zone-coverage", headers=AUTH_MGR)
        assert res.status_code == 200
        matches = [i for i in res.json()["items"] if i["inspection_id"] == insp.id]
        assert len(matches) == 1
        assert matches[0]["coverage_quality"] == "not_assessed"

    def test_fully_tagged_zones_do_not_appear(self):
        db = SessionLocal()
        try:
            from app.services.instrument_anatomy import get_anatomy
            anatomy = get_anatomy("kerrison rongeur")
            insp = _make_inspection(
                db, instrument_type="kerrison rongeur",
                inspected_zones_json=json.dumps(anatomy["required_images"]),
                recommended_action="Pass — clean.",
            )
        finally:
            db.close()

        res = client.get("/api/pre-sterilization-command-center/missing-zone-coverage", headers=AUTH_MGR)
        ids = [i["inspection_id"] for i in res.json()["items"]]
        assert insp.id not in ids


class TestBaselineCoverage:
    def test_baseline_coverage_rate_and_gaps(self):
        db = SessionLocal()
        try:
            db.query(BaselineLibraryEntry).filter(
                BaselineLibraryEntry.instrument_category == "cmd-center-widget"
            ).delete()
            db.commit()
            _make_inspection(
                db, instrument_type="cmd-center-widget", baseline_status="no_approved_baseline",
                recommended_action="Supervisor review recommended before release — no baseline.",
            )
        finally:
            db.close()

        res = client.get("/api/pre-sterilization-command-center/baseline-coverage", headers=AUTH_MGR)
        assert res.status_code == 200
        data = res.json()
        assert "baseline_coverage_rate" in data
        gaps = {g["instrument_type"]: g for g in data["instrument_types_missing_baseline"]}
        assert "cmd-center-widget" in gaps


class TestRepairRemoveQueue:
    def test_repair_and_removed_are_split(self):
        db = SessionLocal()
        try:
            repair_insp = _make_inspection(
                db, recommended_action="Remove from service — crack.", detected_issue="crack",
            )
            removed_insp = _make_inspection(
                db, recommended_action="Remove from service — severe corrosion.", detected_issue="blood",
            )
            repair_id, removed_id = repair_insp.id, removed_insp.id
        finally:
            db.close()

        res = client.get("/api/pre-sterilization-command-center/repair-remove-queue", headers=AUTH_MGR)
        assert res.status_code == 200
        data = res.json()
        repair_ids = [c["inspection_id"] for c in data["repair_candidates"]["cases"]]
        removed_ids = [c["inspection_id"] for c in data["removed_from_service"]["cases"]]
        assert repair_id in repair_ids
        assert removed_id in removed_ids


class TestExecutiveRiskDashboard:
    def test_returns_required_sections(self):
        res = client.get("/api/pre-sterilization-command-center/executive-risk-dashboard", headers=AUTH_ADMIN)
        assert res.status_code == 200
        data = res.json()
        for key in (
            "readiness_summary", "high_risk_findings_count", "supervisor_review_backlog",
            "repair_candidates_count", "removed_from_service_count", "baseline_coverage_rate",
            "facility_rollup", "anatomy_zone_failure_trend", "human_review_required",
        ):
            assert key in data


class TestFullDashboard:
    def test_dashboard_includes_all_ten_modules(self):
        res = client.get("/api/pre-sterilization-command-center/dashboard", headers=AUTH_ADMIN)
        assert res.status_code == 200
        data = res.json()
        for key in (
            "clinical_inspection_readiness", "tray_readiness", "instrument_readiness",
            "facility_readiness", "high_risk_findings_queue", "supervisor_review_queue",
            "missing_zone_coverage_queue", "baseline_coverage", "repair_remove_queue",
            "executive_risk_dashboard",
        ):
            assert key in data

    def test_unauthenticated_rejected(self):
        res = client.get("/api/pre-sterilization-command-center/dashboard")
        assert res.status_code in (401, 403)
