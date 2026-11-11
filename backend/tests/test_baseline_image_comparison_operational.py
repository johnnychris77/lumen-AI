"""Make real manufacturer baseline image comparison operational — end-to-end.

Proves the corrected pilot workflow: an uploaded inspection photograph is
compared against verified, compatible manufacturer reference-image bytes WITHOUT
being enrolled in a training dataset, via the temporary processing pathway —
while the trained-model status stays honestly separate and no fabricated score is
produced.

Baseline governance is driven through the real service layer; the upload +
inspection go through the real HTTP routes.
"""
import io

from fastapi.testclient import TestClient
from PIL import Image

from app.db.session import SessionLocal
from app.main import app
from app.models.dataset_governance import DatasetRegistryEntry
from app.models.inspection import Inspection
from app.models.inspection_processing_image import InspectionProcessingImage
from app.services import inspection_image_processing_service as proc
from tests.test_manufacturer_baseline_image_integration import (
    _approve_and_activate,
    _mfr,
    _model,
    _register_reference,
    _seed_entry,
)

client = TestClient(app)
TENANT = "pilot-op-tenant"


def _hdr(role="admin", tenant=TENANT):
    return {"Authorization": "Bearer dev-token", "X-Tenant-Id": tenant, "X-User-Role": role}


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


def _submit(sha, itype="rigid_scope", mfr="", model="", tenant=TENANT, tags=None):
    body = {
        "instrument_type": itype, "site_name": "Pilot Hospital", "facility_name": "Pilot Hospital",
        "has_image": True, "image_sha256": sha, "file_name": "insp.png",
        "instrument_manufacturer": mfr, "instrument_model": model, "vendor_name": mfr,
        "finding_categories": [],
    }
    if tags:
        body["image_view_tags"] = tags
    return client.post("/api/inspections", json=body, headers=_hdr(tenant=tenant))


def _make_active(itype, img, tenant=TENANT):
    db = SessionLocal()
    try:
        entry = _seed_entry(db, instrument_type=itype)
        reg = _register_reference(db, entry=entry, image_bytes=img, tenant=tenant)
        link = _approve_and_activate(db, link=reg["link"], tenant=tenant)
        return entry.id, link.id
    finally:
        db.close()


# ── Happy path: real comparison via the temporary processing pathway ──────────
def test_operational_comparison_end_to_end():
    itype = "rigid_scope"
    # Distinct baseline vs inspection photos (realistic — the inspection image is
    # not byte-identical to the reference), so the inspection's own hash differs
    # from the baseline's governed LCID entry.
    baseline_img = _png(101)
    inspection_img = _png(102)
    _entry_id, link_id = _make_active(itype, baseline_img)

    up = _upload(inspection_img)
    assert up.status_code == 200, up.text
    sha = up.json()["images"][0]["sha256"]
    assert up.json()["images"][0]["processing_available"] is True

    r = _submit(sha, itype=itype, mfr=_mfr(itype), model=_model(itype))
    assert r.status_code == 201, r.text
    a = r.json()["analysis"]

    # A REAL pixel comparison completed against the verified reference bytes.
    sim = a["ai_analysis"]["baseline_image_similarity"]
    assert sim["is_image_comparison"] is True
    assert sim["similarity"] is not None
    assert sim["baseline_id"] == link_id
    assert sim["method"]
    ev = a["baseline_evidence"]
    assert ev["real_image_comparison_completed"] is True
    assert ev["inspection_image_bytes_available"] is True
    # … while the trained vision model stays unavailable (separate surface).
    assert ev["trained_vision_model_available"] is False
    assert a["ai_analysis"]["status"] == "AI_UNAVAILABLE"
    # No fabricated clinical result.
    assert a["predicted_findings"] == []
    assert a["inspection_score"] is None
    assert a["ai_analysis"]["authorizes_release"] is False

    iid = r.json()["id"]
    db = SessionLocal()
    try:
        row = db.query(Inspection).filter(Inspection.id == iid).first()
        # Persisted comparison result (so report/history match without the pixels).
        assert row.baseline_comparison_similarity is not None
        assert row.baseline_image_link_id == link_id
        assert row.baseline_comparison_method
        # Temporary processing image consumed (bytes removed), NOT enrolled in training.
        prow = (
            db.query(InspectionProcessingImage)
            .filter(InspectionProcessingImage.tenant_id == TENANT, InspectionProcessingImage.image_sha256 == sha)
            .first()
        )
        assert prow.status == "consumed"
        assert prow.image_bytes is None
        assert db.query(DatasetRegistryEntry).filter(
            DatasetRegistryEntry.tenant_id == TENANT,
            DatasetRegistryEntry.image_sha256 == prow.stored_sha256,
        ).first() is None
    finally:
        db.close()

    # The clinical report reflects the same comparison (pixels already purged).
    pdf = client.get(f"/api/inspections/{iid}/clinical-report.pdf", headers=_hdr())
    assert pdf.status_code == 200
    assert pdf.content[:5] == b"%PDF-"


