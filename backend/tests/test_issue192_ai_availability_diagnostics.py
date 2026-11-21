"""Issue #192 — explicit AI_UNAVAILABLE reason codes and baseline-image status.

Negative controls for each failure mode the inspection UI previously collapsed
into "No eligible trained vision model" / "registered but not ACTIVE":

* no model registered, model not promoted, artifact missing, artifact
  checksum failure, eligible model but no image bytes (AI side);
* reference image PENDING_REVIEW, APPROVED-not-activated, ACTIVE but not
  matching the inspection's identity, ACTIVE and resolved, and another
  tenant's ACTIVE image (baseline side, tested separately from the model).

Every case must stay fail-closed: AI_UNAVAILABLE, no score, no confidence,
human review required. Real image bytes and the real registry/adapter are
used throughout; nothing is mocked.
"""
import io
import itertools
import os
import random
import uuid

import pytest
from PIL import Image

from app.db.session import SessionLocal
from app.models.baseline_library import BaselineLibraryEntry
from app.services import ai_availability_diagnostics as diag
from app.services import baseline_image_library_service as bil
from app.services import baseline_image_registration_service as bir
from app.services.baseline_comparison_scoring_service import analyze_inspection
from app.services.ml import live_inference_adapter
from app.services.ml.experimental_dataset_generator import generate_experimental_dataset
from app.services.ml.lens_model_registration import register_lens_model
from app.services.ml.lens_training_pipeline import run_lens_training
from app.services.ml.training_config import TrainingConfig
from app.services.ml.training_eligibility_service import compute_training_eligibility


@pytest.fixture(autouse=True)
def _enable_retention(monkeypatch):
    monkeypatch.setenv("RETAIN_INSPECTION_IMAGES", "true")


_versions = itertools.count(1)


def _tenant(prefix: str) -> str:
    return f"i192-{prefix}-{uuid.uuid4().hex[:8]}"


def _png(seed: int, size=(256, 256)) -> bytes:
    rnd = random.Random(seed)
    raw = bytes(rnd.getrandbits(8) for _ in range(size[0] * size[1] * 3))
    buf = io.BytesIO()
    Image.frombytes("RGB", size, raw).save(buf, format="PNG")
    return buf.getvalue()


def _train(db, tenant_id: str, *, stage: str | None = None):
    """Train the real (synthetic-experimental) Lens pipeline and register it.
    ``stage`` overrides the registry stage ONLY inside this test database, to
    exercise the load path; it is never a promotion decision."""
    generate_experimental_dataset(db, tenant_id=tenant_id, samples_per_class=6)
    run = run_lens_training(compute_training_eligibility(db, tenant_id=tenant_id), config=TrainingConfig(epochs=60))
    model = register_lens_model(db, tenant_id=tenant_id, run=run, model_version=f"0.1.0-i192-{next(_versions)}")
    if stage is not None:
        model.candidate_stage = stage
        db.commit()
        db.refresh(model)
    return model


def _assert_fail_closed(result: dict, code: str) -> None:
    # Either the AI_UNAVAILABLE result or the no-approved-baseline result;
    # both must carry the code and neither may carry an AI-derived value.
    assert result["analysis_status"] in ("ai_unavailable", "supervisor_review_required")
    assert result["ai_analysis"]["status"] == "AI_UNAVAILABLE"
    assert result["ai_analysis"]["manual_inspection_required"] is True
    assert result.get("confidence") is None
    assert result.get("inspection_score") is None
    assert result.get("risk_level") is None
    assert not any(f.get("verified_ai") for f in result.get("predicted_findings") or [])
    assert result["human_review_required"] is True
    reason = result["ai_unavailable_reason"]
    assert reason["code"] == code
    assert result["ai_analysis"]["unavailable_reason"]["code"] == code
    if result["analysis_status"] == "ai_unavailable":
        assert result["pass_fail"] == "AI_UNAVAILABLE"
        assert result["predicted_findings"] == []
        assert result["scoring_explanation"][0] == reason["message"]


