"""Sprint 2 — Core Inspection Workflow Closure.

Covers the behaviors added/fixed in this pass:
  - honest, scope-limited model result contract (supported vs. unsupported
    categories — never a fabricated probability for an unsupported category)
  - analysis exceptions degrade safely instead of crashing the request
  - disposition-action audit events are actually persisted
  - image upload audit events are actually persisted, and empty files are
    rejected
  - a finalized (terminal-state) inspection cannot receive further
    disposition actions
  - cross-tenant access is denied for both the inspection resource and the
    supervisor disposition workflow
  - the original AI output is never overwritten by a supervisor correction
"""
import io

from fastapi.testclient import TestClient

from app.db import models
from app.db.session import SessionLocal
from app.main import app
from app.models.audit_log import AuditLog
from app.models.baseline_library import BaselineLibraryEntry

client = TestClient(app)

AUTH_ADMIN = {"Authorization": "Bearer dev-token"}          # admin
AUTH_MGR = {"Authorization": "Bearer manager-token"}        # spd_manager
AUTH_OPERATOR = {"Authorization": "Bearer operator-token"}  # operator
AUTH_VIEWER = {"Authorization": "Bearer viewer-token"}      # viewer

SHA = "ab12cd34" + "0" * 56


def _baseline(itype: str) -> None:
    db = SessionLocal()
    try:
        db.query(BaselineLibraryEntry).filter(BaselineLibraryEntry.instrument_category == itype).delete()
        db.add(BaselineLibraryEntry(
            udi=f"cw-{itype}", instrument_category=itype, manufacturer_name="M",
            model_name="X", baseline_type="manufacturer", approval_status="approved",
        ))
        db.commit()
    finally:
        db.close()


def _clear_baseline(itype: str) -> None:
    db = SessionLocal()
    try:
        db.query(BaselineLibraryEntry).filter(BaselineLibraryEntry.instrument_category == itype).delete()
        db.commit()
    finally:
        db.close()


def _payload(itype="forceps"):
    return {
        "instrument_type": itype, "site_name": "H", "has_image": True,
        "image_sha256": SHA, "file_name": "i.jpg",
    }


def _png_upload():
    return {"images": ("i.png", io.BytesIO(b"\x89PNG\r\n\x1a\n" + b"0" * 64), "image/png")}


class TestHonestModelResultContract:
    def test_supported_categories_scored_unsupported_marked_not_evaluated(self):
        _baseline("cw_forceps")
        r = client.post("/api/inspections", json=_payload("cw_forceps"), headers=AUTH_OPERATOR)
        assert r.status_code == 201, r.text
        mr = r.json()["analysis"]["model_result"]
        assert mr["supported_categories"] == ["debris", "corrosion"]
        categories_found = {f["category"] for f in mr["findings"]}
        assert categories_found <= {"debris", "corrosion"}
        assert "blood" in mr["unsupported_categories"]
        assert "bone" in mr["unsupported_categories"]
        assert "rust" in mr["unsupported_categories"]
        assert "debris" not in mr["unsupported_categories"]
        assert "corrosion" not in mr["unsupported_categories"]
        assert mr["human_review_required"] is True
        assert mr["model_status"] == "experimental"

    def test_no_baseline_model_result_has_no_fabricated_findings(self):
        _clear_baseline("cw_nobaseline")
        r = client.post("/api/inspections", json=_payload("cw_nobaseline"), headers=AUTH_OPERATOR)
        assert r.status_code == 201, r.text
        mr = r.json()["analysis"]["model_result"]
        assert mr["findings"] == []
        assert mr["baseline_status"] == "no_approved_baseline"
        assert any("baseline" in lim.lower() for lim in mr["limitations"])


class TestAnalysisFailureSafety:
    def test_analysis_exception_degrades_safely_instead_of_crashing(self, monkeypatch):
        import app.routes.inspections as inspections_mod

        def boom(*a, **kw):
            raise RuntimeError("simulated model crash")

        monkeypatch.setattr(inspections_mod, "analyze_inspection", boom)
        _baseline("cw_failtype")
        r = client.post("/api/inspections", json=_payload("cw_failtype"), headers=AUTH_OPERATOR)
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["analysis"]["analysis_status"] == "analysis_unavailable"
        assert body["supervisor_review_required"] is True
        assert body["baseline_status"] == "analysis_unavailable"
        assert body["analysis"]["model_result"]["findings"] == []


