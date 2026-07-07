"""LumenAI Inspect v2.0 — Anatomy-Aware Clinical Intelligence ("Project Anatomy").

Covers: the Anatomy Zone Engine (Instrument -> Anatomy -> Zone -> Risk ->
Typical Findings -> Recommended Inspection Method), the Zone Risk Matrix,
zone-specific finding models, Dynamic Inspection Guidance, Zone-Based AI
Context threaded into the real scoring engine, and Learning Dataset v2.
"""
from __future__ import annotations

import uuid

from fastapi.testclient import TestClient
from passlib.hash import bcrypt

from app.db.session import SessionLocal
from app.main import app
from app.models.admin_credential import AdminCredential
from app.models.baseline_library import BaselineLibraryEntry
from app.services.baseline_comparison_scoring_service import analyze_inspection
from app.services.guided_capture import guided_capture_panel
from app.services.instrument_anatomy import INSTRUMENT_ANATOMY, TYPICAL_FINDINGS_BY_CATEGORY
from app.services.learning_dataset_v2 import learning_dataset_v2
from app.services.zone_intelligence import (
    dynamic_inspection_guidance, typical_findings_for_legacy_zone, zone_engine,
    zone_risk_for_family, zone_risk_for_name, zone_risk_matrix,
)
from app.models.inspection_image_tag import InspectionImageTag
from app.models.supervisor_review import SupervisorReview

client = TestClient(app)
AUTH_ADMIN = {"Authorization": "Bearer dev-token"}
AUTH_VIEWER = {"Authorization": "Bearer viewer-token"}
SHA = "20b00000" + "0" * 56


def _baseline(itype: str) -> None:
    db = SessionLocal()
    try:
        db.query(BaselineLibraryEntry).filter(BaselineLibraryEntry.instrument_category == itype).delete()
        db.add(BaselineLibraryEntry(
            udi=f"v20-{itype}", instrument_category=itype, manufacturer_name="M",
            model_name="X", baseline_type="manufacturer", approval_status="approved",
        ))
        db.commit()
    finally:
        db.close()


class TestZoneSpecificFindingModels:
    def test_five_zone_categories_each_have_distinct_findings(self):
        assert set(TYPICAL_FINDINGS_BY_CATEGORY) == {
            "cutting_working_surface", "rotary_orthopedic", "lumen_scope", "mechanical", "handle_external",
        }
        # No two categories should share an identical (contamination, condition) pair —
        # that would mean the "zone-specific" model collapsed back to one generic list.
        seen = set()
        for cat, findings in TYPICAL_FINDINGS_BY_CATEGORY.items():
            key = (tuple(findings["contamination"]), tuple(findings["condition"]))
            assert key not in seen, f"{cat} duplicates another category's finding vocabulary"
            seen.add(key)

    def test_rigid_scope_oring_and_kerrison_jaw_reason_differently(self):
        oring = zone_engine("rigid scope", "o-ring area")
        jaw = zone_engine("kerrison rongeur", "jaw")
        assert oring["typical_condition_findings"] != jaw["typical_condition_findings"]
        assert "crack" in oring["typical_condition_findings"]
        assert "damaged seal" in oring["typical_condition_findings"]

    def test_drill_flute_expects_metal_shavings(self):
        flutes = zone_engine("drill bit", "flutes")
        assert "metal shavings" in flutes["typical_contamination_findings"]

    def test_every_zone_uses_a_real_category_vocabulary_not_the_flat_default(self):
        # Regression: before v2.0 every zone defaulted to the same generic
        # _CONTAM/_COND list regardless of zone_category.
        for defn in INSTRUMENT_ANATOMY.values():
            for zone in defn["zones"]:
                expected = TYPICAL_FINDINGS_BY_CATEGORY.get(zone["zone_category"])
                if expected is None:
                    continue
                assert zone["contamination_risks"] == expected["contamination"] or zone["contamination_risks"] != [
                    "blood", "bone", "tissue", "organic residue", "debris",
                ]