# ── The comparator responds to actual image differences ───────────────────────
def test_comparator_responds_to_differences():
    itype = "rigid_scope"
    baseline_img = _png(201)
    _make_active(itype, baseline_img)

    # Same image → exact/high similarity.
    up_same = _upload(baseline_img, filename="same.png")
    same = _submit(up_same.json()["images"][0]["sha256"], itype=itype, mfr=_mfr(itype), model=_model(itype))
    sim_same = same.json()["analysis"]["ai_analysis"]["baseline_image_similarity"]["similarity"]

    # Clearly different image → a lower similarity (the comparator reacts).
    different_img = _png(999)
    up_diff = _upload(different_img, filename="diff.png")
    diff = _submit(up_diff.json()["images"][0]["sha256"], itype=itype, mfr=_mfr(itype), model=_model(itype))
    diff_sim = diff.json()["analysis"]["ai_analysis"]["baseline_image_similarity"]
    assert diff_sim["is_image_comparison"] is True
    assert diff_sim["similarity"] is not None
    assert diff_sim["similarity"] < sim_same


# ── Incompatible manufacturer → no comparison ─────────────────────────────────
def test_incompatible_manufacturer_no_comparison():
    itype = "rigid_scope"
    img = _png(301)
    _make_active(itype, img)
    up = _upload(img)
    r = _submit(up.json()["images"][0]["sha256"], itype=itype, mfr="Totally Different Mfr", model="X")
    ev = r.json()["analysis"]["baseline_evidence"]
    assert ev["real_image_comparison_completed"] is False


# ── Missing inspection bytes → comparison unavailable ─────────────────────────
def test_missing_inspection_bytes_unavailable():
    itype = "rigid_scope"
    img = _png(401)
    _make_active(itype, img)
    # Submit with a sha that was never uploaded → no processing bytes available.
    r = _submit("f" * 64, itype=itype, mfr=_mfr(itype), model=_model(itype))
    assert r.status_code == 201, r.text
    ev = r.json()["analysis"]["baseline_evidence"]
    assert ev["inspection_image_bytes_available"] is False
    assert ev["real_image_comparison_completed"] is False


# ── Cross-tenant: a processing image is never loadable by another tenant ───────
def test_processing_image_cross_tenant_denied():
    img = _png(501)
    up = _upload(img, tenant="tenant-aaa")
    sha = up.json()["images"][0]["sha256"]
    db = SessionLocal()
    try:
        mine, _ = proc.load_processing_bytes(db, tenant_id="tenant-aaa", image_sha256=sha)
        theirs, _ = proc.load_processing_bytes(db, tenant_id="tenant-bbb", image_sha256=sha)
        assert mine is not None
        assert theirs is None
    finally:
        db.close()


# ── Hash-mismatched processing bytes are never returned ───────────────────────
def test_processing_hash_mismatch_not_returned():
    img = _png(601)
    up = _upload(img, tenant="tenant-hash")
    sha = up.json()["images"][0]["sha256"]
    db = SessionLocal()
    try:
        row = (
            db.query(InspectionProcessingImage)
            .filter(InspectionProcessingImage.tenant_id == "tenant-hash", InspectionProcessingImage.image_sha256 == sha)
            .first()
        )
        row.image_bytes = _png(602)  # corrupt the stored bytes
        db.commit()
        got, _ = proc.load_processing_bytes(db, tenant_id="tenant-hash", image_sha256=sha)
        assert got is None
    finally:
        db.close()


# ── Processing images are not retained for training without consent ───────────
def test_processing_not_enrolled_in_training():
    itype = "rigid_scope"
    _make_active(itype, _png(701))
    up = _upload(_png(702), filename="notrain.png")
    sha = up.json()["images"][0]["sha256"]
    _submit(sha, itype=itype, mfr=_mfr(itype), model=_model(itype))
    db = SessionLocal()
    try:
        # No training RetainedImage row was created for this inspection image
        # (retention was never enabled / consented), and no dataset entry exists.
        from app.models.retained_image import RetainedImage
        prow = (
            db.query(InspectionProcessingImage)
            .filter(InspectionProcessingImage.tenant_id == TENANT, InspectionProcessingImage.image_sha256 == sha)
            .first()
        )
        assert db.query(RetainedImage).filter(
            RetainedImage.tenant_id == TENANT, RetainedImage.sha256 == prow.stored_sha256,
        ).first() is None
        assert db.query(DatasetRegistryEntry).filter(
            DatasetRegistryEntry.tenant_id == TENANT, DatasetRegistryEntry.image_sha256 == prow.stored_sha256,
        ).first() is None
    finally:
        db.close()


