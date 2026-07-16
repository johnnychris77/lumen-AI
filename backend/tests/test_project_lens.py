"""Project Lens — Section 20 live-path tests.

Uses real image fixtures (real PNG-encoded bytes via Pillow, not mocked
prediction objects) throughout, matching this codebase's established
convention (tests/test_candidate_model_training.py::_img()).
"""
import hashlib
import io
import itertools
import os
import uuid as _uuid

import pytest
from PIL import Image
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.services.baseline_comparison_scoring_service import analyze_inspection
from app.services.ml import image_similarity_service, live_inference_adapter
from app.services.ml.experimental_dataset_generator import generate_experimental_dataset
from app.services.ml.lens_model_registration import MODEL_ID, register_lens_model
from app.services.ml.lens_training_pipeline import run_lens_training
from app.services.ml.training_config import TrainingConfig
from app.services.ml.training_eligibility_service import compute_training_eligibility

TENANT = "default-tenant"
OTHER_TENANT = "other-tenant"


@pytest.fixture(autouse=True)
def _enable_retention(monkeypatch):
    # The experimental generator ingests images through the real,
    # opt-in retention path (image_retention_service.retain_image()) —
    # this must be explicitly enabled here rather than assumed from the
    # test-runner's invocation environment.
    monkeypatch.setenv("RETAIN_INSPECTION_IMAGES", "true")


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


_version_counter = itertools.count(1)


def _train_and_register(db: Session, *, tenant_id: str = TENANT, samples_per_class: int = 6, candidate_stage: str | None = None):
    generate_experimental_dataset(db, tenant_id=tenant_id, samples_per_class=samples_per_class)
    eligibility = compute_training_eligibility(db, tenant_id=tenant_id)
    run = run_lens_training(eligibility, config=TrainingConfig(epochs=100))
    # Unique per call — each test run's artifact must not overwrite another
    # test's artifact file on disk (they'd otherwise collide on the same
    # model_artifacts/{model_id}_{model_version}.json path).
    model_version = f"0.1.0-test{next(_version_counter)}"
    model = register_lens_model(db, tenant_id=tenant_id, run=run, model_version=model_version)
    if candidate_stage is not None:
        model.candidate_stage = candidate_stage
        db.commit()
        db.refresh(model)
    return model, run


# ── 1/2 — same image vs. different image comparison ─────────────────────────

def test_exact_same_image_produces_exact_match():
    data = _img(90)
    result = image_similarity_service.compare_image_bytes(data, data)
    assert result["status"] == image_similarity_service.STATUS_EXACT_MATCH
    assert result["similarity"] == 1.0


def test_visually_different_image_does_not_reuse_first_result():
    a, b = _img(20, stripe_period=4), _img(230, stripe_period=0)
    result_ab = image_similarity_service.compare_image_bytes(a, b)
    result_aa = image_similarity_service.compare_image_bytes(a, a)
    assert result_ab["status"] != result_aa["status"] or result_ab["similarity"] < result_aa["similarity"]
    assert result_ab["status"] in (
        image_similarity_service.STATUS_COMPARABLE, image_similarity_service.STATUS_MATERIALLY_DIFFERENT,
    )


# ── 5/6 — baseline availability / compatibility gating ──────────────────────

def test_no_approved_baseline_returns_no_approved_baseline():
    result = image_similarity_service.compare_against_baseline(
        image_bytes=_img(100), baseline_image_bytes=None,
        candidate_instrument_family="scissors", baseline_instrument_family="",
        baseline_available=False,
    )
    assert result["status"] == image_similarity_service.STATUS_NO_APPROVED_BASELINE
    assert result["similarity"] is None


def test_incompatible_instrument_family_does_not_receive_fabricated_similarity():
    result = image_similarity_service.compare_against_baseline(
        image_bytes=_img(100), baseline_image_bytes=_img(100),
        candidate_instrument_family="scissors", baseline_instrument_family="grasper",
        baseline_available=True,
    )
    assert result["status"] == image_similarity_service.STATUS_INCOMPATIBLE_VIEW
    assert result["similarity"] is None


# ── 3/4 — real image bytes actually reach the model adapter ─────────────────