class TestAnatomyZoneEngine:
    def test_full_chain_for_a_known_zone(self):
        result = zone_engine("kerrison rongeur", "jaw")
        for key in (
            "instrument_type", "instrument_family", "anatomy_zone", "zone_category",
            "zone_risk_level", "retention_risk", "typical_contamination_findings",
            "typical_condition_findings", "cleaning_method", "required_lighting",
            "recommended_angle", "human_review_required",
        ):
            assert key in result
        assert result["instrument_family"] == "kerrison_rongeur"
        assert result["human_review_required"] is True

    def test_unknown_zone_for_instrument_returns_none(self):
        assert zone_engine("kerrison rongeur", "not-a-real-zone") is None

    def test_new_v1_10_family_zone_resolves_through_the_engine(self):
        result = zone_engine("towel clamp", "box lock")
        assert result is not None
        assert result["instrument_family"] == "towel_clamp"


class TestDynamicInspectionGuidance:
    def test_guidance_has_all_required_fields(self):
        g = dynamic_inspection_guidance("rigid scope", "o-ring area", coverage_status="captured")
        for key in (
            "current_zone", "risk_level", "expected_findings", "inspection_tips",
            "required_lighting", "recommended_angle", "coverage_status",
        ):
            assert key in g
        assert g["current_zone"] == "o-ring area"
        assert g["coverage_status"] == "captured"

    def test_default_coverage_status_when_not_supplied(self):
        g = dynamic_inspection_guidance("scissors", "blade")
        assert g["coverage_status"] == "not_assessed"

    def test_unknown_zone_returns_none(self):
        assert dynamic_inspection_guidance("scissors", "not-a-zone") is None


class TestZoneRiskMatrix:
    def test_matrix_has_four_tiers(self):
        matrix = zone_risk_matrix()
        assert set(matrix) == {"critical", "high", "medium", "low"}

    def test_known_critical_zones_present(self):
        matrix = zone_risk_matrix()
        assert "flutes" in matrix["critical"] or "flutes" in matrix["high"]
        assert "suction channel" in matrix["critical"]

    def test_api_endpoint_matches_service(self):
        res = client.get("/api/anatomy/zone-risk-matrix", headers=AUTH_VIEWER)
        assert res.status_code == 200
        assert set(res.json()) == {"critical", "high", "medium", "low"}


class TestZoneBasedAIContext:
    def test_predicted_findings_carry_instrument_family_and_expected_findings(self):
        _baseline("kerrison rongeur")
        db = SessionLocal()
        try:
            result = analyze_inspection(
                db, instrument_type="kerrison rongeur", tenant_id="default-tenant",
                has_image=True, image_sha256=SHA, declared_findings=["blood"],
            )
        finally:
            db.close()
        assert result["predicted_findings"], result
        for f in result["predicted_findings"]:
            assert f["instrument_family"] == "kerrison_rongeur"
            assert "expected_findings_for_zone" in f
            assert "contamination" in f["expected_findings_for_zone"]
            assert "condition" in f["expected_findings_for_zone"]

    def test_legacy_zone_bridges_to_a_real_category(self):
        findings = typical_findings_for_legacy_zone("o-ring area")
        assert findings == TYPICAL_FINDINGS_BY_CATEGORY["lumen_scope"]

    def test_unknown_legacy_zone_falls_back_honestly(self):
        findings = typical_findings_for_legacy_zone("unspecified region")
        assert findings == TYPICAL_FINDINGS_BY_CATEGORY["handle_external"]


class TestZoneRiskForName:
    def test_legacy_zone_name_resolves(self):
        assert zone_risk_for_name("hinge") == "high"

    def test_anatomy_zone_name_resolves(self):
        assert zone_risk_for_name("perforating tip") == "medium"

    def test_unknown_zone_name_returns_none(self):
        assert zone_risk_for_name("not-a-real-zone-anywhere") is None


