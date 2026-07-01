"""Tests for the baseline_comparison_scoring_service and AI analysis output.

Covers:
  - manufacturer baseline used first
  - vendor baseline fallback
  - hospital baseline fallback
  - missing baseline requires supervisor review (no score)
  - rust / discoloration KPIs returned
  - blood / bone / tissue / debris KPIs returned
  - inspection_score + risk_level returned
  - explainable response shape
"""
from fastapi.testclient import TestClient

from app.main import app
from app.db.session import SessionLocal
from app.models.baseline_library import BaselineLibraryEntry
from app.services.baseline_comparison_scoring_service import (
    analyze_inspection,
    resolve_baseline,
)

client = TestClient(app)

AUTH_TECH = {"Authorization": "Bearer operator-token"}

# Deterministic 64-char hex sha256 used to seed scoring.
SHA = "a1b2c3d4" + "0" * 56


def _add_baseline(instrument_type: str, baseline_type: str, status: str = "approved") -> int:
    db = SessionLocal()
    try:
        entry = BaselineLibraryEntry(
            udi=f"udi-{instrument_type}-{baseline_type}",
            instrument_category=instrument_type,
            manufacturer_name="TestMfg",
            model_name="Model-X",
            baseline_type=baseline_type,
            approval_status=status,
        )
        db.add(entry)
        db.commit()
        return entry.id
    finally:
        db.close()


def _clear_baselines(instrument_type: str) -> None:
    db = SessionLocal()
    try:
        db.query(BaselineLibraryEntry).filter(
            BaselineLibraryEntry.instrument_category == instrument_type,
        ).delete()
        db.commit()
    finally:
        db.close()


def _add_uploaded_baseline(instrument_type: str, baseline_source: str = "manufacturer",
                           approval_status: str = "approved") -> int:
    """Simulate a baseline uploaded + reviewed through the UI (vendor-subscription table)."""
    from app.models.enterprise_quality import EnterpriseVendorBaselineSubscription
    db = SessionLocal()
    try:
        row = EnterpriseVendorBaselineSubscription(
            vendor_name="UI Upload",
            instrument_name=instrument_type.replace("_", " "),
            instrument_category=instrument_type,
            baseline_source=baseline_source,
            approval_status=approval_status,
        )
        db.add(row)
        db.commit()
        return row.id
    finally:
        db.close()


def _clear_uploaded(instrument_type: str) -> None:
    from app.models.enterprise_quality import EnterpriseVendorBaselineSubscription
    db = SessionLocal()
    try:
        db.query(EnterpriseVendorBaselineSubscription).filter(
            EnterpriseVendorBaselineSubscription.instrument_category == instrument_type,
        ).delete()
        db.commit()
    finally:
        db.close()


# ── Baseline resolution priority ────────────────────────────────────────────

class TestBaselineResolution:
    def test_manufacturer_used_first(self):
        itype = "needle_holder"
        _clear_baselines(itype)
        _add_baseline(itype, "manufacturer")
        _add_baseline(itype, "vendor")
        db = SessionLocal()
        try:
            res = resolve_baseline(db, itype, "default-tenant")
        finally:
            db.close()
        assert res["baseline_found"] is True
        assert res["baseline_source"] == "manufacturer"

    def test_vendor_fallback_when_no_manufacturer(self):
        itype = "trocar"
        _clear_baselines(itype)
        _add_baseline(itype, "vendor")
        db = SessionLocal()
        try:
            res = resolve_baseline(db, itype, "default-tenant")
        finally:
            db.close()
        assert res["baseline_source"] == "vendor"

    def test_hospital_fallback_when_no_manufacturer_or_vendor(self):
        itype = "stapler"
        _clear_baselines(itype)
        _add_baseline(itype, "hospital")
        db = SessionLocal()
        try:
            res = resolve_baseline(db, itype, "default-tenant")
        finally:
            db.close()
        assert res["baseline_source"] == "hospital"

    def test_missing_baseline_not_found(self):
        itype = "clip_applier"
        _clear_baselines(itype)
        _clear_uploaded(itype)
        db = SessionLocal()
        try:
            res = resolve_baseline(db, itype, "default-tenant")
        finally:
            db.close()
        assert res["baseline_found"] is False
        assert res["baseline_source"] is None

    def test_uploaded_approved_baseline_is_used(self):
        # A baseline uploaded + approved through the UI (vendor-subscription
        # table) must be visible to the scoring engine.
        itype = "needle_holder"
        _clear_baselines(itype)
        _clear_uploaded(itype)
        _add_uploaded_baseline(itype, baseline_source="manufacturer", approval_status="approved")
        db = SessionLocal()
        try:
            res = resolve_baseline(db, itype, "default-tenant")
        finally:
            db.close()
        assert res["baseline_found"] is True
        assert res["baseline_source"] == "manufacturer"

    def test_uploaded_unapproved_baseline_not_used(self):
        itype = "stapler"
        _clear_baselines(itype)
        _clear_uploaded(itype)
        _add_uploaded_baseline(itype, baseline_source="manufacturer", approval_status="pending_hospital_review")
        db = SessionLocal()
        try:
            res = resolve_baseline(db, itype, "default-tenant")
        finally:
            db.close()
        assert res["baseline_found"] is False