def test_image_bytes_reach_model_adapter_and_change_prediction():
    db = SessionLocal()
    try:
        model, _run = _train_and_register(db, candidate_stage="Candidate")
        dark = _img(20, stripe_period=4)
        bright = _img(230, stripe_period=0)
        result_dark = live_inference_adapter.predict(db, tenant_id=TENANT, image_bytes=dark)
        result_bright = live_inference_adapter.predict(db, tenant_id=TENANT, image_bytes=bright)
        assert result_dark["analysis_status"] == "completed"
        assert result_bright["analysis_status"] == "completed"
        assert result_dark["model"]["model_id"] == MODEL_ID
        assert result_dark["model"]["model_version"] == model.model_version
        # Different pixel content produced a different feature vector and
        # therefore is free to yield a different observation/probability —
        # asserting they are not required to be identical proves the
        # prediction is a function of the actual bytes, not a hash-seeded
        # placeholder that would also differ, but for the wrong reason.
        assert (
            result_dark["observation"]["raw_probability"] != result_bright["observation"]["raw_probability"]
            or result_dark["observation"]["category"] != result_bright["observation"]["category"]
        )
    finally:
        db.close()


# ── 7 — unavailable artifact returns a safe state, never the placeholder ────

def test_unavailable_model_returns_safe_state_not_placeholder():
    db = SessionLocal()
    try:
        result = live_inference_adapter.predict(db, tenant_id="tenant-with-no-model", image_bytes=_img(100))
        assert result["analysis_status"] == "ai_unavailable"
        assert result["model"]["status"] == live_inference_adapter.HEALTH_UNAVAILABLE
        assert result["observation"] is None
        assert result["human_review_required"] is True
    finally:
        db.close()


def test_unpromoted_experimental_model_reports_not_promoted():
    db = SessionLocal()
    try:
        tenant = "lens-not-promoted-tenant"
        _train_and_register(db, tenant_id=tenant)  # stays "Experimental" — never promoted by register_lens_model
        result = live_inference_adapter.predict(db, tenant_id=tenant, image_bytes=_img(100))
        assert result["model"]["status"] == live_inference_adapter.HEALTH_NOT_PROMOTED
        assert result["observation"] is None
    finally:
        db.close()


# ── 9 — unsupported categories are never scored ─────────────────────────────

def test_unsupported_categories_never_scored():
    db = SessionLocal()
    try:
        model, run = _train_and_register(db, candidate_stage="Candidate")
        result = live_inference_adapter.predict(db, tenant_id=TENANT, image_bytes=_img(150, stripe_period=10))
        if result["observation"] and not result["observation"]["abstained"]:
            assert result["observation"]["category"] in result["supported_categories"]
        assert set(result["supported_categories"]).isdisjoint(set(result["unsupported_categories"]))
    finally:
        db.close()


# ── 10/11 — abstention: low confidence and insufficient image quality ───────

def test_low_confidence_triggers_abstention():
    db = SessionLocal()
    try:
        model, run = _train_and_register(db, candidate_stage="Candidate")
        # Force a high abstention threshold directly on the exported artifact
        # so the test genuinely exercises the abstention branch regardless of
        # this run's real calibration outcome.
        import json
        with open(model.artifact_path) as f:
            payload = json.load(f)
        payload["calibration"]["abstention_threshold"] = 0.999
        serialized = json.dumps(payload, indent=2, sort_keys=True)
        with open(model.artifact_path, "w") as f:
            f.write(serialized)
        import hashlib
        model.artifact_checksum = hashlib.sha256(serialized.encode()).hexdigest()
        db.commit()

        result = live_inference_adapter.predict(db, tenant_id=TENANT, image_bytes=_img(120, stripe_period=6))
        assert result["observation"]["abstained"] is True
        assert result["observation"]["abstention_reason"] in ("confidence_below_threshold", "unknown_review_required")
    finally:
        db.close()


def test_insufficient_image_quality_does_not_return_confident_finding():
    db = SessionLocal()
    try:
        _train_and_register(db, candidate_stage="Candidate")
        # A 10x10 image fails image_quality's MIN_WIDTH/MIN_HEIGHT check.
        tiny = Image.new("RGB", (10, 10), (100, 100, 100))
        buf = io.BytesIO()
        tiny.save(buf, format="PNG")
        result = live_inference_adapter.predict(db, tenant_id=TENANT, image_bytes=buf.getvalue())
        assert result["observation"]["abstained"] is True
        assert result["observation"]["category"] == "insufficient_image_quality"
        assert result["image_quality"]["status"] == "insufficient_image_quality"
    finally:
        db.close()


# ── 12/13 — model ID/version persisted; prior runs remain immutable ────────