def _analyze(db, tenant_id, *, image_bytes, itype="forceps", mfr=None, mdl=None):
    return analyze_inspection(
        db, instrument_type=itype, tenant_id=tenant_id, has_image=True,
        image_sha256="b" * 64, image_bytes=image_bytes,
        instrument_manufacturer=mfr, instrument_model=mdl, demo_scoring=False,
    )


# ── classifier (pure) ───────────────────────────────────────────────────────

@pytest.mark.parametrize(
    "live, code",
    [
        ({"analysis_status": "ai_unavailable", "model": {"status": "unavailable", "model_version": None}},
         diag.NO_MODEL_REGISTERED),
        ({"analysis_status": "ai_unavailable", "model": {"status": "not_promoted"}}, diag.MODEL_NOT_PROMOTED),
        ({"analysis_status": "ai_unavailable", "model": {"status": "artifact_missing"}}, diag.ARTIFACT_MISSING),
        ({"analysis_status": "ai_unavailable", "model": {"status": "checksum_failed"}}, diag.ARTIFACT_INTEGRITY_FAILED),
        ({"analysis_status": "ai_unavailable", "model": {"status": "incompatible_label_map"}}, diag.MODEL_LOAD_FAILED),
        ({"analysis_status": "ai_unavailable", "model": {"status": "candidate", "model_version": "1"}},
         diag.NO_IMAGE_BYTES),
        ({"analysis_status": "completed", "observation": {"abstained": True,
          "abstention_reason": "insufficient_image_quality"}}, diag.ABSTAINED_INSUFFICIENT_IMAGE_QUALITY),
        ({"analysis_status": "completed", "observation": {"abstained": True,
          "abstention_reason": "confidence_below_threshold"}}, diag.ABSTAINED_LOW_CONFIDENCE),
        ({"analysis_status": "completed", "observation": {"abstained": True,
          "abstention_reason": "unknown_review_required"}}, diag.ABSTAINED_UNKNOWN_REVIEW_REQUIRED),
        ({}, diag.UNKNOWN),
        (None, diag.UNKNOWN),
    ],
)
def test_classifier_maps_every_failure_mode(live, code):
    out = diag.classify_ai_unavailable(live)
    assert out["code"] == code
    assert out["code"] in diag.ALL_REASON_CODES
    assert out["message"] and out["admin_action"]


def test_explicit_adapter_code_wins_over_inference():
    live = {"analysis_status": "ai_unavailable", "unavailable_reason_code": diag.NO_IMAGE_BYTES,
            "model": {"status": "unavailable"}}
    assert diag.classify_ai_unavailable(live)["code"] == diag.NO_IMAGE_BYTES


def test_messages_leak_no_paths_ids_or_tenants():
    for code in diag.ALL_REASON_CODES:
        text = diag._TEXT[code]
        for part in text[1:]:
            assert "/" not in part and "id=" not in part and "tenant" not in part.lower()


# ── AI side, through the real adapter + analyze_inspection ──────────────────

def test_no_model_registered():
    db = SessionLocal()
    try:
        t = _tenant("nomodel")
        live = live_inference_adapter.predict(db, tenant_id=t, image_bytes=_png(1))
        assert live["unavailable_reason_code"] == diag.NO_MODEL_REGISTERED
        _assert_fail_closed(_analyze(db, t, image_bytes=_png(1)), diag.NO_MODEL_REGISTERED)
    finally:
        db.close()


def test_synthetic_experimental_model_is_not_promoted_and_not_served():
    db = SessionLocal()
    try:
        t = _tenant("exp")
        model = _train(db, t)  # real pipeline; synthetic data => Experimental
        assert model.candidate_stage == "Experimental"
        _entry(db)  # approved baseline metadata => the AI_UNAVAILABLE (not no-baseline) path
        result = _analyze(db, t, image_bytes=_png(2), itype=ITYPE, mfr=MFR, mdl=MDL)
        assert result["analysis_status"] == "ai_unavailable"
        _assert_fail_closed(result, diag.MODEL_NOT_PROMOTED)
        assert result["live_model_result"]["observation"] is None
        assert result["model_label"] == "No eligible trained model"
    finally:
        db.close()


