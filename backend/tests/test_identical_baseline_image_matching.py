"""Exact manufacturer baseline image matching — end to end.

Verifies the specific pilot scenario the operator reported: the SAME photograph
is uploaded as the approved manufacturer reference AND as the new inspection
image. The real comparator must recognise the byte-identical pair and the result
must flow through every surface as an exact match (100% visual similarity) —
WITHOUT ever being represented as proof of cleanliness, and with the trained
vision model staying honestly separate (AI_UNAVAILABLE).

The comparator is exercised directly (unit) and through the real HTTP routes +
service-layer baseline governance (end to end). Baseline bytes and inspection
bytes both pass through the same deterministic EXIF-strip normalisation, so an
identical original yields byte-identical stored bytes on both sides →
``sha256_exact``.
"""
import io

from fastapi.testclient import TestClient
from PIL import Image

from app.db.session import SessionLocal
from app.main import app
from app.models.inspection import Inspection
from app.services.ml.image_similarity_service import (
    COMPARATOR_VERSION,
    compare_against_baseline,
    compare_image_bytes,
)
from tests.test_manufacturer_baseline_image_integration import (
    _approve_and_activate,
    _mfr,
    _model,
    _register_reference,
    _seed_entry,
)

client = TestClient(app)
TENANT = "identical-img-tenant"


def _hdr(tenant=TENANT):
    return {"Authorization": "Bearer dev-token", "X-Tenant-Id": tenant, "X-User-Role": "admin"}


def _png(seed: int, size=(256, 256)) -> bytes:
    import random
    rnd = random.Random(seed)
    raw = bytes(rnd.getrandbits(8) for _ in range(size[0] * size[1] * 3))
    buf = io.BytesIO()
    Image.frombytes("RGB", size, raw).save(buf, format="PNG")
    return buf.getvalue()


def _upload(img: bytes, tenant=TENANT, filename="insp.png"):
    return client.post(
        "/api/inspections/upload-images",
        files={"images": (filename, img, "image/png")},
        params={"instrument_type": "rigid_scope"},
        headers=_hdr(tenant=tenant),
    )


def _submit(sha, itype="rigid_scope", mfr="", model="", tenant=TENANT):
    return client.post("/api/inspections", json={
        "instrument_type": itype, "site_name": "P", "facility_name": "P",
        "has_image": True, "image_sha256": sha, "file_name": "insp.png",
        "instrument_manufacturer": mfr, "instrument_model": model, "vendor_name": mfr,
        "finding_categories": [],
    }, headers=_hdr(tenant=tenant))


def _make_active(itype, img, tenant=TENANT):
    db = SessionLocal()
    try:
        entry = _seed_entry(db, instrument_type=itype)
        reg = _register_reference(db, entry=entry, image_bytes=img, tenant=tenant)
        link = _approve_and_activate(db, link=reg["link"], tenant=tenant)
        return entry.id, link.id
    finally:
        db.close()


def _run_identical_e2e(seed: int):
    """Register ``_png(seed)`` as the ACTIVE reference, upload the SAME bytes as
    the inspection, submit, and return (analysis, link_id, inspection_id)."""
    itype = "rigid_scope"
    photo = _png(seed)
    _entry_id, link_id = _make_active(itype, photo)
    up = _upload(photo)
    assert up.status_code == 200, up.text
    assert up.json()["images"][0]["processing_available"] is True
    sha = up.json()["images"][0]["sha256"]
    r = _submit(sha, itype=itype, mfr=_mfr(itype), model=_model(itype))
    assert r.status_code == 201, r.text
    return r.json()["analysis"], link_id, r.json()["id"]


# ── 1. Comparator unit: byte-identical valid images → exact match ─────────────
def test_comparator_identical_bytes_is_exact_match():
    img = _png(11)
    result = compare_image_bytes(img, img)
    assert result == {
        "status": "exact_match", "similarity": 1.0, "hamming_distance": 0,
        "method": "sha256_exact", "comparator_version": COMPARATOR_VERSION,
    }


# ── 2. Decode gate: identical NON-image bytes are NOT an exact match ──────────
def test_comparator_identical_non_image_bytes_not_exact_match():
    not_an_image = b"this is not an image, just identical bytes" * 8
    result = compare_image_bytes(not_an_image, not_an_image)
    # Byte-identical, but neither input decodes as an image → must be reported
    # insufficient_quality, never a (meaningless) exact_match of two non-images.
    assert result["status"] == "insufficient_quality"
    assert result["status"] != "exact_match"
    assert result["similarity"] is None