# ── Analysis output ─────────────────────────────────────────────────────────

class TestAnalysisOutput:
    def test_missing_baseline_requires_supervisor_review(self):
        itype = "clip_applier"
        _clear_baselines(itype)
        db = SessionLocal()
        try:
            out = analyze_inspection(
                db, instrument_type=itype, tenant_id="default-tenant",
                has_image=True, image_sha256=SHA,
            )
        finally:
            db.close()
        assert out["analysis_status"] == "supervisor_review_required"
        assert out["inspection_score"] is None
        assert out["risk_level"] is None
        assert "Supervisor review required" in out["recommendation"]
        assert out["human_review_required"] is True

    def test_completed_analysis_returns_score_and_risk(self):
        itype = "scissors"
        _clear_baselines(itype)
        _add_baseline(itype, "manufacturer")
        db = SessionLocal()
        try:
            out = analyze_inspection(
                db, instrument_type=itype, tenant_id="default-tenant",
                has_image=True, image_sha256=SHA,
            )
        finally:
            db.close()
        assert out["analysis_status"] == "completed"
        assert out["baseline_source"] == "manufacturer"
        # Manufacturer is the authoritative primary comparison
        assert out["baseline_role"] == "primary"
        assert out["baseline_comparison_label"] == "Manufacturer baseline"
        assert isinstance(out["inspection_score"], int)
        assert 0 <= out["inspection_score"] <= 100
        assert out["risk_level"] in ("low", "medium", "high", "critical")
        assert 0.0 <= out["baseline_match_score"] <= 1.0
        assert 0.0 <= out["baseline_deviation_score"] <= 1.0

    def test_kpi_summary_includes_all_categories(self):
        itype = "scissors"
        _clear_baselines(itype)
        _add_baseline(itype, "manufacturer")
        db = SessionLocal()
        try:
            out = analyze_inspection(
                db, instrument_type=itype, tenant_id="default-tenant",
                has_image=True, image_sha256=SHA,
            )
        finally:
            db.close()
        for kpi in ("blood", "bone", "tissue", "debris", "rust", "discoloration", "corrosion", "crack"):
            assert kpi in out["kpi_summary"]

    def test_rust_kpi_returned_when_declared(self):
        # "corrosion" declared maps to corrosion; rust is a separate condition KPI
        # that is always reported. Verify rust is present in predicted_findings.
        itype = "forceps"
        _clear_baselines(itype)
        _add_baseline(itype, "manufacturer")
        db = SessionLocal()
        try:
            out = analyze_inspection(
                db, instrument_type=itype, tenant_id="default-tenant",
                has_image=True, image_sha256=SHA,
            )
        finally:
            db.close()
        types = {f["type"] for f in out["predicted_findings"]}
        assert "rust" in types
        assert "discoloration" in types

    def test_declared_blood_raises_blood_kpi(self):
        itype = "retractor"
        _clear_baselines(itype)
        _add_baseline(itype, "manufacturer")
        db = SessionLocal()
        try:
            out = analyze_inspection(
                db, instrument_type=itype, tenant_id="default-tenant",
                has_image=True, image_sha256=SHA,
                declared_findings=["blood", "bone", "tissue", "debris"],
            )
        finally:
            db.close()
        assert out["kpi_summary"]["blood"] is True
        assert out["kpi_summary"]["bone"] is True
        assert out["kpi_summary"]["tissue"] is True
        assert out["kpi_summary"]["debris"] is True

    def test_identification_detection_and_mismatch(self):
        # _add_baseline stores udi "udi-{itype}-manufacturer"; the decoded values
        # here do not match it → real comparison must report a mismatch.
        itype = "scissors"
        _clear_baselines(itype)
        _add_baseline(itype, "manufacturer")
        db = SessionLocal()
        try:
            out = analyze_inspection(
                db, instrument_type=itype, tenant_id="default-tenant",
                has_image=True, image_sha256=SHA,
                instrument_barcode="BC123", instrument_udi="UDI456", keydot_id="KD789",
            )
        finally:
            db.close()
        ident = out["identification"]
        assert ident["barcode_detected"] is True
        assert ident["qr_udi_detected"] is True
        assert ident["keydot_detected"] is True
        # Decoded values differ from the baseline UDI → mismatch, not a fake match.
        assert ident["barcode_match"] is False
        assert ident["identification_status"] == "mismatch"
        assert out["risk_level"] in ("high", "critical")

    def test_identification_match_against_baseline_udi(self):
        itype = "scissors"
        _clear_baselines(itype)
        _add_baseline(itype, "manufacturer")  # udi = "udi-scissors-manufacturer"
        db = SessionLocal()
        try:
            out = analyze_inspection(
                db, instrument_type=itype, tenant_id="default-tenant",
                has_image=True, image_sha256=SHA,
                instrument_barcode="udi-scissors-manufacturer",
            )
        finally:
            db.close()
        ident = out["identification"]
        assert ident["barcode_match"] is True
        assert ident["identification_status"] == "verified"