# ── The clinical report renders the baseline comparison (visual similarity) ───
def test_report_renders_baseline_comparison():
    from app.services.clinical_report_pdf import build_clinical_report_pdf

    class _Row:
        id = 1
        facility_name = "P"
        site_name = "P"
        instrument_type = "rigid_scope"
        instrument_barcode = None
        instrument_udi = None
        created_at = None
        baseline_comparison_status = "materially_different"

    base = {"ai_analysis": {"status": "AI_UNAVAILABLE"}, "technician_declared_observations": []}
    with_cmp = {"ai_analysis": {"status": "AI_UNAVAILABLE", "baseline_image_similarity": {
        "is_image_comparison": True, "similarity": 0.44, "status": "materially_different",
        "method": "average_hash_hamming", "comparator_version": "lens-average-hash-v1",
        "baseline_id": 1, "baseline_version": "1.0"}}, "technician_declared_observations": []}
    without = build_clinical_report_pdf(_Row(), base)
    withc = build_clinical_report_pdf(_Row(), with_cmp)
    assert without[:5] == b"%PDF-" and withc[:5] == b"%PDF-"
    # The comparison section adds content to the (AI-unavailable) report.
    assert len(withc) > len(without)


# ── Expired processing images are purged ──────────────────────────────────────
def test_expired_processing_images_purged():
    from datetime import datetime, timedelta, timezone
    img = _png(801)
    up = _upload(img, tenant="tenant-exp")
    sha = up.json()["images"][0]["sha256"]
    db = SessionLocal()
    try:
        row = (
            db.query(InspectionProcessingImage)
            .filter(InspectionProcessingImage.tenant_id == "tenant-exp", InspectionProcessingImage.image_sha256 == sha)
            .first()
        )
        row.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        db.commit()
        removed = proc.purge_expired(db)
        assert removed >= 1
        assert db.query(InspectionProcessingImage).filter(
            InspectionProcessingImage.tenant_id == "tenant-exp", InspectionProcessingImage.image_sha256 == sha
        ).first() is None
    finally:
        db.close()


# ── Upload/create tenant resolution must agree (production JWT scenario) ───────
def test_upload_and_create_resolve_same_tenant_for_jwt_user():
    """Reproduces the production blocker: a logged-in (JWT) user whose membership
    tenant is resolved server-side, with NO X-Tenant-Id header. The upload must
    store the processing image under the SAME tenant the inspection-create route
    looks it up under, or the comparison silently loses the pixels."""
    from app.deps import get_current_user

    class _User:
        tenant_id = "jwt-tenant-xyz"
        tenant_name = "JWT Tenant"
        role = "admin"
        email = "clinician@hospital.example"
        username = "clinician@hospital.example"

    itype = "rigid_scope"
    _make_active(itype, _png(1201), tenant="jwt-tenant-xyz")

    app.dependency_overrides[get_current_user] = lambda: _User()
    try:
        # NOTE: deliberately no X-Tenant-Id header — tenant comes from the user.
        plain = {"Authorization": "Bearer dev-token"}
        up = client.post("/api/inspections/upload-images",
                         files={"images": ("insp.png", _png(1202), "image/png")},
                         params={"instrument_type": itype}, headers=plain)
        assert up.status_code == 200, up.text
        assert up.json()["images"][0]["processing_available"] is True
        sha = up.json()["images"][0]["sha256"]

        r = client.post("/api/inspections", json={
            "instrument_type": itype, "site_name": "P", "facility_name": "P",
            "has_image": True, "image_sha256": sha, "file_name": "insp.png",
            "instrument_manufacturer": _mfr(itype), "instrument_model": _model(itype),
            "vendor_name": _mfr(itype), "finding_categories": [],
        }, headers=plain)
        assert r.status_code == 201, r.text
        ev = r.json()["analysis"]["baseline_evidence"]
        # The processing image stored at upload time is found at create time
        # because both resolved tenant='jwt-tenant-xyz' (not 'default-tenant').
        assert ev["inspection_image_bytes_available"] is True
        assert ev["real_image_comparison_completed"] is True
    finally:
        app.dependency_overrides.pop(get_current_user, None)


# ── A failed processing-store surfaces its reason in the upload response ───────
def test_upload_surfaces_processing_error(monkeypatch):
    import app.services.inspection_image_processing_service as svc

    def _boom(*a, **k):
        raise RuntimeError("relation \"inspection_processing_images\" does not exist")

    monkeypatch.setattr(svc, "store_processing_image", _boom)
    up = client.post("/api/inspections/upload-images",
                     files={"images": ("x.png", _png(1301), "image/png")},
                     params={"instrument_type": "rigid_scope"}, headers=_hdr())
    assert up.status_code == 200
    img = up.json()["images"][0]
    assert img["processing_available"] is False
    assert "does not exist" in img.get("processing_error", "")
