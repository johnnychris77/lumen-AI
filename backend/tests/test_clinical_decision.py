"""Phase 13 — Explainable Clinical Decision Support payload + PDF report."""
from fastapi.testclient import TestClient

from app.main import app
from app.db.session import SessionLocal
from app.models.baseline_library import BaselineLibraryEntry
from app.services.baseline_comparison_scoring_service import (
    analyze_inspection,
    AI_ROADMAP,
)

client = TestClient(app)
AUTH_OPERATOR = {"Authorization": "Bearer operator-token"}
SHA = "a1b2c3d4" + "0" * 56


def _baseline(itype: str) -> None:
    db = SessionLocal()
    try:
        db.query(BaselineLibraryEntry).filter(
            BaselineLibraryEntry.instrument_category == itype
        ).delete()
        db.add(BaselineLibraryEntry(
            udi=f"cd-{itype}", instrument_category=itype, manufacturer_name="M",
            model_name="X", baseline_type="manufacturer", approval_status="approved",
        ))
        db.commit()
    finally:
        db.close()


def _analyze(itype, declared=None):
    _baseline(itype)
    db = SessionLocal()
    try:
        return analyze_inspection(
            db, instrument_type=itype, tenant_id="default-tenant",
            has_image=True, image_sha256=SHA, declared_findings=declared,
        )
    finally:
        db.close()


class TestClinicalDecisionShape:
    def test_all_phases_present(self):
        cd = _analyze("scissors")["clinical_decision"]
        for key in (
            "overall_result", "summary", "score_breakdown", "cleaning",
            "integrity", "clinical_reasoning", "recommendation", "evidence",
            "executive_summary", "audit", "roadmap",
        ):
            assert key in cd, f"missing {key}"

    def test_overall_result_is_one_of_four(self):
        cd = _analyze("scissors")["clinical_decision"]
        assert cd["overall_result"] in (
            "PASS", "MONITOR", "SUPERVISOR REVIEW", "REMOVE FROM SERVICE"
        )

    def test_summary_fields(self):
        s = _analyze("forceps")["clinical_decision"]["summary"]
        for k in ("inspection_score", "cleaning_assessment", "integrity_assessment",
                  "overall_risk", "confidence", "baseline_source"):
            assert k in s

    def test_cleaning_separates_from_integrity(self):
        cd = _analyze("forceps")["clinical_decision"]
        cleaning_types = {i["type"] for i in cd["cleaning"]["items"]}
        integrity_types = {i["type"] for i in cd["integrity"]["items"]}
        assert "blood" in cleaning_types
        assert "crack" in integrity_types
        assert not (cleaning_types & integrity_types)  # no overlap

    def test_cleaning_items_have_required_fields(self):
        items = _analyze("scissors")["clinical_decision"]["cleaning"]["items"]
        for it in items:
            for k in ("detected", "probability", "confidence", "severity", "spd_risk"):
                assert k in it

    def test_integrity_status_values(self):
        cd = _analyze("scissors")["clinical_decision"]
        assert cd["integrity"]["overall_status"] in (
            "Acceptable", "Monitor", "Repair Required", "Remove From Service"
        )

    def test_crack_forces_remove_from_service(self):
        cd = _analyze("forceps", declared=["crack"])["clinical_decision"]
        assert cd["overall_result"] == "REMOVE FROM SERVICE"
        assert cd["integrity"]["overall_status"] == "Remove From Service"

    def test_blood_forces_supervisor_or_remove(self):
        cd = _analyze("scissors", declared=["blood"])["clinical_decision"]
        assert cd["overall_result"] in ("SUPERVISOR REVIEW", "REMOVE FROM SERVICE")

    def test_reasoning_is_grounded(self):
        cd = _analyze("needle_holder")["clinical_decision"]
        assert cd["clinical_reasoning"]
        assert any("matched at" in ln for ln in cd["clinical_reasoning"])

    def test_score_breakdown_math(self):
        cd = _analyze("scissors", declared=["debris"])["clinical_decision"]
        sb = cd["score_breakdown"]
        assert sb["baseline_match_points"] is not None
        assert sb["final_score"] is not None
        # debris penalty should appear as a negative-or-zero item
        labels = {i["label"]: i["points"] for i in sb["items"]}
        assert "debris" in labels

    def test_evidence_no_fabricated_heatmap(self):
        cd = _analyze("scissors")["clinical_decision"]
        assert "coming in a future computer vision release" in cd["evidence"]["image_evidence_note"]

    def test_roadmap_present(self):
        cd = _analyze("scissors")["clinical_decision"]
        assert cd["roadmap"] == AI_ROADMAP
        assert "Visual heatmaps" in cd["roadmap"]

    def test_no_baseline_still_has_clinical_decision(self):
        db = SessionLocal()
        try:
            db.query(BaselineLibraryEntry).filter(
                BaselineLibraryEntry.instrument_category == "clip_applier"
            ).delete()
            db.commit()
            out = analyze_inspection(
                db, instrument_type="clip_applier", tenant_id="default-tenant",
                has_image=True, image_sha256=SHA,
            )
        finally:
            db.close()
        assert out["clinical_decision"]["overall_result"] == "SUPERVISOR REVIEW"


class TestClinicalReportPDF:
    def _create(self, itype):
        _baseline(itype)
        r = client.post("/api/inspections", json={
            "instrument_type": itype, "site_name": "Mercy",
            "has_image": True, "image_sha256": SHA, "file_name": "x.jpg",
        }, headers=AUTH_OPERATOR)
        assert r.status_code == 201, r.text
        return r.json()["id"]

    def test_pdf_report_generated(self):
        iid = self._create("scissors")
        r = client.get(f"/api/inspections/{iid}/clinical-report.pdf", headers=AUTH_OPERATOR)
        assert r.status_code == 200, r.text
        assert r.headers["content-type"] == "application/pdf"
        assert r.content[:4] == b"%PDF"
        assert len(r.content) > 1000

    def test_pdf_404_for_missing(self):
        r = client.get("/api/inspections/999999/clinical-report.pdf", headers=AUTH_OPERATOR)
        assert r.status_code == 404