class TestLearningDatasetV2:
    def test_dataset_reflects_a_real_supervisor_review(self):
        tenant = f"tenant-{uuid.uuid4().hex[:8]}"
        _baseline("scissors")
        r = client.post("/api/inspections", json={
            "instrument_type": "scissors", "site_name": "Mercy", "has_image": True,
            "image_sha256": SHA, "file_name": "x.jpg", "finding_categories": ["blood"],
        }, headers={**AUTH_ADMIN, "X-Tenant-Id": tenant})
        assert r.status_code == 201, r.text
        iid = r.json()["id"]

        review = client.post(
            f"/api/inspections/{iid}/supervisor-review",
            headers={**AUTH_ADMIN, "X-Tenant-Id": tenant},
            json={
                "agreement": "agree",
                "rationale": "Confirmed blood in the hinge.",
                "instrument_family_correct": True,
                "zone_correct": True,
                "finding_correct": True,
            },
        )
        assert review.status_code == 201, review.text

        db = SessionLocal()
        try:
            dataset = learning_dataset_v2(db, tenant)
        finally:
            db.close()
        assert dataset["count"] >= 1
        assert dataset["rows"][0]["inspection_id"] == iid

    def test_api_endpoint_requires_admin_or_manager(self):
        res = client.get("/api/anatomy/learning-dataset", headers=AUTH_VIEWER)
        assert res.status_code == 403

    def test_api_endpoint_returns_dataset_shape(self):
        res = client.get("/api/anatomy/learning-dataset", headers=AUTH_ADMIN)
        assert res.status_code == 200
        body = res.json()
        assert "rows" in body
        assert body["human_review_required"] is True


class TestGuidedCapturePanelZoneGuidance:
    """The capture UI's Guided Capture Panel is the natural place a
    technician sees Dynamic Inspection Guidance — v2.0 enriches its existing
    per-zone camera-technique guidance (angle/lighting/focus, unchanged)
    with the new zone-specific clinical risk_level/expected_findings,
    rather than duplicating the camera-guidance logic."""

    def test_panel_carries_risk_level_and_expected_findings_for_current_zone(self):
        panel = guided_capture_panel("kerrison rongeur", [])
        assert panel["current_zone"] == "jaw"
        assert panel["risk_level"] == "high"
        assert "blood" in panel["expected_findings"]
        assert "corrosion" in panel["expected_findings"]
        # Existing per-zone camera guidance is untouched by the v2.0 addition.
        assert panel["recommended_camera_angle"]

    def test_panel_has_no_risk_fields_once_all_zones_captured(self):
        from app.services.instrument_anatomy import get_anatomy

        anatomy = get_anatomy("kerrison rongeur")
        panel = guided_capture_panel("kerrison rongeur", anatomy["required_images"])
        assert panel["current_zone"] is None
        assert panel["risk_level"] is None
        assert panel["expected_findings"] == []

    def test_endpoint_response_includes_new_fields(self):
        res = client.get(
            "/api/guided-capture/kerrison%20rongeur",
            headers=AUTH_VIEWER,
        )
        assert res.status_code == 200
        body = res.json()
        assert "risk_level" in body
        assert "expected_findings" in body