# ── 3. Exact match requires true byte identity (re-encode ≠ exact) ────────────
def test_comparator_reencoded_copy_is_not_exact_but_highly_similar():
    img = _png(13)
    # Same pixels, re-encoded → different bytes, so not sha256-equal, but the
    # perceptual hash still recognises them as the same picture.
    with Image.open(io.BytesIO(img)) as im:
        buf = io.BytesIO()
        im.convert("RGB").save(buf, format="PNG", optimize=True)
        reencoded = buf.getvalue()
    result = compare_image_bytes(img, reencoded)
    assert result["status"] != "exact_match"
    assert result["status"] in {"comparable", "materially_different"}
    assert result["similarity"] is not None


# ── 4. compare_against_baseline threads identity through an exact match ────────
def test_compare_against_baseline_identical_exact_match():
    img = _png(14)
    result = compare_against_baseline(
        image_bytes=img, baseline_image_bytes=img,
        candidate_instrument_family="rigid_scope", baseline_instrument_family="rigid_scope",
        candidate_manufacturer="Acme", baseline_manufacturer="Acme",
        baseline_available=True, baseline_id=777, baseline_version="2.1",
    )
    assert result["status"] == "exact_match"
    assert result["similarity"] == 1.0
    assert result["method"] == "sha256_exact"
    assert result["baseline_id"] == 777
    assert result["baseline_version"] == "2.1"


# ── 5. E2E: ai_analysis.baseline_image_similarity reports the exact match ──────
def test_e2e_identical_surfaces_exact_match_similarity():
    analysis, link_id, _iid = _run_identical_e2e(21)
    sim = analysis["ai_analysis"]["baseline_image_similarity"]
    assert sim["is_image_comparison"] is True
    assert sim["status"] == "exact_match"
    assert sim["similarity"] == 1.0
    assert sim["method"] == "sha256_exact"
    assert sim["comparator_version"] == COMPARATOR_VERSION
    assert sim["baseline_id"] == link_id


# ── 6. E2E: baseline_evidence confirms a real comparison completed ────────────
def test_e2e_identical_baseline_evidence_completed():
    analysis, link_id, _iid = _run_identical_e2e(22)
    ev = analysis["baseline_evidence"]
    assert ev["manufacturer_baseline_metadata_found"] is True
    assert ev["baseline_image_registered"] is True
    assert ev["baseline_image_active"] is True
    assert ev["baseline_image_compatible"] is True
    assert ev["inspection_image_bytes_available"] is True
    assert ev["real_image_comparison_completed"] is True
    assert ev["comparison_status"] == "exact_match"
    assert ev["baseline_image_link_id"] == link_id


# ── 7. E2E: the exact match is persisted (report/history match the page) ───────
def test_e2e_identical_persisted_columns():
    _analysis, link_id, iid = _run_identical_e2e(23)
    db = SessionLocal()
    try:
        row = db.query(Inspection).filter(Inspection.id == iid).first()
        assert row.baseline_comparison_status == "exact_match"
        assert row.baseline_comparison_similarity == 1.0
        assert row.baseline_comparison_method == "sha256_exact"
        assert row.baseline_image_link_id == link_id
    finally:
        db.close()


# ── 8. E2E: an exact IMAGE match never fabricates a clinical clearance ─────────
def test_e2e_identical_does_not_authorize_release():
    analysis, _link_id, _iid = _run_identical_e2e(24)
    # 100% visual similarity is NOT cleanliness: no finding, no score, no release.
    assert analysis["predicted_findings"] == []
    assert analysis["inspection_score"] is None
    assert analysis["ai_analysis"]["authorizes_release"] is False
    assert analysis["ai_analysis"]["human_review_required"] is True


# ── 9. E2E: trained vision model stays honestly separate on an exact match ─────
def test_e2e_identical_trained_model_still_unavailable():
    analysis, _link_id, _iid = _run_identical_e2e(25)
    assert analysis["baseline_evidence"]["trained_vision_model_available"] is False
    assert analysis["ai_analysis"]["status"] == "AI_UNAVAILABLE"


# ── 10. E2E: the clinical report renders the exact-match comparison ───────────
def test_e2e_identical_clinical_report_renders():
    _analysis, _link_id, iid = _run_identical_e2e(26)
    pdf = client.get(f"/api/inspections/{iid}/clinical-report.pdf", headers=_hdr())
    assert pdf.status_code == 200
    assert pdf.content[:5] == b"%PDF-"