# ── End-to-end via API ──────────────────────────────────────────────────────

class TestInspectionApiAnalysis:
    def test_api_returns_analysis_when_baseline_exists(self):
        itype = "scissors"
        _clear_baselines(itype)
        _add_baseline(itype, "manufacturer")
        resp = client.post("/api/inspections", json={
            "instrument_type": itype,
            "site_name": "Test Hospital",
            "has_image": True,
            "image_sha256": SHA,
            "file_name": "img.jpg",
        }, headers=AUTH_TECH)
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert "analysis" in data
        assert data["analysis"]["analysis_status"] == "completed"
        assert data["analysis"]["inspection_score"] is not None
        assert data["analysis"]["risk_level"] in ("low", "medium", "high", "critical")
        assert data["baseline_source"] == "manufacturer"

    def test_api_supervisor_review_when_no_baseline(self):
        itype = "clip_applier"
        _clear_baselines(itype)
        resp = client.post("/api/inspections", json={
            "instrument_type": itype,
            "site_name": "Test Hospital",
            "has_image": True,
            "image_sha256": SHA,
            "file_name": "img.jpg",
        }, headers=AUTH_TECH)
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["supervisor_review_required"] is True
        assert data["analysis"]["analysis_status"] == "supervisor_review_required"
        assert data["analysis"]["inspection_score"] is None

    def test_api_vendor_baseline_fallback(self):
        itype = "trocar"
        _clear_baselines(itype)
        _add_baseline(itype, "vendor")
        resp = client.post("/api/inspections", json={
            "instrument_type": itype,
            "site_name": "Test Hospital",
            "has_image": True,
            "image_sha256": SHA,
            "file_name": "img.jpg",
        }, headers=AUTH_TECH)
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["baseline_source"] == "vendor"
        assert data["analysis"]["baseline_source"] == "vendor"
        # Vendor is clearly labeled a fallback, not the primary comparison
        assert data["analysis"]["baseline_role"] == "fallback"
        assert data["analysis"]["baseline_comparison_label"] == "Vendor baseline (fallback)"

    def test_manufacturer_preferred_over_vendor_for_comparison(self):
        # Both exist → comparison must use manufacturer (primary), not vendor
        itype = "scissors"
        _clear_baselines(itype)
        _add_baseline(itype, "vendor")
        _add_baseline(itype, "manufacturer")
        resp = client.post("/api/inspections", json={
            "instrument_type": itype,
            "site_name": "Test Hospital",
            "has_image": True,
            "image_sha256": SHA,
            "file_name": "img.jpg",
        }, headers=AUTH_TECH)
        assert resp.status_code == 201, resp.text
        analysis = resp.json()["analysis"]
        assert analysis["baseline_source"] == "manufacturer"
        assert analysis["baseline_role"] == "primary"
        # Clean up so other suites that expect no scissors baseline aren't polluted
        _clear_baselines(itype)
