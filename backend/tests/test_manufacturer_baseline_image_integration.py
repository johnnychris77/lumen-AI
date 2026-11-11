"""Manufacturer baseline image registration + real inspection comparison.

Covers the two defects fixed on branch
``fix/manufacturer-baseline-image-integration``:

  1. Creating a manufacturer baseline with a photo now genuinely registers the
     reference-image BYTES through the governed pipeline (retain -> LCID ->
     BaselineImageLink), instead of recording only a SHA-256.
  2. The inspection comparator now passes manufacturer/model/anatomy/view into
     the baseline-image resolution hierarchy, so an approved manufacturer
     reference image is actually matched and compared.

Every test runs with the deterministic placeholder scorer OFF (production
default). A real baseline-image comparison is proven to be independent of the
trained-vision-model status: the model stays AI_UNAVAILABLE while the baseline
visual-similarity comparison genuinely completes.
"""
import hashlib
import io

import pytest
from PIL import Image

from app.db.session import SessionLocal
from app.models.baseline_image_library import (
    STATE_ACTIVE,
    STATE_PENDING_REVIEW,
    BaselineImageLink,
    COMPATIBLE,
    INCOMPATIBLE_ANATOMY_ZONE,
    INCOMPATIBLE_INSTRUMENT,
    INCOMPATIBLE_VIEW,
    BASELINE_NOT_ACTIVE,
    NO_APPROVED_BASELINE,
)
from app.models.baseline_library import BaselineLibraryEntry
from app.models.retained_image import RetainedImage
from app.services import baseline_image_library_service as bil
from app.services import baseline_image_registration_service as bir
from app.services.baseline_comparison_scoring_service import analyze_inspection
from app.services.baseline_compatibility_service import (
    CandidateContext,
    check_compatibility,
    resolve_baseline_image,
)


def _texture_png(seed: int = 1, size=(256, 256)) -> bytes:
    """A decodable, well-exposed, textured image that passes the quality gate
    (a solid colour would grade POOR and fail activation)."""
    rnd = __import__("random").Random(seed)
    raw = bytes(rnd.getrandbits(8) for _ in range(size[0] * size[1] * 3))
    img = Image.frombytes("RGB", size, raw)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _mfr(itype: str) -> str:
    return f"Mfr_{itype}"


def _model(itype: str) -> str:
    return f"Model_{itype}"


