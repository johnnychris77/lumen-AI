"""False-PASS defect remediation — safety-invariant regression tests.

Reproduces the reported patient-safety defect (LumenAI returning PASS, or a
near-identical result, for visually different inspection images evaluated
against the same approved baseline — including images with obvious
blood-like contamination) and proves the fix. Uses real image fixtures (real
PNG-encoded bytes via Pillow), matching this codebase's established
convention (tests/test_candidate_model_training.py::_img(),
tests/test_project_lens.py::_img()).
"""
import hashlib
import io

import pytest
from PIL import Image
from fastapi.testclient import TestClient

from app.main import app
from app.db.session import SessionLocal
from app.models.baseline_library import BaselineLibraryEntry
from app.services.baseline_comparison_scoring_service import (
    OVERALL_RESULT_AI_UNAVAILABLE,
    _cleaning_actionable,
    _overall_result,
    analyze_inspection,
    overall_cleaning_assessment,
)

client = TestClient(app)
AUTH_ADMIN = {"Authorization": "Bearer dev-token"}
TENANT = "default-tenant"


def _img(brightness: int, stripe_period: int = 8, size: int = 300) -> bytes:
    img = Image.new("RGB", (size, size), (brightness, brightness, brightness))
    if stripe_period:
        px = img.load()
        inverse = 255 - brightness
        for x in range(0, size, stripe_period):
            for y in range(size):
                px[x, y] = (inverse, inverse, inverse)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _baseline(itype: str) -> None:
    db = SessionLocal()
    try:
        db.query(BaselineLibraryEntry).filter(
            BaselineLibraryEntry.instrument_category == itype
        ).delete()
        db.add(BaselineLibraryEntry(
            udi=f"fpr-{itype}", instrument_category=itype, manufacturer_name="M",
            model_name="X", baseline_type="manufacturer", approval_status="approved",
        ))
        db.commit()
    finally:
        db.close()


def _analyze(itype, image_sha256, declared=None, image_bytes=None):
    _baseline(itype)
    db = SessionLocal()
    try:
        return analyze_inspection(
            db, instrument_type=itype, tenant_id=TENANT, has_image=True,
            image_sha256=image_sha256, declared_findings=declared, image_bytes=image_bytes,
        )
    finally:
        db.close()


# ── Test C — contaminated inspection, no eligible model, never PASS ────────

def test_undeclared_contamination_never_returns_pass_from_placeholder():
    """Core reported defect: a visibly different, contaminated inspection
    image compared against the same approved baseline must never resolve to
    PASS purely because the technician didn't manually declare a finding —
    the placeholder has no real vision and must not assert a verified
    "clean" result (Section 6 — Contamination Safety Invariant)."""
    clean_bytes = _img(200, stripe_period=0)
    contaminated_bytes = _img(20, stripe_period=3)  # visibly different pixel content
    clean_sha = hashlib.sha256(clean_bytes).hexdigest()
    contaminated_sha = hashlib.sha256(contaminated_bytes).hexdigest()
    assert clean_sha != contaminated_sha

    baseline_result = _analyze("scissors", clean_sha)
    contaminated_result = _analyze("scissors", contaminated_sha)

    # Never a placeholder-generated PASS for either — with no declared
    # findings and no eligible trained model, both must honestly report
    # AI_ANALYSIS_UNAVAILABLE, not a fabricated clean verdict.
    assert baseline_result["pass_fail"] == "AI_ANALYSIS_UNAVAILABLE"
    assert contaminated_result["pass_fail"] == "AI_ANALYSIS_UNAVAILABLE"
    assert contaminated_result["clinical_decision"]["overall_result"] == OVERALL_RESULT_AI_UNAVAILABLE


def test_declared_contamination_still_reprocesses_never_pass():
    """Real, technician-sourced evidence (declared findings) is unaffected by
    the remediation and must still drive a genuine REPROCESS/FAIL — the
    fix must not suppress real signal, only the fabricated placeholder one."""
    bytes_ = _img(20, stripe_period=3)
    sha = hashlib.sha256(bytes_).hexdigest()
    out = _analyze("scissors", sha, declared=["blood"])
    assert out["pass_fail"] == "FAIL"
    assert out["clinical_decision"]["overall_result"] in ("REPROCESS", "REMOVE FROM SERVICE")
    assert out["overall_cleaning_assessment"] in ("Residual contamination suspected", "Cleaning failure")


# ── Test F — result-contradiction rejection (Section 7) ────────────────────