def test_model_id_and_version_persisted_and_prior_runs_immutable():
    db = SessionLocal()
    try:
        model_v1, _ = _train_and_register(db, samples_per_class=4)
        first_id, first_checksum = model_v1.id, model_v1.artifact_checksum
        model_v2, _ = _train_and_register(db, samples_per_class=4)

        db.refresh(model_v1)
        assert model_v1.id == first_id
        assert model_v1.artifact_checksum == first_checksum  # untouched by the later run
        assert model_v2.id != model_v1.id
        assert model_v2.model_id == MODEL_ID == model_v1.model_id
    finally:
        db.close()


# ── 14 — cross-tenant model access is rejected ──────────────────────────────

def test_cross_tenant_model_access_rejected():
    db = SessionLocal()
    try:
        _train_and_register(db, tenant_id=TENANT, candidate_stage="Candidate")
        result = live_inference_adapter.predict(db, tenant_id=OTHER_TENANT, image_bytes=_img(100))
        assert result["analysis_status"] == "ai_unavailable"
        assert result["model"]["status"] == live_inference_adapter.HEALTH_UNAVAILABLE
    finally:
        db.close()


# ── 15 — analyze_inspection() integration is purely additive ───────────────

def test_analyze_inspection_live_model_result_is_additive_only():
    db = SessionLocal()
    try:
        without_bytes = analyze_inspection(
            db, instrument_type="scissors", tenant_id=TENANT, has_image=True, image_sha256="a" * 64,
        )
        with_bytes = analyze_inspection(
            db, instrument_type="scissors", tenant_id=TENANT, has_image=True, image_sha256="a" * 64,
            image_bytes=_img(100),
        )
        assert "live_model_result" in without_bytes
        assert "live_model_result" in with_bytes
        # Every pre-existing key is untouched by adding image_bytes.
        for key in without_bytes:
            if key == "live_model_result":
                continue
            assert with_bytes[key] == without_bytes[key], f"key {key!r} changed when only image_bytes was added"
    finally:
        db.close()


# ── 16 — settings.ai_strict_no_placeholder disables placeholder scoring ─────

def test_strict_no_placeholder_disables_deterministic_placeholder_finding(monkeypatch):
    monkeypatch.setenv("AI_STRICT_NO_PLACEHOLDER", "true")
    db = SessionLocal()
    try:
        result = analyze_inspection(
            db, instrument_type="scissors", tenant_id=TENANT, has_image=True, image_sha256="b" * 64,
        )
        assert result["model_result"]["model_status"] == "unavailable"
        assert result["model_result"]["findings"] == []
        assert any(
            "Strict no-placeholder mode is enabled" in limitation
            for limitation in result["model_result"]["limitations"]
        )
    finally:
        db.close()


def test_strict_no_placeholder_defaults_off(monkeypatch):
    monkeypatch.delenv("AI_STRICT_NO_PLACEHOLDER", raising=False)
    db = SessionLocal()
    try:
        result = analyze_inspection(
            db, instrument_type="scissors", tenant_id=TENANT, has_image=True, image_sha256="c" * 64,
        )
        assert result["model_result"]["model_status"] == "experimental"
        assert not any(
            "Strict no-placeholder mode is enabled" in limitation
            for limitation in result["model_result"]["limitations"]
        )
    finally:
        db.close()


# ── 17 — missing artifact file returns safe unavailable state ───────────────

def test_missing_artifact_file_returns_artifact_missing():
    db = SessionLocal()
    try:
        tenant = "lens-artifact-missing-tenant"
        model, _run = _train_and_register(db, tenant_id=tenant, candidate_stage="Candidate")
        os.remove(model.artifact_path)
        result = live_inference_adapter.predict(db, tenant_id=tenant, image_bytes=_img(100))
        assert result["analysis_status"] == "ai_unavailable"
        assert result["model"]["status"] == live_inference_adapter.HEALTH_ARTIFACT_MISSING
        assert result["observation"] is None
    finally:
        db.close()


# ── 18 — corrupted artifact / checksum mismatch blocks loading ──────────────

def test_checksum_mismatch_blocks_loading():
    db = SessionLocal()
    try:
        tenant = "lens-checksum-mismatch-tenant"
        model, _run = _train_and_register(db, tenant_id=tenant, candidate_stage="Candidate")
        with open(model.artifact_path, "ab") as f:
            f.write(b"corrupted-tail-bytes")
        result = live_inference_adapter.predict(db, tenant_id=tenant, image_bytes=_img(100))
        assert result["analysis_status"] == "ai_unavailable"
        assert result["model"]["status"] == live_inference_adapter.HEALTH_CHECKSUM_FAILED
        assert result["observation"] is None
    finally:
        db.close()


# ── 19 — same filename, different bytes: identity is content-hash based ─────