class TestImageUploadIntegrity:
    def test_empty_file_rejected(self):
        files = {"images": ("empty.png", io.BytesIO(b""), "image/png")}
        r = client.post("/api/inspections/upload-images", files=files, headers=AUTH_OPERATOR)
        assert r.status_code == 422

    def test_upload_audit_event_persisted(self):
        db = SessionLocal()
        try:
            before = db.query(AuditLog).filter(AuditLog.action_type == "inspection_image_uploaded").count()
        finally:
            db.close()

        r = client.post("/api/inspections/upload-images", files=_png_upload(), headers=AUTH_OPERATOR)
        assert r.status_code == 200, r.text

        db = SessionLocal()
        try:
            after = db.query(AuditLog).filter(AuditLog.action_type == "inspection_image_uploaded").count()
        finally:
            db.close()
        assert after == before + 1


class TestDispositionActionAuditAndFinalization:
    def _pending_inspection(self, itype: str) -> int:
        _clear_baseline(itype)
        ins = client.post("/api/inspections", json=_payload(itype), headers=AUTH_OPERATOR)
        assert ins.status_code == 201, ins.text
        return ins.json()["id"]

    def test_disposition_action_audit_event_persisted(self):
        iid = self._pending_inspection("cw_audit1")
        db = SessionLocal()
        try:
            before = db.query(AuditLog).filter(AuditLog.action_type == "disposition_action_reclean").count()
        finally:
            db.close()

        r = client.post(
            f"/api/inspections/{iid}/disposition-action",
            json={"action": "reclean", "reason": "visible residue on hinge"},
            headers=AUTH_MGR,
        )
        assert r.status_code == 201, r.text

        db = SessionLocal()
        try:
            after = db.query(AuditLog).filter(AuditLog.action_type == "disposition_action_reclean").count()
        finally:
            db.close()
        assert after == before + 1

    def test_cannot_act_on_already_finalized_inspection(self):
        iid = self._pending_inspection("cw_finalize1")
        r1 = client.post(
            f"/api/inspections/{iid}/disposition-action",
            json={"action": "approve"},
            headers=AUTH_MGR,
        )
        assert r1.status_code == 201, r1.text

        r2 = client.post(
            f"/api/inspections/{iid}/disposition-action",
            json={"action": "reclean", "reason": "trying again after finalized"},
            headers=AUTH_MGR,
        )
        assert r2.status_code == 409, r2.text

    def test_original_ai_output_not_overwritten_by_disposition_action(self):
        _baseline("cw_preserve")
        ins = client.post("/api/inspections", json=_payload("cw_preserve"), headers=AUTH_OPERATOR)
        assert ins.status_code == 201, ins.text
        iid = ins.json()["id"]
        original_analysis = ins.json()["analysis"]

        r = client.post(
            f"/api/inspections/{iid}/disposition-action",
            json={"action": "modify", "modified_disposition": "reprocess", "reason": "corrected on review"},
            headers=AUTH_MGR,
        )
        assert r.status_code == 201, r.text

        db = SessionLocal()
        try:
            row = db.query(models.Inspection).filter(models.Inspection.id == iid).first()
            # The original per-inspection AI verdict snapshot must be unchanged.
            assert row.risk_level == original_analysis.get("risk_level")
            assert row.recommended_action == original_analysis.get("recommended_action")
        finally:
            db.close()


class TestCrossTenantAccessDenied:
    def test_get_inspection_denied_across_tenants_for_non_admin(self):
        create = client.post(
            "/api/inspections",
            json=_payload("cw_tenant_iso"),
            headers={**AUTH_MGR, "X-Tenant-Id": "tenant-alpha"},
        )
        assert create.status_code == 201, create.text
        iid = create.json()["id"]

        r = client.get(
            f"/api/inspections/{iid}",
            headers={**AUTH_MGR, "X-Tenant-Id": "tenant-beta"},
        )
        assert r.status_code == 404

    def test_disposition_action_denied_across_tenants(self):
        create = client.post(
            "/api/inspections",
            json=_payload("cw_tenant_iso2"),
            headers={**AUTH_MGR, "X-Tenant-Id": "tenant-alpha"},
        )
        assert create.status_code == 201, create.text
        iid = create.json()["id"]

        r = client.post(
            f"/api/inspections/{iid}/disposition-action",
            json={"action": "approve"},
            headers={**AUTH_MGR, "X-Tenant-Id": "tenant-beta"},
        )
        assert r.status_code == 404


class TestViewerCannotTransitionState:
    def test_viewer_cannot_submit_disposition_action(self):
        db = SessionLocal()
        try:
            db.query(BaselineLibraryEntry).filter(BaselineLibraryEntry.instrument_category == "cw_viewer_deny").delete()
            db.commit()
        finally:
            db.close()
        ins = client.post("/api/inspections", json=_payload("cw_viewer_deny"), headers=AUTH_OPERATOR)
        iid = ins.json()["id"]
        r = client.post(
            f"/api/inspections/{iid}/disposition-action",
            json={"action": "approve"},
            headers=AUTH_VIEWER,
        )
        assert r.status_code == 403