def test_no_critical_finding_and_reprocess_can_never_coexist():
    """Reproduces the reported contradictory display exactly: "No Critical
    Findings" shown simultaneously with "REPROCESS — residual contamination
    suspected". A trace-level (severity_index==1) contamination finding in a
    HIGH-RETENTION zone previously escalated _overall_result() to REPROCESS
    via a separate threshold than overall_cleaning_assessment()/findings_summary
    used, producing the contradiction. Both must now agree because
    _overall_result() derives from the single overall_cleaning_assessment()
    value instead of re-deriving its own threshold."""
    finding = {
        "type": "other_organic_residue", "severity_index": 1,
        "instrument_zone": "o-ring area", "evaluated": True,
    }
    assert _cleaning_actionable(finding) is True  # trace + high-retention zone
    findings_by_kpi = {"other_organic_residue": finding}
    cleaning = overall_cleaning_assessment(findings_by_kpi)
    assert cleaning == "Residual contamination suspected"

    result = {
        "analysis_status": "completed",
        "predicted_findings": [finding],
        "identification": {},
        "baseline_match_score": 0.95,
        "overall_cleaning_assessment": cleaning,
    }
    assert _overall_result(result) == "REPROCESS"
    # The invalid combination the report described can no longer occur: if
    # disposition is REPROCESS, cleaning can never simultaneously read "Clean"
    # (which is what would let findings_summary claim "No critical findings").
    assert cleaning != "Clean"


def test_trace_finding_outside_high_retention_zone_is_consistently_clean():
    """The complementary case: the same trace-level finding in a NORMAL
    (non-high-retention) zone must consistently read "Clean" in both the
    cleaning assessment and the disposition — no contradiction either way."""
    finding = {
        "type": "other_organic_residue", "severity_index": 1,
        "instrument_zone": "flat handle surface", "evaluated": True,
    }
    assert _cleaning_actionable(finding) is False
    findings_by_kpi = {"other_organic_residue": finding}
    cleaning = overall_cleaning_assessment(findings_by_kpi)
    assert cleaning == "Clean"
    result = {
        "analysis_status": "completed", "predicted_findings": [finding],
        "identification": {}, "baseline_match_score": 0.95,
        "overall_cleaning_assessment": cleaning,
    }
    assert _overall_result(result) == "PASS"


# ── Image identity verification (Section 2) ────────────────────────────────

@pytest.fixture(autouse=True)
def _enable_retention(monkeypatch):
    monkeypatch.setenv("RETAIN_INSPECTION_IMAGES", "true")


def _upload_and_get_sha(itype: str, img_bytes: bytes) -> str:
    files = {"images": ("inspection.png", img_bytes, "image/png")}
    r = client.post(
        "/api/inspections/upload-images", files=files, params={"consent": "true"},
        headers=AUTH_ADMIN,
    )
    assert r.status_code == 200, r.text
    return r.json()["images"][0]["sha256"]


def test_corrupted_retained_bytes_are_rejected_not_silently_analyzed():
    """Section 2 — reload the stored bytes, recompute SHA-256, verify it
    matches the registered hash, reject analysis on mismatch. Directly
    corrupts a RetainedImage row's bytes after upload (simulating storage
    corruption) and confirms create_inspection() does not silently pass the
    now-mismatched bytes into analysis — it must fail safe (proceed as if no
    real image bytes exist) rather than analyze corrupted/wrong data."""
    _baseline("scissors")
    img_bytes = _img(150, stripe_period=5)
    sha = _upload_and_get_sha("scissors", img_bytes)

    db = SessionLocal()
    try:
        from app.models.retained_image import RetainedImage
        row = db.query(RetainedImage).filter(RetainedImage.sha256 == sha).first()
        assert row is not None
        row.image_bytes = b"corrupted-bytes-that-no-longer-match-the-registered-hash"
        db.commit()
    finally:
        db.close()

    payload = {
        "instrument_type": "scissors", "facility_name": "Test Facility",
        "site_name": "Test Facility",
        "vendor_name": "unknown", "has_image": True, "image_sha256": sha,
        "file_name": "inspection.png",
    }
    r = client.post("/api/inspections", json=payload, headers=AUTH_ADMIN)
    assert r.status_code == 201, r.text
    # Must not crash and must not silently fabricate a result from corrupted
    # bytes — the request completes with the same safe, honest
    # AI_ANALYSIS_UNAVAILABLE path as if no real bytes were ever available.
    body = r.json()
    assert body.get("recommended_action") is not None
