"""Inspection #30 — baseline-image resolution is decoupled from metadata lookup.

Regression coverage for the P1 pilot blocker: an ACTIVE, compatible, tenant-scoped
manufacturer reference image must resolve and be compared even when no APPROVED
baseline-library *metadata* record exists — previously `analyze_inspection`
early-returned on missing metadata and hardcoded every baseline fact to False,
so a governed ACTIVE reference image (e.g. "Baseline Image #2, Karl Storz") was
silently ignored. Visual similarity is recorded independently of trained-AI
availability; clinical scoring stays independently governed and human review
stays mandatory.
"""
import io
import random

from app.db.session import SessionLocal
from app.models.baseline_library import BaselineLibraryEntry
from app.services import baseline_image_library_service as bil
from app.services import baseline_image_registration_service as bir
from app.services.baseline_comparison_scoring_service import (
    _resolve_from_library,
    _resolve_from_uploaded,
    analyze_inspection,
    resolve_baseline,
)

ITYPE = "rigid_scope"


def _png(seed: int, size=(256, 256)) -> bytes:
    rnd = random.Random(seed)
    raw = bytes(rnd.getrandbits(8) for _ in range(size[0] * size[1] * 3))
    buf = io.BytesIO()
    from PIL import Image
    Image.frombytes("RGB", size, raw).save(buf, format="PNG")
    return buf.getvalue()


