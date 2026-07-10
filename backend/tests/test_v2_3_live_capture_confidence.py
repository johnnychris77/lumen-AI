"""LumenAI Inspect v2.3 — Live Capture Confidence & Warnings.

Follow-up to v2.2 (Vision Intelligence): (1) persists each analysis-time
finding's own confidence on `InspectionFinding` so Evidence Fusion's
`average_confidence` reflects real data instead of always being null, and
(2) surfaces missing-anatomy / duplicate-image warnings during capture
(before submission) instead of only after the fact on the Vision Session
review page.
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.db.session import SessionLocal
from app.main import app
from app.models.baseline_library import BaselineLibraryEntry
from app.models.inspection_finding import InspectionFinding

client = TestClient(app)
AUTH_ADMIN = {"Authorization": "Bearer dev-token"}
SHA_A = "a1" * 32
SHA_B = "b2" * 32


def _baseline(itype: str) -> None:
    db = SessionLocal()
    try:
        db.query(BaselineLibraryEntry).filter(BaselineLibraryEntry.instrument_category == itype).delete()
        db.add(BaselineLibraryEntry(
            udi=f"v23-{itype}", instrument_category=itype, manufacturer_name="M",
            model_name="X", baseline_type="manufacturer", approval_status="approved",
        ))
        db.commit()
    finally:
        db.close()


def _create_session(instrument_type: str, tags: list[dict] | None = None, finding_categories=None) -> dict:
    _baseline(instrument_type)
    r = client.post("/api/inspections", headers=AUTH_ADMIN, json={
        "instrument_type": instrument_type, "site_name": "Main OR", "has_image": True,
        "image_sha256": SHA_A, "file_name": "x.jpg",
        "finding_categories": finding_categories or [],
        "image_view_tags": tags or [],
    })
    assert r.status_code == 201, r.text
    return r.json()


class TestPersistedFindingConfidence:
    def test_declared_finding_persists_a_real_confidence(self):
        insp = _create_session("scissors", finding_categories=["blood"])
        db = SessionLocal()
        try:
            rows = db.query(InspectionFinding).filter(
                InspectionFinding.inspection_id == insp["id"]
            ).all()
            assert rows, "expected at least one persisted finding"
            assert all(r.confidence is not None for r in rows)
            assert all(0.0 <= r.confidence <= 1.0 for r in rows)
        finally:
            db.close()

    def test_persisted_confidence_matches_the_analysis_response(self):
        insp = _create_session("scissors", finding_categories=["blood"])
        analysis_findings = {
            f["type"]: f["confidence"] for f in insp["analysis"]["predicted_findings"]
        }
        db = SessionLocal()
        try:
            rows = db.query(InspectionFinding).filter(
                InspectionFinding.inspection_id == insp["id"]
            ).all()
            for row in rows:
                assert row.confidence == analysis_findings[row.finding_type]
        finally:
            db.close()

    def test_vision_session_reconstruction_reflects_persisted_confidence(self):
        insp = _create_session("scissors", finding_categories=["blood"], tags=[
            {"instrument_family": "scissors", "anatomy_zone": "blade", "image_view": "blade", "image_sha256": SHA_A},
        ])
        r = client.get(f"/api/inspections/{insp['id']}/vision-session", headers=AUTH_ADMIN)
        assert r.status_code == 200
        fusion = r.json()["evidence_fusion"]
        assert fusion["contributing_factors"]["average_confidence"] is not None

    def test_no_baseline_means_no_persisted_findings_and_null_confidence(self):
        # No BaselineLibraryEntry registered for this instrument type, so
        # analyze_inspection() returns analysis_status="supervisor_review_required"
        # with predicted_findings=[] — nothing is persisted, and the average
        # is omitted rather than fabricated.
        r = client.post("/api/inspections", headers=AUTH_ADMIN, json={
            "instrument_type": "unbaselined_instrument_v23", "site_name": "Main OR",
            "has_image": True, "image_sha256": SHA_B, "file_name": "x.jpg",
        })
        assert r.status_code == 201, r.text
        insp = r.json()
        db = SessionLocal()
        try:
            rows = db.query(InspectionFinding).filter(
                InspectionFinding.inspection_id == insp["id"]
            ).all()
            assert rows == []
        finally:
            db.close()

        vr = client.get(f"/api/inspections/{insp['id']}/vision-session", headers=AUTH_ADMIN)
        assert vr.status_code == 200
        fusion = vr.json()["evidence_fusion"]
        assert fusion["contributing_factors"]["average_confidence"] is None


class TestLiveCaptureWarnings:
    """Objective — v2.3: the same missing-anatomy / duplicate-detection
    checks the Vision Session review page shows after the fact, available
    live during capture on tags that have not been submitted yet."""

    def test_requires_authentication(self):
        r = client.post("/api/inspections/preview-warnings", json={"instrument_type": "scissors", "tags": []})
        assert r.status_code in (401, 403)

    def test_no_tags_yet_reports_all_zones_missing_and_no_duplicates(self):
        r = client.post(
            "/api/inspections/preview-warnings", headers=AUTH_ADMIN,
            json={"instrument_type": "scissors", "tags": []},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["missing_anatomy"]["prompts"]
        assert body["duplicate_detection"]["has_warnings"] is False

    def test_duplicate_image_hash_flagged_before_submission(self):
        r = client.post(
            "/api/inspections/preview-warnings", headers=AUTH_ADMIN,
            json={
                "instrument_type": "scissors",
                "tags": [
                    {"anatomy_zone": "blade", "instrument_family": "scissors", "image_sha256": SHA_A},
                    {"anatomy_zone": "box lock", "instrument_family": "scissors", "image_sha256": SHA_A},
                ],
            },
        )
        assert r.status_code == 200
        findings = r.json()["duplicate_detection"]["findings"]
        assert any(f["type"] == "duplicate_image" for f in findings)

    def test_wrong_anatomy_zone_flagged_before_submission(self):
        r = client.post(
            "/api/inspections/preview-warnings", headers=AUTH_ADMIN,
            json={
                "instrument_type": "scissors",
                "tags": [
                    {"anatomy_zone": "not_a_real_zone", "instrument_family": "scissors", "image_sha256": SHA_A},
                ],
            },
        )
        assert r.status_code == 200
        findings = r.json()["duplicate_detection"]["findings"]
        assert any(f["type"] == "wrong_anatomy" for f in findings)

    def test_full_coverage_clears_the_missing_anatomy_prompts(self):
        from app.services.instrument_anatomy import get_anatomy

        anatomy = get_anatomy("scissors")
        tags = [
            {"anatomy_zone": z, "instrument_family": "scissors", "image_sha256": f"{i}" * 64}
            for i, z in enumerate(anatomy["required_images"])
        ]
        r = client.post(
            "/api/inspections/preview-warnings", headers=AUTH_ADMIN,
            json={"instrument_type": "scissors", "tags": tags},
        )
        assert r.status_code == 200
        assert r.json()["missing_anatomy"]["prompts"] == []