def _seed_entry(db, *, instrument_type, manufacturer=None, model=None) -> BaselineLibraryEntry:
    # Unique manufacturer/model per instrument type: level-2 resolution keys on
    # manufacturer/model/anatomy (not instrument_family), so distinct values keep
    # each test hermetic and mirror real distinct manufacturer baselines.
    manufacturer = manufacturer or _mfr(instrument_type)
    model = model or _model(instrument_type)
    db.query(BaselineLibraryEntry).filter(
        BaselineLibraryEntry.instrument_category == instrument_type
    ).delete()
    entry = BaselineLibraryEntry(
        udi=f"udi-{instrument_type}", instrument_category=instrument_type,
        manufacturer_name=manufacturer, model_name=model, baseline_type="manufacturer",
        baseline_version="1.0", approval_status="approved", approved_by="seed",
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def _register_reference(db, *, entry, image_bytes, tenant="default-tenant", anatomy_zone="", inspection_view=""):
    return bir.register_manufacturer_reference_image(
        db, tenant_id=tenant, baseline_library_entry_id=entry.id,
        image_bytes=image_bytes, content_type="image/png", uploaded_by="spd@x",
        source_organization="Karl Storz GmbH",
        source_reference="PO-2024-0199 / vendor-portal submission 55",
        usage_rights_attested=True, no_phi_attested=True,
        anatomy_zone=anatomy_zone, inspection_view=inspection_view,
    )


def _approve_and_activate(db, *, link, tenant="default-tenant"):
    bil.review_baseline_image(
        db, link=link, reviewer="rev@x", reviewer_role="clinical_reviewer",
        decision="approve", rationale="Manufacturer reference verified against PO.",
        source_verification="PO-2024-0199", anatomy_compatibility_confirmed=True,
        image_quality_assessment="good",
    )
    return bil.activate_baseline_image(db, link=link, actor="adm@x", actor_role="admin")


# ── 1. A manufacturer baseline RECORD can exist without a usable image ────────
def test_metadata_baseline_without_reference_image():
    db = SessionLocal()
    try:
        itype = "mbi_meta_only"
        _seed_entry(db, instrument_type=itype)
        analysis = analyze_inspection(
            db, instrument_type=itype, tenant_id="default-tenant", has_image=True,
            image_sha256="a" * 64, image_bytes=_texture_png(), demo_scoring=False,
        )
        ev = analysis["baseline_evidence"]
        assert ev["manufacturer_baseline_metadata_found"] is True
        assert ev["baseline_image_registered"] is False
        assert ev["baseline_image_active"] is False
        assert ev["real_image_comparison_completed"] is False
        assert analysis["ai_analysis"]["baseline_image_similarity"]["similarity"] is None
    finally:
        db.close()


# ── 2. A hash-only upload is NOT an image-backed comparison ───────────────────
def test_hash_only_upload_is_not_image_backed():
    db = SessionLocal()
    try:
        itype = "mbi_hash_only"
        entry = _seed_entry(db, instrument_type=itype)
        # Simulate the legacy path: a hash recorded, but no governed image link.
        assert (
            db.query(BaselineImageLink)
            .filter(BaselineImageLink.baseline_library_entry_id == entry.id)
            .first()
            is None
        )
        analysis = analyze_inspection(
            db, instrument_type=itype, tenant_id="default-tenant", has_image=True,
            image_sha256="b" * 64, image_bytes=_texture_png(), demo_scoring=False,
        )
        assert analysis["baseline_evidence"]["baseline_image_registered"] is False
        assert analysis["baseline_evidence"]["real_image_comparison_completed"] is False
    finally:
        db.close()


# ── 3. A retained, registered, approved, ACTIVE image resolves ────────────────
def test_active_reference_image_resolves():
    db = SessionLocal()
    try:
        itype = "mbi_active"
        entry = _seed_entry(db, instrument_type=itype)
        reg = _register_reference(db, entry=entry, image_bytes=_texture_png(3))
        assert reg["lifecycle_status"] == STATE_PENDING_REVIEW  # never auto-ACTIVE
        link = _approve_and_activate(db, link=reg["link"])
        assert link.lifecycle_status == STATE_ACTIVE

        res = resolve_baseline_image(db, candidate=CandidateContext(
            tenant_id="default-tenant", instrument_family=itype,
            manufacturer=_mfr(itype), model_name=_model(itype), anatomy_zone="whole_instrument",
        ))
        assert res.baseline_image_link_id == link.id
    finally:
        db.close()


# ── 4. Manufacturer/model/anatomy/view compatibility is enforced ──────────────
def test_compatibility_enforced():
    db = SessionLocal()
    try:
        itype = "mbi_compat"
        entry = _seed_entry(db, instrument_type=itype)
        # Register with a SPECIFIC zone/view so zone/view incompatibility is
        # testable (a whole_instrument overview is compatible with any zone).
        reg = _register_reference(db, entry=entry, image_bytes=_texture_png(4),
                                  anatomy_zone="jaw", inspection_view="closed")
        link = _approve_and_activate(db, link=reg["link"])

        base = dict(tenant_id="default-tenant", instrument_family=itype,
                    manufacturer=_mfr(itype), model_name=_model(itype),
                    anatomy_zone="jaw", inspection_view="closed")
        assert check_compatibility(candidate=CandidateContext(**base), baseline_link=link) == COMPATIBLE
        assert check_compatibility(
            candidate=CandidateContext(**{**base, "manufacturer": "Olympus"}), baseline_link=link
        ) == INCOMPATIBLE_INSTRUMENT
        assert check_compatibility(
            candidate=CandidateContext(**{**base, "anatomy_zone": "distal_tip"}), baseline_link=link
        ) == INCOMPATIBLE_ANATOMY_ZONE
        assert check_compatibility(
            candidate=CandidateContext(**{**base, "inspection_view": "side"}), baseline_link=link
        ) == INCOMPATIBLE_VIEW
    finally:
        db.close()


# ── 5. Cross-tenant reference images remain inaccessible ──────────────────────
def test_cross_tenant_isolation():
    db = SessionLocal()
    try:
        itype = "mbi_tenant"
        entry = _seed_entry(db, instrument_type=itype)
        reg = _register_reference(db, entry=entry, image_bytes=_texture_png(5), tenant="tenant-A")
        link = _approve_and_activate(db, link=reg["link"], tenant="tenant-A")

        # Another tenant must not resolve or be compatible with tenant-A's image.
        res = resolve_baseline_image(db, candidate=CandidateContext(
            tenant_id="tenant-B", instrument_family=itype, manufacturer=_mfr(itype),
            model_name=_model(itype), anatomy_zone="whole_instrument",
        ))
        assert res.baseline_image_link_id is None
        assert check_compatibility(
            candidate=CandidateContext(tenant_id="tenant-B", instrument_family=itype),
            baseline_link=link,
        ) == NO_APPROVED_BASELINE
    finally:
        db.close()


# ── 6. Inactive/rejected images cannot be used ────────────────────────────────
def test_inactive_image_not_used():
    db = SessionLocal()
    try:
        itype = "mbi_inactive"
        entry = _seed_entry(db, instrument_type=itype)
        reg = _register_reference(db, entry=entry, image_bytes=_texture_png(6))
        link = reg["link"]  # PENDING_REVIEW, never activated
        assert link.lifecycle_status == STATE_PENDING_REVIEW

        res = resolve_baseline_image(db, candidate=CandidateContext(
            tenant_id="default-tenant", instrument_family=itype, manufacturer=_mfr(itype),
            model_name=_model(itype), anatomy_zone="whole_instrument",
        ))
        assert res.baseline_image_link_id is None
        assert check_compatibility(
            candidate=CandidateContext(tenant_id="default-tenant", instrument_family=itype),
            baseline_link=link,
        ) == BASELINE_NOT_ACTIVE
    finally:
        db.close()


# ── 7. Hash-integrity failures prevent comparison ────────────────────────────
def test_hash_integrity_failure_blocks_comparison():
    db = SessionLocal()
    try:
        itype = "mbi_integrity"
        entry = _seed_entry(db, instrument_type=itype)
        reg = _register_reference(db, entry=entry, image_bytes=_texture_png(7))
        _approve_and_activate(db, link=reg["link"])

        # Corrupt the stored bytes WITHOUT updating the registered hash.
        row = db.query(RetainedImage).filter(RetainedImage.id == reg["retained_image_id"]).first()
        row.image_bytes = _texture_png(999)  # different bytes, same registered sha256 column
        db.commit()

        with pytest.raises(bil.ImageIdentityMismatchError):
            link = db.query(BaselineImageLink).filter(BaselineImageLink.id == reg["link"].id).first()
            bil.load_and_verify_baseline_bytes(db, link=link, accessed_by="test")
    finally:
        db.close()


# ── 8. Compatible bytes produce a traceable visual-similarity result ──────────
def test_real_comparison_produces_traceable_similarity():
    db = SessionLocal()
    try:
        itype = "mbi_real"
        img = _texture_png(8)
        entry = _seed_entry(db, instrument_type=itype)
        reg = _register_reference(db, entry=entry, image_bytes=img)
        link = _approve_and_activate(db, link=reg["link"])

        analysis = analyze_inspection(
            db, instrument_type=itype, tenant_id="default-tenant", has_image=True,
            image_sha256=hashlib.sha256(img).hexdigest(), image_bytes=img,
            instrument_manufacturer=_mfr(itype), instrument_model=_model(itype), demo_scoring=False,
        )
        sim = analysis["ai_analysis"]["baseline_image_similarity"]
        assert sim["is_image_comparison"] is True
        assert sim["similarity"] is not None
        assert sim["baseline_id"] == link.id
        assert sim["method"]
        assert analysis["baseline_evidence"]["real_image_comparison_completed"] is True
    finally:
        db.close()


# ── 9. No inspection image bytes → unavailable comparison status ──────────────
def test_no_inspection_bytes_unavailable_comparison():
    db = SessionLocal()
    try:
        itype = "mbi_nobytes"
        entry = _seed_entry(db, instrument_type=itype)
        reg = _register_reference(db, entry=entry, image_bytes=_texture_png(9))
        _approve_and_activate(db, link=reg["link"])

        analysis = analyze_inspection(
            db, instrument_type=itype, tenant_id="default-tenant", has_image=True,
            image_sha256="c" * 64, image_bytes=None,
            instrument_manufacturer=_mfr(itype), instrument_model=_model(itype), demo_scoring=False,
        )
        ev = analysis["baseline_evidence"]
        assert ev["inspection_image_bytes_available"] is False
        assert ev["real_image_comparison_completed"] is False
        assert analysis["ai_analysis"]["baseline_image_similarity"]["similarity"] is None
    finally:
        db.close()


# ── 10. No trained model → AI_UNAVAILABLE even when the comparison succeeds ────
def test_comparison_success_still_ai_unavailable():
    db = SessionLocal()
    try:
        itype = "mbi_separation"
        img = _texture_png(10)
        entry = _seed_entry(db, instrument_type=itype)
        reg = _register_reference(db, entry=entry, image_bytes=img)
        _approve_and_activate(db, link=reg["link"])

        analysis = analyze_inspection(
            db, instrument_type=itype, tenant_id="default-tenant", has_image=True,
            image_sha256=hashlib.sha256(img).hexdigest(), image_bytes=img,
            instrument_manufacturer=_mfr(itype), instrument_model=_model(itype), demo_scoring=False,
        )
        ev = analysis["baseline_evidence"]
        # Baseline image comparison genuinely ran …
        assert ev["real_image_comparison_completed"] is True
        # … while the trained vision model is correctly unavailable.
        assert ev["trained_vision_model_available"] is False
        assert analysis["ai_analysis"]["status"] == "AI_UNAVAILABLE"
        assert analysis["analysis_status"] == "ai_unavailable"
    finally:
        db.close()


# ── 11. No fabricated finding or clinical clearance ───────────────────────────
def test_no_fabricated_finding_or_clearance():
    db = SessionLocal()
    try:
        itype = "mbi_nofab"
        img = _texture_png(11)
        entry = _seed_entry(db, instrument_type=itype)
        reg = _register_reference(db, entry=entry, image_bytes=img)
        _approve_and_activate(db, link=reg["link"])

        analysis = analyze_inspection(
            db, instrument_type=itype, tenant_id="default-tenant", has_image=True,
            image_sha256=hashlib.sha256(img).hexdigest(), image_bytes=img,
            instrument_manufacturer=_mfr(itype), instrument_model=_model(itype), demo_scoring=False,
        )
        assert analysis["predicted_findings"] == []
        assert analysis["inspection_score"] is None
        assert analysis["ai_analysis"]["authorizes_release"] is False
        assert analysis["human_review_required"] is True
    finally:
        db.close()


# ── 12. No cross-manufacturer false match (Codex P1) ──────────────────────────
def test_no_cross_manufacturer_false_match():
    db = SessionLocal()
    try:
        itype = "mbi_xmfr"
        img = _texture_png(12)
        # One ACTIVE manufacturer-A reference image for this instrument type.
        entry = _seed_entry(db, instrument_type=itype, manufacturer="Alpha Surgical", model="A-1")
        reg = _register_reference(db, entry=entry, image_bytes=img)
        _approve_and_activate(db, link=reg["link"])

        # An inspection of a DIFFERENT manufacturer's instrument of the same type
        # must never resolve or compare against Alpha's reference image.
        analysis = analyze_inspection(
            db, instrument_type=itype, tenant_id="default-tenant", has_image=True,
            image_sha256=hashlib.sha256(img).hexdigest(), image_bytes=img,
            instrument_manufacturer="Beta Medical", instrument_model="B-9", demo_scoring=False,
        )
        ev = analysis["baseline_evidence"]
        assert ev["real_image_comparison_completed"] is False
        assert analysis["ai_analysis"]["baseline_image_similarity"] is None or \
            analysis["ai_analysis"]["baseline_image_similarity"]["similarity"] is None

        # The correct manufacturer DOES resolve and compare.
        ok = analyze_inspection(
            db, instrument_type=itype, tenant_id="default-tenant", has_image=True,
            image_sha256=hashlib.sha256(img).hexdigest(), image_bytes=img,
            instrument_manufacturer="Alpha Surgical", instrument_model="A-1", demo_scoring=False,
        )
        assert ok["baseline_evidence"]["real_image_comparison_completed"] is True
    finally:
        db.close()


# ── 13. An overview reference resolves a zone-tagged inspection (Codex P1) ─────
def test_overview_reference_matches_zone_tagged_inspection():
    db = SessionLocal()
    try:
        itype = "mbi_overview"
        img = _texture_png(13)
        entry = _seed_entry(db, instrument_type=itype)  # registered whole_instrument/overview
        reg = _register_reference(db, entry=entry, image_bytes=img)
        _approve_and_activate(db, link=reg["link"])

        # The technician tags a specific anatomy zone/view on the inspection image.
        analysis = analyze_inspection(
            db, instrument_type=itype, tenant_id="default-tenant", has_image=True,
            image_sha256=hashlib.sha256(img).hexdigest(), image_bytes=img,
            instrument_manufacturer=_mfr(itype), instrument_model=_model(itype),
            image_view_tags=[{"anatomy_zone": "jaw", "image_view": "jaw"}], demo_scoring=False,
        )
        # The whole-instrument overview reference still resolves + compares.
        assert analysis["baseline_evidence"]["real_image_comparison_completed"] is True
        assert analysis["ai_analysis"]["baseline_image_similarity"]["similarity"] is not None
    finally:
        db.close()