def test_artifact_missing_and_integrity_failure_are_distinct():
    db = SessionLocal()
    try:
        t = _tenant("art")
        model = _train(db, t, stage="Candidate")
        original = model.artifact_path
        model.artifact_path = original + ".absent"
        db.commit()
        _assert_fail_closed(_analyze(db, t, image_bytes=_png(3)), diag.ARTIFACT_MISSING)

        model.artifact_path = original
        model.artifact_checksum = "0" * 64
        db.commit()
        _assert_fail_closed(_analyze(db, t, image_bytes=_png(3)), diag.ARTIFACT_INTEGRITY_FAILED)
    finally:
        db.close()


def test_eligible_model_without_image_bytes_reports_no_image_bytes():
    db = SessionLocal()
    try:
        t = _tenant("nobytes")
        _train(db, t, stage="Candidate")
        _entry(db)
        result = _analyze(db, t, image_bytes=None, itype=ITYPE, mfr=MFR, mdl=MDL)
        assert result["analysis_status"] == "ai_unavailable"
        _assert_fail_closed(result, diag.NO_IMAGE_BYTES)
        assert result["model_label"] == "Eligible model — image not available to it"
        assert result["recommended_action"] == "Manual inspection required — no AI observation for this image."
    finally:
        db.close()


def test_other_tenants_model_never_makes_this_tenant_eligible():
    db = SessionLocal()
    try:
        owner, other = _tenant("own"), _tenant("oth")
        _train(db, owner, stage="Candidate")
        _assert_fail_closed(_analyze(db, other, image_bytes=_png(4)), diag.NO_MODEL_REGISTERED)
    finally:
        db.close()


# ── baseline side (independent of the model) ────────────────────────────────

ITYPE = "i192_rigid_scope"
MFR, MDL = "Karl Storz", "Hopkins II"