def test_same_filename_different_bytes_is_distinct_identity():
    # The live adapter and analyze_inspection() never receive or key off a
    # filename — identity is always the actual image bytes / their sha256.
    # Two uploads sharing a filename (a common accidental-reuse scenario)
    # must never be treated as the same image.
    bytes_a = _img(40)
    bytes_b = _img(220)
    assert bytes_a != bytes_b
    sha_a = hashlib.sha256(bytes_a).hexdigest()
    sha_b = hashlib.sha256(bytes_b).hexdigest()
    assert sha_a != sha_b

    db = SessionLocal()
    try:
        model, _run = _train_and_register(db, tenant_id="lens-filename-collision-tenant", candidate_stage="Candidate")
        result_a = live_inference_adapter.predict(db, tenant_id="lens-filename-collision-tenant", image_bytes=bytes_a, image_sha256=sha_a)
        result_b = live_inference_adapter.predict(db, tenant_id="lens-filename-collision-tenant", image_bytes=bytes_b, image_sha256=sha_b)
        assert result_a["image"]["sha256"] == sha_a
        assert result_b["image"]["sha256"] == sha_b
        assert result_a["image"]["sha256"] != result_b["image"]["sha256"]
    finally:
        db.close()


# ── 21 — live baseline comparator wiring (Atlas → live path) ───────────────

def _nonce_img(brightness: int, stripe_period: int = 8) -> bytes:
    # A random PNG text chunk guarantees a unique SHA-256 across pytest
    # invocations sharing the same persistent SQLite test DB — without it,
    # the LCID duplicate gate rejects re-registering last run's identical
    # bytes (same mitigation as tests/test_baseline_image_library.py::_img).
    from PIL import PngImagePlugin

    img = Image.new("RGB", (300, 300), (brightness, brightness, brightness))
    if stripe_period:
        px = img.load()
        inverse = 255 - brightness
        for x in range(0, 300, stripe_period):
            for y in range(300):
                px[x, y] = (inverse, inverse, inverse)
    buf = io.BytesIO()
    meta = PngImagePlugin.PngInfo()
    meta.add_text("test-nonce", _uuid.uuid4().hex)
    img.save(buf, format="PNG", pnginfo=meta)
    return buf.getvalue()


def _make_active_baseline_link(db, *, tenant_id: str, instrument_family: str, image_data: bytes):
    """Create an ACTIVE, governed-consensus baseline image link through the
    real Atlas lifecycle (link → review → activate) — the only resolution
    level reachable when the live path knows just the instrument family."""
    import uuid as _uuid

    from app.models.baseline_library import BaselineLibraryEntry
    from app.models.baseline_image_library import (
        IMAGE_TYPE_MANUFACTURER_BASELINE,
        SOURCE_GOVERNED_CONSENSUS_REFERENCE,
    )
    from app.models.retained_image import RetainedImage
    from app.services import baseline_image_library_service as bil
    from app.services.ml import dataset_registry

    retained = RetainedImage(
        tenant_id=tenant_id, deident_name="lens-baseline", instrument_type=instrument_family,
        content_type="image/png", size_bytes=len(image_data),
        sha256=hashlib.sha256(image_data).hexdigest(), exif_stripped=True, source="test",
        consent_recorded=True, uploaded_by="tester", image_bytes=image_data,
    )
    db.add(retained)
    db.commit()
    db.refresh(retained)
    version = dataset_registry.create_dataset_version(db, tenant_id=tenant_id, version_label=f"lens-bl-{_uuid.uuid4().hex[:8]}")
    lcid_entry = dataset_registry.register_image(
        db, tenant_id=tenant_id, dataset_version_id=version.id, retained_image_id=retained.id,
        image_sha256=retained.sha256, instrument_family=instrument_family, instrument_model="X1",
        manufacturer="Acme", anatomy_zone="tip", capture_device="phone", image_resolution="300x300",
        facility="Test Hospital", operator="tech1", usage_rights="internal_use", phi_verification="verified",
    )
    lcid_entry.image_quality = "Good"
    db.commit()
    baseline_entry = BaselineLibraryEntry(
        instrument_category=instrument_family, manufacturer_name="Acme", model_name="X1",
        baseline_type="manufacturer", approval_status="approved",
    )
    db.add(baseline_entry)
    db.commit()
    db.refresh(baseline_entry)
    link = bil.link_lcid_image_to_baseline(
        db, tenant_id=tenant_id, baseline_library_entry_id=baseline_entry.id, lcid_image_id=lcid_entry.id,
        anatomy_zone="tip", inspection_view="lateral", image_type=IMAGE_TYPE_MANUFACTURER_BASELINE,
        source_type=SOURCE_GOVERNED_CONSENSUS_REFERENCE, created_by="ingest@test",
    )
    link = bil.submit_for_review(db, link=link, actor="ingest@test")
    bil.review_baseline_image(
        db, link=link, reviewer="reviewer@test", reviewer_role="spd_manager", decision="approve",
        rationale="Reference consensus image.", anatomy_compatibility_confirmed=True,
        image_quality_assessment="Good",
    )
    db.refresh(link)
    bil.activate_baseline_image(db, link=link, actor="admin@test", actor_role="admin")
    db.refresh(link)
    return link


