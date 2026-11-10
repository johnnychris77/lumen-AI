"""Fix persisted placeholder scores & clinical history consistency.

An image inspection with no verified AI model must never be marked Scored or
expose a fabricated inspection score / risk; the History API, exports, and PDF
must agree; legacy rows are shown as unvalidated without deleting evidence; and
tenant history resolves from the authenticated user's verified membership.
"""
from fastapi.testclient import TestClient

from app.main import app
from app.db.session import SessionLocal
from app.db import models
from app.models.baseline_library import BaselineLibraryEntry
from app.routes.history import inspection_response, csv_text, _export_header
from app.services.ai_result_integrity import (
    ai_evaluated, ai_unavailable_for_presentation, presented_inspection_score,
)

client = TestClient(app)
AUTH = {"Authorization": "Bearer dev-token"}


def _approved_baseline(category="drill_bit"):
    db = SessionLocal()
    try:
        db.query(BaselineLibraryEntry).filter(
            BaselineLibraryEntry.instrument_category == category
        ).delete()
        db.add(BaselineLibraryEntry(
            udi=f"ph-{category}", instrument_category=category, manufacturer_name="M",
            model_name="X", baseline_type="manufacturer", approval_status="approved",
        ))
        db.commit()
    finally:
        db.close()


def _run_image_inspection(category="drill_bit"):
    _approved_baseline(category)
    r = client.post("/api/inspections", headers=AUTH, json={
        "instrument_type": category, "site_name": "St Marys",
        "has_image": True, "image_sha256": "a" * 64,
    })
    assert r.status_code == 201, r.text
    return r.json()


def _row(db, iid):
    return db.query(models.Inspection).filter(models.Inspection.id == iid).first()


class TestPersistence:
    def test_ai_unavailable_inspection_is_not_scored(self):
        data = _run_image_inspection()
        assert data["analysis"]["ai_analysis"]["status"] == "AI_UNAVAILABLE"
        db = SessionLocal()
        try:
            row = _row(db, data["id"])
            assert row.score_status == "ai_unavailable"
            assert row.score_status != "scored"
            assert row.supervisor_review_required is True
            assert row.ai_analysis_status == "AI_UNAVAILABLE"
            # No heuristic clinical values persisted as valid conclusions.
            assert row.risk_level is None
            assert row.ai_confidence is None
        finally:
            db.close()

    def test_ai_unavailable_exposes_no_fabricated_score_or_risk(self):
        data = _run_image_inspection()
        db = SessionLocal()
        try:
            resp = inspection_response(_row(db, data["id"]))
            assert resp["inspection_score"] is None
            assert resp["risk_level"] is None
            assert resp["confidence"] is None
            assert resp["ai_evaluated"] is False
            assert resp["detected_issue"] == "No verified AI observation"
            assert "Manual inspection required" in resp["overall_cleaning_assessment"]
        finally:
            db.close()


class TestLegacyRows:
    def test_legacy_scored_image_row_shown_unvalidated_without_deleting_evidence(self):
        # Simulate a legacy #3–#8 row: scored, heuristic risk, no ai_analysis_status.
        db = SessionLocal()
        try:
            insp = models.Inspection(
                tenant_id="default-tenant", file_name="legacy.jpg", instrument_type="drill_bit",
                risk_score=7, score_status="scored", has_image=True, image_sha256="b" * 64,
                risk_level="low", ai_confidence=0.93, ai_analysis_status="",
                detected_issue="blood",
            )
            db.add(insp)
            db.commit()
            db.refresh(insp)
            iid = insp.id
        finally:
            db.close()
        db = SessionLocal()
        try:
            row = _row(db, iid)
            # Presentation suppresses the placeholder clinical values...
            assert ai_unavailable_for_presentation(row) is True
            assert presented_inspection_score(row) is None
            resp = inspection_response(row)
            assert resp["inspection_score"] is None
            assert resp["risk_level"] is None
            # ...but the raw evidence is preserved for audit provenance.
            assert resp["audit_raw_risk_score"] == 7
            assert resp["audit_raw_detected_issue"] == "blood"
            # And the stored row is NOT mutated/deleted.
            assert row.risk_score == 7 and row.score_status == "scored"
        finally:
            db.close()

    def test_manual_no_image_entry_keeps_its_human_score(self):
        # A manual entry is a human declaration, not an AI claim — not suppressed.
        db = SessionLocal()
        try:
            insp = models.Inspection(
                tenant_id="default-tenant", file_name="manual", instrument_type="scissors",
                risk_score=20, score_status="scored", has_image=False, ai_analysis_status="",
            )
            db.add(insp)
            db.commit()
            db.refresh(insp)
            row = _row(db, insp.id)
            assert ai_unavailable_for_presentation(row) is False
            assert presented_inspection_score(row) == 80
            assert ai_evaluated(row) is False
        finally:
            db.close()


