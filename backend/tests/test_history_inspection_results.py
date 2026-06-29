"""History must surface inspections run via /api/inspections with their results.

Regression: the Inspection History UI read a different table (EnterpriseFinding)
than the New Inspection form wrote to (inspections), so runs never appeared.
These tests pin the /api/history contract that the results panel depends on.
"""
from fastapi.testclient import TestClient

from app.main import app
from app.db.session import SessionLocal
from app.models.baseline_library import BaselineLibraryEntry

client = TestClient(app)

AUTH_ADMIN = {"Authorization": "Bearer dev-token"}
AUTH_VIEWER = {"Authorization": "Bearer viewer-token"}

SHA = "f00dcafe" + "0" * 56


def _add_baseline(instrument_type: str, baseline_type: str = "manufacturer") -> None:
    db = SessionLocal()
    try:
        db.add(BaselineLibraryEntry(
            udi=f"hist-udi-{instrument_type}-{baseline_type}",
            instrument_category=instrument_type,
            manufacturer_name="HistMfg",
            model_name="Model-H",
            baseline_type=baseline_type,
            approval_status="approved",
        ))
        db.commit()
    finally:
        db.close()


def _create_inspection(instrument_type: str) -> int:
    resp = client.post("/api/inspections", json={
        "instrument_type": instrument_type,
        "site_name": "History Hospital",
        "facility_name": "History Hospital",
        "has_image": True,
        "image_sha256": SHA,
        "file_name": "hist.jpg",
    }, headers=AUTH_VIEWER)
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


class TestHistoryShowsInspectionResults:
    def test_run_inspection_appears_in_history(self):
        itype = "needle_holder"
        _add_baseline(itype)
        inspection_id = _create_inspection(itype)

        resp = client.get("/api/history?limit=100", headers=AUTH_ADMIN)
        assert resp.status_code == 200, resp.text
        items = resp.json()["items"]
        ids = [it["id"] for it in items]
        assert inspection_id in ids

    def test_history_record_includes_result_fields(self):
        itype = "scissors"
        _add_baseline(itype)
        inspection_id = _create_inspection(itype)

        resp = client.get("/api/history?limit=100", headers=AUTH_ADMIN)
        items = resp.json()["items"]
        record = next(it for it in items if it["id"] == inspection_id)

        # Result fields the history UI renders
        for field in (
            "inspection_score", "score_status", "baseline_status",
            "baseline_source", "supervisor_review_required", "risk_score",
            "facility_name", "instrument_type",
        ):
            assert field in record, f"missing {field}"

        assert record["score_status"] == "scored"
        assert record["baseline_source"] == "manufacturer"
        assert record["inspection_score"] is not None
        assert 0 <= record["inspection_score"] <= 100

    def test_supervisor_review_record_has_no_score(self):
        # No baseline → supervisor review, inspection_score should be None
        itype = "clip_applier"
        db = SessionLocal()
        try:
            db.query(BaselineLibraryEntry).filter(
                BaselineLibraryEntry.instrument_category == itype,
            ).delete()
            db.commit()
        finally:
            db.close()

        inspection_id = _create_inspection(itype)
        resp = client.get("/api/history?limit=100", headers=AUTH_ADMIN)
        record = next(it for it in resp.json()["items"] if it["id"] == inspection_id)
        assert record["supervisor_review_required"] is True
        assert record["inspection_score"] is None

    def test_history_summary_counts_inspections(self):
        itype = "forceps"
        _add_baseline(itype)
        _create_inspection(itype)

        resp = client.get("/api/history/summary", headers=AUTH_ADMIN)
        assert resp.status_code == 200, resp.text
        summary = resp.json()
        assert summary["total_inspections"] >= 1