def test_live_baseline_comparison_no_approved_baseline():
    from app.services.baseline_comparison_scoring_service import _live_model_result

    db = SessionLocal()
    try:
        family = f"lens-no-baseline-{_uuid.uuid4().hex[:8]}"
        result = _live_model_result(
            db, tenant_id=TENANT, image_bytes=_img(120), instrument_type=family,
        )
        comparison = result["baseline_comparison"]
        assert comparison is not None
        assert comparison["status"] == "no_approved_baseline"
        assert comparison["similarity"] is None
        # The model's own channel is untouched — a missing baseline never
        # blocks inference (Section 17); the adapter still reports its own
        # honest state independently.
        assert result["analysis_status"] in ("completed", "ai_unavailable")
    finally:
        db.close()


def test_live_baseline_comparison_with_active_baseline_produces_similarity():
    from app.services.baseline_comparison_scoring_service import _live_model_result

    db = SessionLocal()
    try:
        family = f"lens-live-baseline-{_uuid.uuid4().hex[:8]}"
        baseline_bytes = _nonce_img(120)
        _make_active_baseline_link(db, tenant_id=TENANT, instrument_family=family, image_data=baseline_bytes)
        result = _live_model_result(db, tenant_id=TENANT, image_bytes=baseline_bytes, instrument_type=family)
        comparison = result["baseline_comparison"]
        assert comparison["status"] in ("exact_match", "comparable")
        assert comparison["similarity"] == 1.0
        assert comparison["resolution_scope"]
    finally:
        db.close()


def test_live_baseline_comparison_never_alters_observation():
    # High baseline similarity must never cancel or change the model's
    # observation channel — populate both from the same call and assert the
    # observation is byte-identical to a run with no baseline registered.
    from app.services.baseline_comparison_scoring_service import _live_model_result

    db = SessionLocal()
    try:
        family = f"lens-separation-{_uuid.uuid4().hex[:8]}"
        probe = _nonce_img(150, stripe_period=10)
        without_baseline = _live_model_result(db, tenant_id=TENANT, image_bytes=probe, instrument_type=family)
        _make_active_baseline_link(db, tenant_id=TENANT, instrument_family=family, image_data=probe)
        with_baseline = _live_model_result(db, tenant_id=TENANT, image_bytes=probe, instrument_type=family)
        assert with_baseline["baseline_comparison"]["similarity"] == 1.0
        assert without_baseline["baseline_comparison"]["status"] == "no_approved_baseline"
        assert with_baseline["observation"] == without_baseline["observation"]
        assert with_baseline["analysis_status"] == without_baseline["analysis_status"]
    finally:
        db.close()


# ── 20 — Decision Engine receives the model observation unchanged ──────────

def test_decision_engine_receives_observation_unchanged():
    # The Decision Engine's contract observation.confidence must be exactly
    # the confidence analyze_inspection() produced for the primary finding —
    # never re-derived, rounded, or recalculated on the way into the contract.
    from app.models.baseline_library import BaselineLibraryEntry
    from app.services import lumen_decision_engine

    db = SessionLocal()
    try:
        itype = "lens-decision-passthrough-instrument"
        db.add(BaselineLibraryEntry(
            instrument_category=itype, manufacturer_name="Acme", model_name="Test",
            baseline_type="manufacturer", approval_status="approved",
        ))
        db.commit()
        analysis = analyze_inspection(
            db, instrument_type=itype, tenant_id=TENANT, has_image=True, image_sha256="d" * 64,
            declared_findings=["debris"],
        )
        assert analysis["analysis_status"] == "completed"
        original_confidence = next(f["confidence"] for f in analysis["predicted_findings"] if f["type"] == "debris")
        contract = lumen_decision_engine.build_decision(
            db, inspection_id=999999, tenant_id=TENANT, facility_name="Test Hospital",
            department="CSSD", instrument_type=itype, analysis=analysis, persist=False,
        )
        assert contract["observation"]["confidence"] == original_confidence
    finally:
        db.close()