class TestCodeReviewFixes:
    """Regression coverage for issues flagged by automated review on PR #83."""

    def test_flutes_gets_the_real_drill_bit_cleaning_entry_not_the_generic_fallback(self):
        # Regression: zone_engine("drill bit", "flutes") used to fall back to
        # the generic "unspecified region" cleaning entry because the
        # anatomy zone name ("flutes") didn't match the cleaning library's
        # key for the same real zone ("drill-bit flute").
        result = zone_engine("drill bit", "flutes")
        assert "flute" in result["cleaning_method"].lower()
        assert result["cleaning_method"] != "Standard manual cleaning per facility protocol."

    def test_zone_engine_endpoint_accepts_slash_bearing_zone_name(self):
        # Regression: the default `str` path converter stopped matching at
        # the "/" in zone names like "air/water nozzle", 404ing declared
        # zones that happen to contain a slash.
        res = client.get(
            "/api/anatomy/zone-engine/flexible endoscope/air/water nozzle",
            headers=AUTH_VIEWER,
        )
        assert res.status_code == 200
        assert res.json()["anatomy_zone"] == "air/water nozzle"

    def test_zone_risk_for_family_prefers_the_reviewed_familys_own_zone(self):
        # "blade" exists in both scissors (medium) and skin_graft_mesher-style
        # families with different risk levels — family-scoped lookup must
        # not silently pick whichever family happens to declare it first.
        assert zone_risk_for_family("scissors", "blade") == "medium"

    def test_learning_dataset_scopes_joins_to_the_requesting_tenant(self):
        # Regression: an Inspection/InspectionImageTag row belonging to a
        # different tenant than the SupervisorReview must never leak into
        # this tenant's exported dataset.
        tenant_a = f"tenant-{uuid.uuid4().hex[:8]}"
        tenant_b = f"tenant-{uuid.uuid4().hex[:8]}"
        _baseline("scissors")

        r = client.post("/api/inspections", json={
            "instrument_type": "scissors", "site_name": "Mercy", "has_image": True,
            "image_sha256": SHA, "file_name": "x.jpg", "finding_categories": [],
        }, headers={**AUTH_ADMIN, "X-Tenant-Id": tenant_a})
        assert r.status_code == 201
        iid = r.json()["id"]

        db = SessionLocal()
        try:
            # A SupervisorReview row claiming tenant_b but pointing at
            # tenant_a's inspection — the export for tenant_b must not
            # pull in tenant_a's real inspection/vendor data.
            db.add(SupervisorReview(
                inspection_id=iid, tenant_id=tenant_b, reviewer_name="x",
                reviewer_role="admin", agreement="agree", ai_recommendation="MONITOR",
                finding_type="blood", ai_zone="blade",
            ))
            db.commit()
            dataset = learning_dataset_v2(db, tenant_b)
        finally:
            db.close()
        assert dataset["count"] == 1
        assert dataset["rows"][0]["manufacturer"] == ""  # not tenant_a's real vendor_name

    def test_learning_dataset_matches_image_tag_to_the_reviewed_zone(self):
        tenant = f"tenant-{uuid.uuid4().hex[:8]}"
        _baseline("scissors")
        r = client.post("/api/inspections", json={
            "instrument_type": "scissors", "site_name": "Mercy", "has_image": True,
            "image_sha256": SHA, "file_name": "x.jpg", "finding_categories": [],
        }, headers={**AUTH_ADMIN, "X-Tenant-Id": tenant})
        iid = r.json()["id"]

        db = SessionLocal()
        try:
            db.add(InspectionImageTag(
                tenant_id=tenant, inspection_id=iid, instrument_family="scissors",
                anatomy_zone="handle", image_view="overview",
            ))
            db.add(InspectionImageTag(
                tenant_id=tenant, inspection_id=iid, instrument_family="scissors",
                anatomy_zone="blade", image_view="blade close-up",
            ))
            db.add(SupervisorReview(
                inspection_id=iid, tenant_id=tenant, reviewer_name="x",
                reviewer_role="admin", agreement="agree", ai_recommendation="MONITOR",
                finding_type="blood", ai_zone="blade",
            ))
            db.commit()
            dataset = learning_dataset_v2(db, tenant)
        finally:
            db.close()
        row = next(r for r in dataset["rows"] if r["inspection_id"] == iid)
        assert row["inspection_view"] == "blade close-up"


class TestSupervisorRoleCanReadAnatomyIntelligence:
    def test_supervisor_role_reads_zone_engine(self):
        username = f"supervisor-v20-{uuid.uuid4().hex[:8]}@lumen.ai"
        from app.models.user_role_assignment import UserRoleAssignment

        db = SessionLocal()
        try:
            db.add(AdminCredential(username=username, password_hash=bcrypt.hash("Password123"), role="admin"))
            db.add(UserRoleAssignment(username=username, role="supervisor", assigned_by="test"))
            db.commit()
        finally:
            db.close()

        login = client.post("/api/auth/login", json={"email": username, "password": "Password123"})
        assert login.status_code == 200, login.text
        token = login.json()["access_token"]

        res = client.get(
            "/api/anatomy/zone-engine/kerrison%20rongeur/jaw",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200