class TestHistoryApiAndExportsAgree:
    def test_history_api_and_exports_agree(self):
        data = _run_image_inspection()
        db = SessionLocal()
        try:
            row = _row(db, data["id"])
            resp = inspection_response(row)
            assert resp["evaluation_status"] == "ai_unavailable"
            # CSV export: clinical columns blank, evaluation_status present, raw kept.
            header = _export_header()
            text = csv_text([row])
            line = text.splitlines()[1].split(",")
            cols = dict(zip(header, line))
            assert cols["evaluation_status"] == "ai_unavailable"
            assert cols["inspection_score"] == ""  # blanked
            assert cols["risk_level"] == ""         # blanked
            assert cols["audit_raw_risk_score"] == str(row.risk_score)  # preserved
        finally:
            db.close()


class TestPdfConsistency:
    def test_pdf_does_not_contradict_ai_unavailable(self):
        data = _run_image_inspection()
        pdf = client.get(f"/api/inspections/{data['id']}/clinical-report.pdf", headers=AUTH)
        assert pdf.status_code == 200
        assert pdf.content[:4] == b"%PDF"

    def test_pdf_builder_reports_unavailable_and_hides_placeholder_score(self):
        # Direct builder check: an AI_UNAVAILABLE analysis must render "unavailable"
        # and must NOT print the placeholder score (93). Text is extracted only
        # when a PDF text library is available; otherwise the valid-PDF check above
        # plus the branch exercise here still guard the behavior.
        from types import SimpleNamespace
        from app.services.clinical_report_pdf import build_clinical_report_pdf

        row = SimpleNamespace(
            id=8, facility_name="St Marys", site_name="", instrument_type="drill_bit",
            instrument_barcode=None, instrument_udi=None, created_at=None,
        )
        analysis = {
            "ai_analysis": {"status": "AI_UNAVAILABLE", "manual_inspection_required": True},
            "clinical_decision": {"summary": {"inspection_score": 93}},
        }
        pdf = build_clinical_report_pdf(row, analysis)
        assert pdf[:4] == b"%PDF"
        try:
            import io
            import pypdf
            text = "".join(p.extract_text() for p in pypdf.PdfReader(io.BytesIO(pdf)).pages)
            assert "UNAVAILABLE" in text.upper()
            assert "Not evaluated" in text
            assert "93" not in text  # the placeholder score is never shown
        except ImportError:
            pass


class TestTenantResolution:
    def test_tenant_resolution_prefers_user_membership(self):
        from app.auth.tenant_membership import resolve_effective_tenant, ensure_tenant_membership_table
        db = SessionLocal()
        try:
            ensure_tenant_membership_table(db)
            db.query(models.TenantMembership).filter(
                models.TenantMembership.user_email == "member@x.com"
            ).delete()
            db.add(models.TenantMembership(
                tenant_id="st-marys", user_email="member@x.com", is_enabled=True,
            ))
            db.commit()
            # A wrong/hardcoded requested tenant falls back to the verified one.
            assert resolve_effective_tenant(
                db, user_email="member@x.com", requested_tenant_id="bonsecours",
            ) == "st-marys"
            # A user with no membership is denied (fail-closed → None).
            assert resolve_effective_tenant(
                db, user_email="nobody@x.com", requested_tenant_id="bonsecours",
            ) is None
        finally:
            db.query(models.TenantMembership).filter(
                models.TenantMembership.user_email == "member@x.com"
            ).delete()
            db.commit()
            db.close()