def _mk_entry(db, *, itype=ITYPE, mfr, mdl, approval="approved"):
    db.query(BaselineLibraryEntry).filter(BaselineLibraryEntry.instrument_category == itype).delete()
    db.commit()
    entry = BaselineLibraryEntry(
        udi=f"udi-{itype}", instrument_category=itype, manufacturer_name=mfr, model_name=mdl,
        baseline_type="manufacturer", baseline_version="1.0",
        approval_status=approval, approved_by=("seed" if approval == "approved" else None),
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def _mk_active_image(db, *, entry, photo, tenant, activate=True):
    reg = bir.register_manufacturer_reference_image(
        db, tenant_id=tenant, baseline_library_entry_id=entry.id, image_bytes=photo,
        content_type="image/png", uploaded_by="spd@x", source_organization="Karl Storz GmbH",
        source_reference="PO", usage_rights_attested=True, no_phi_attested=True,
        anatomy_zone="", inspection_view="",
    )
    bil.review_baseline_image(
        db, link=reg["link"], reviewer="rev@x", reviewer_role="clinical_reviewer",
        decision="approve", rationale="verified", source_verification="PO",
        anatomy_compatibility_confirmed=True, image_quality_assessment="good",
    )
    if activate:
        bil.activate_baseline_image(db, link=reg["link"], actor="adm@x", actor_role="admin")
    return reg["link"].id


def _analyze(*, tenant, mfr, mdl, photo, image_sha="a" * 64):
    db = SessionLocal()
    try:
        return analyze_inspection(
            db, instrument_type=ITYPE, tenant_id=tenant, has_image=True,
            image_sha256=image_sha, image_bytes=photo,
            instrument_manufacturer=mfr, instrument_model=mdl, demo_scoring=False,
        )
    finally:
        db.close()


# ── 1. Identical ACTIVE reference + inspection (approved metadata) → 100% ──────
def test_identical_active_reference_exact_match():
    T, MFR, MDL = "i30-t1", "Karl Storz", "Hopkins II"
    photo = _png(1)
    db = SessionLocal()
    try:
        entry = _mk_entry(db, mfr=MFR, mdl=MDL, approval="approved")
        link_id = _mk_active_image(db, entry=entry, photo=photo, tenant=T)
    finally:
        db.close()
    ev = _analyze(tenant=T, mfr=MFR, mdl=MDL, photo=photo)["baseline_evidence"]
    assert ev["real_image_comparison_completed"] is True
    assert ev["comparison_status"] == "exact_match"
    assert ev["baseline_image_link_id"] == link_id


# ── 2. Different photos, same compatible instrument → real (not fabricated) ────
def test_different_photos_real_similarity():
    T, MFR, MDL = "i30-t2", "Karl Storz", "Hopkins II"
    db = SessionLocal()
    try:
        entry = _mk_entry(db, mfr=MFR, mdl=MDL, approval="approved")
        _mk_active_image(db, entry=entry, photo=_png(10), tenant=T)
    finally:
        db.close()
    a = _analyze(tenant=T, mfr=MFR, mdl=MDL, photo=_png(999))
    sim = a["ai_analysis"]["baseline_image_similarity"]
    assert sim["is_image_comparison"] is True
    assert sim["similarity"] is not None
    assert sim["status"] != "exact_match"  # different photos are not an exact match


# ── 3. #30: metadata lookup fails, ACTIVE compatible image exists → resolves ───
def test_metadata_absent_active_image_still_resolves():
    T, MFR, MDL = "i30-t3", "Karl Storz", "Hopkins II"
    photo = _png(30)
    db = SessionLocal()
    try:
        # Entry NOT approved → metadata resolution fails (the #30 condition).
        entry = _mk_entry(db, mfr=MFR, mdl=MDL, approval="pending")
        link_id = _mk_active_image(db, entry=entry, photo=photo, tenant=T)
    finally:
        db.close()
    a = _analyze(tenant=T, mfr=MFR, mdl=MDL, photo=photo)
    ev = a["baseline_evidence"]
    assert ev["manufacturer_baseline_metadata_found"] is False  # no approved metadata
    assert ev["baseline_image_registered"] is True
    assert ev["baseline_image_active"] is True
    assert ev["baseline_image_compatible"] is True
    assert ev["real_image_comparison_completed"] is True
    assert ev["comparison_status"] == "exact_match"
    assert ev["baseline_image_link_id"] == link_id


# ── 4. Truly incompatible instrument → no clinical baseline comparison ─────────
def test_incompatible_manufacturer_no_comparison():
    T = "i30-t4"
    db = SessionLocal()
    try:
        entry = _mk_entry(db, mfr="Alpha Surgical", mdl="A-1", approval="approved")
        _mk_active_image(db, entry=entry, photo=_png(41), tenant=T)
    finally:
        db.close()
    # Inspection declares a DIFFERENT manufacturer than the ACTIVE reference.
    ev = _analyze(tenant=T, mfr="Beta Medical", mdl="B-9", photo=_png(41))["baseline_evidence"]
    assert ev["real_image_comparison_completed"] is False


# ── 5. ACTIVE image in another tenant → access denied (not resolved) ───────────
def test_cross_tenant_active_image_denied():
    MFR, MDL = "Karl Storz", "Hopkins II"
    photo = _png(5)
    db = SessionLocal()
    try:
        entry = _mk_entry(db, mfr=MFR, mdl=MDL, approval="pending")
        _mk_active_image(db, entry=entry, photo=photo, tenant="tenant-owner")
    finally:
        db.close()
    ev = _analyze(tenant="tenant-other", mfr=MFR, mdl=MDL, photo=photo)["baseline_evidence"]
    assert ev["baseline_image_active"] is False
    assert ev["real_image_comparison_completed"] is False


# ── 6. Reference inactive (APPROVED, never activated) → no governed comparison ─
def test_inactive_reference_no_comparison():
    T, MFR, MDL = "i30-t6", "Karl Storz", "Hopkins II"
    photo = _png(6)
    db = SessionLocal()
    try:
        entry = _mk_entry(db, mfr=MFR, mdl=MDL, approval="pending")
        _mk_active_image(db, entry=entry, photo=photo, tenant=T, activate=False)  # stays APPROVED
    finally:
        db.close()
    ev = _analyze(tenant=T, mfr=MFR, mdl=MDL, photo=photo)["baseline_evidence"]
    assert ev["baseline_image_active"] is False
    assert ev["real_image_comparison_completed"] is False


# ── 7. Missing image bytes → explicit unavailable status, no fabricated score ──
def test_missing_image_bytes_status():
    T, MFR, MDL = "i30-t7", "Karl Storz", "Hopkins II"
    db = SessionLocal()
    try:
        entry = _mk_entry(db, mfr=MFR, mdl=MDL, approval="pending")
        _mk_active_image(db, entry=entry, photo=_png(7), tenant=T)
        a = analyze_inspection(
            db, instrument_type=ITYPE, tenant_id=T, has_image=True, image_sha256="b" * 64,
            image_bytes=None, instrument_manufacturer=MFR, instrument_model=MDL, demo_scoring=False,
        )
    finally:
        db.close()
    ev = a["baseline_evidence"]
    assert ev["inspection_image_bytes_available"] is False
    assert ev["real_image_comparison_completed"] is False
    sim = a["ai_analysis"]["baseline_image_similarity"]
    assert sim is None or sim.get("similarity") is None  # never a fabricated number


# ── 8. No trained vision model → comparison still works, AI stays unavailable ──
def test_no_trained_model_comparison_still_runs():
    T, MFR, MDL = "i30-t8", "Karl Storz", "Hopkins II"
    photo = _png(8)
    db = SessionLocal()
    try:
        entry = _mk_entry(db, mfr=MFR, mdl=MDL, approval="pending")
        _mk_active_image(db, entry=entry, photo=photo, tenant=T)
    finally:
        db.close()
    a = _analyze(tenant=T, mfr=MFR, mdl=MDL, photo=photo)
    ev = a["baseline_evidence"]
    assert ev["trained_vision_model_available"] is False
    assert ev["real_image_comparison_completed"] is True
    assert a["ai_analysis"]["status"] == "AI_UNAVAILABLE"


# ── 9. Human review stays mandatory; similarity never authorizes release ───────
def test_human_review_mandatory_on_exact_match():
    T, MFR, MDL = "i30-t9", "Karl Storz", "Hopkins II"
    photo = _png(9)
    db = SessionLocal()
    try:
        entry = _mk_entry(db, mfr=MFR, mdl=MDL, approval="pending")
        _mk_active_image(db, entry=entry, photo=photo, tenant=T)
    finally:
        db.close()
    a = _analyze(tenant=T, mfr=MFR, mdl=MDL, photo=photo)
    assert a["ai_analysis"]["human_review_required"] is True
    assert a["ai_analysis"]["authorizes_release"] is False
    assert a["predicted_findings"] == []
    assert a["inspection_score"] is None


# ── 10. Clinical report (PDF) renders the comparison for the #30 path ──────────
def test_clinical_pdf_renders_for_decoupled_comparison():
    from app.services.clinical_report_pdf import build_clinical_report_pdf

    class _Row:
        id = 30
        facility_name = "P"
        site_name = "P"
        instrument_type = ITYPE
        instrument_barcode = None
        instrument_udi = None
        created_at = None
        baseline_comparison_status = "exact_match"

    T, MFR, MDL = "i30-t10", "Karl Storz", "Hopkins II"
    photo = _png(11)
    db = SessionLocal()
    try:
        entry = _mk_entry(db, mfr=MFR, mdl=MDL, approval="pending")
        _mk_active_image(db, entry=entry, photo=photo, tenant=T)
    finally:
        db.close()
    a = _analyze(tenant=T, mfr=MFR, mdl=MDL, photo=photo)
    pdf = build_clinical_report_pdf(_Row(), a)
    assert pdf[:5] == b"%PDF-"


# ── 11. Typed identifiers never conflate tables (Task 3) ──────────────────────
def test_typed_identifiers_do_not_conflate_tables():
    db = SessionLocal()
    try:
        entry = _mk_entry(db, mfr="Karl Storz", mdl="Hopkins II", approval="approved")
        lib = _resolve_from_library(db, ITYPE, manufacturer="Karl Storz", model="Hopkins II")
        assert lib is not None
        # The library resolver exposes a real BaselineLibraryEntry id.
        assert lib["baseline_library_entry_id"] == entry.id
        assert lib["vendor_subscription_id"] is None
        # The uploaded (vendor-subscription) resolver, when it matches, must NOT
        # put a subscription id where a library-entry id is expected.
        up = _resolve_from_uploaded(db, ITYPE)
        if up is not None:
            assert up["baseline_library_entry_id"] is None
            assert up["vendor_subscription_id"] is not None
        # Not-found resolution carries both typed ids as None.
        nf = resolve_baseline(db, "no_such_instrument_type", "t", manufacturer="X", model="Y")
        assert nf["baseline_library_entry_id"] is None
        assert nf["vendor_subscription_id"] is None
    finally:
        db.close()