def _entry(db):
    db.query(BaselineLibraryEntry).filter(BaselineLibraryEntry.instrument_category == ITYPE).delete()
    db.commit()
    entry = BaselineLibraryEntry(
        udi=f"udi-{ITYPE}", instrument_category=ITYPE, manufacturer_name=MFR, model_name=MDL,
        baseline_type="manufacturer", baseline_version="1.0", approval_status="approved", approved_by="seed",
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def _register(db, *, tenant, entry, photo, review=False, activate=False):
    reg = bir.register_manufacturer_reference_image(
        db, tenant_id=tenant, baseline_library_entry_id=entry.id, image_bytes=photo,
        content_type="image/png", uploaded_by="spd@x", source_organization="Manufacturer",
        source_reference="PO", usage_rights_attested=True, no_phi_attested=True,
    )
    if review:
        bil.review_baseline_image(
            db, link=reg["link"], reviewer="rev@x", reviewer_role="clinical_reviewer",
            decision="approve", rationale="verified", source_verification="PO",
            anatomy_compatibility_confirmed=True, image_quality_assessment="good",
        )
    if activate:
        bil.activate_baseline_image(db, link=reg["link"], actor="adm@x", actor_role="admin")
    return reg["link"]


def _evidence(db, tenant, *, photo, mdl=MDL):
    return _analyze(db, tenant, image_bytes=photo, itype=ITYPE, mfr=MFR, mdl=mdl)["baseline_evidence"]


def test_pending_review_reference_is_awaiting_review():
    db = SessionLocal()
    try:
        t = _tenant("bl-pend")
        _register(db, tenant=t, entry=_entry(db), photo=_png(10))
        ev = _evidence(db, t, photo=_png(10))
        assert ev["baseline_image_registered"] is True
        assert ev["baseline_image_active"] is False
        assert ev["baseline_image_status_code"] == "AWAITING_REVIEW"
        assert ev["baseline_image_lifecycle_states"] == ["PENDING_REVIEW"]
        assert ev["real_image_comparison_completed"] is False
    finally:
        db.close()


def test_approved_reference_is_awaiting_activation():
    db = SessionLocal()
    try:
        t = _tenant("bl-appr")
        _register(db, tenant=t, entry=_entry(db), photo=_png(11), review=True)
        ev = _evidence(db, t, photo=_png(11))
        assert ev["baseline_image_active"] is False
        assert ev["baseline_image_status_code"] == "AWAITING_ACTIVATION"
    finally:
        db.close()


def test_active_reference_for_a_different_model_is_active_not_matched():
    db = SessionLocal()
    try:
        t = _tenant("bl-mis")
        _register(db, tenant=t, entry=_entry(db), photo=_png(12), review=True, activate=True)
        ev = _evidence(db, t, photo=_png(12), mdl="Hopkins 2")  # identity typed differently
        assert ev["baseline_image_active"] is False
        assert ev["baseline_image_status_code"] == "ACTIVE_NOT_MATCHED"
        assert ev["real_image_comparison_completed"] is False
    finally:
        db.close()


def test_active_matching_reference_resolves_and_compares():
    db = SessionLocal()
    try:
        t = _tenant("bl-ok")
        link = _register(db, tenant=t, entry=_entry(db), photo=_png(13), review=True, activate=True)
        result = _analyze(db, t, image_bytes=_png(13), itype=ITYPE, mfr=MFR, mdl=MDL)
        ev = result["baseline_evidence"]
        assert ev["baseline_image_status_code"] == "ACTIVE_RESOLVED"
        assert ev["baseline_image_link_id"] == link.id
        assert ev["real_image_comparison_completed"] is True
        # A completed baseline comparison is NOT a trained-model finding.
        assert result["analysis_status"] == "ai_unavailable"
        assert result["confidence"] is None
    finally:
        db.close()


def test_another_tenants_active_reference_is_invisible():
    db = SessionLocal()
    try:
        owner, other = _tenant("bl-own"), _tenant("bl-oth")
        _register(db, tenant=owner, entry=_entry(db), photo=_png(14), review=True, activate=True)
        ev = _evidence(db, other, photo=_png(14))
        assert ev["baseline_image_registered"] is False
        assert ev["baseline_image_status_code"] == "NOT_REGISTERED"
        assert ev["baseline_image_lifecycle_states"] == []
        assert ev["baseline_image_link_id"] is None
    finally:
        db.close()


def test_artifact_dir_is_not_persistent_on_render():
    """Deployment fact the remediation plan depends on: the model artifact
    directory defaults to a relative path inside the container, and render.yaml
    declares no persistent disk. Fails if that changes so the docs get updated."""
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    render_path = os.path.join(root, "render.yaml")
    if not os.path.exists(render_path):
        pytest.skip("render.yaml not present in this checkout")
    with open(render_path, encoding="utf-8") as fh:
        render = fh.read()
    assert "disk:" not in render
    assert "LUMENAI_MODEL_ARTIFACT_DIR" not in render


def _blank_png(size=(16, 16)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, (0, 0, 0)).save(buf, format="PNG")
    return buf.getvalue()


def test_model_that_abstains_is_fail_closed_on_every_surface():
    """An eligible model that runs and abstains must not leave the
    authoritative AI surface saying COMPLETED / no manual inspection."""
    db = SessionLocal()
    try:
        t = _tenant("abst")
        _train(db, t, stage="Candidate")
        _entry(db)
        result = _analyze(db, t, image_bytes=_blank_png(), itype=ITYPE, mfr=MFR, mdl=MDL)
        live_obs = result["live_model_result"]["observation"]
        assert result["live_model_result"]["analysis_status"] == "completed"
        assert live_obs["abstained"] is True  # raw abstention kept for audit
        _assert_fail_closed(result, diag.ABSTAINED_INSUFFICIENT_IMAGE_QUALITY)
        assert result["ai_analysis"]["observation"] is None
        assert result["model_label"] == "Trained model abstained"
    finally:
        db.close()


def test_model_that_abstains_without_approved_baseline_is_fail_closed():
    db = SessionLocal()
    try:
        t = _tenant("abst-nb")
        _train(db, t, stage="Candidate")
        result = _analyze(db, t, image_bytes=_blank_png(), itype="i192_no_baseline_family")
        assert result["analysis_status"] == "supervisor_review_required"
        _assert_fail_closed(result, diag.ABSTAINED_INSUFFICIENT_IMAGE_QUALITY)
        assert result["ai_analysis"]["observation"] is None
    finally:
        db.close()
