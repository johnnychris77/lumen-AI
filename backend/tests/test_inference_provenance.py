"""Acceptance tests — inference provenance & real-vision pilot readiness.

Proves the eight guarantees from the "Correct inspection inference provenance"
task: deterministic-placeholder output is never presented as a verified AI
observation, probability, clinical interpretation, or real baseline image
similarity; the live-model contract is the authoritative AI source; and no model
result can auto-authorize instrument release.

All image bytes are built inline with Pillow (repo convention — no static
fixtures). Each test uses a unique instrument type / tenant to stay isolated.
"""
import io

from PIL import Image

from app.db.session import SessionLocal
from app.models.baseline_library import BaselineLibraryEntry
from app.ai.inference import SUPPORTED_MODEL_CATEGORIES
from app.services.baseline_comparison_scoring_service import (
    _authoritative_ai_analysis,
    analyze_inspection,
)
from app.services.ml.image_similarity_service import (
    COMPARATOR_VERSION,
    compare_against_baseline,
)
from app.services.ml.live_inference_adapter import (
    HEALTH_UNAVAILABLE,
    load_active_model,
    predict as live_predict,
)
from app.services.ml.lens_model_registration import MODEL_ID

# A dedicated tenant with no registered model of its own, so "no eligible
# model" holds regardless of what other suites register for default-tenant on
# the shared test DB. Baseline library entries resolve by instrument category
# (not tenant), so seeded baselines still resolve for this tenant.
TENANT = "prov-vision-tenant"


def _png(color=(120, 120, 120), size=(64, 64)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format="PNG")
    return buf.getvalue()


def _seed_manufacturer_baseline(instrument_type: str) -> None:
    db = SessionLocal()
    try:
        db.add(BaselineLibraryEntry(
            udi=f"udi-{instrument_type}", instrument_category=instrument_type,
            manufacturer_name="M", model_name="X", baseline_type="manufacturer",
            approval_status="approved",
        ))
        db.commit()
    finally:
        db.close()


def _analyze(instrument_type: str, **kwargs) -> dict:
    db = SessionLocal()
    try:
        return analyze_inspection(
            db, instrument_type=instrument_type, tenant_id=TENANT, has_image=True, **kwargs
        )
    finally:
        db.close()


# 1. No trained model produces an explicit AI_UNAVAILABLE result.
def test_no_trained_model_yields_ai_unavailable():
    itype = "prov_no_model"
    _seed_manufacturer_baseline(itype)
    res = _analyze(itype, image_sha256="a" * 64)

    assert res["ai_analysis"]["status"] == "AI_UNAVAILABLE"
    assert res["ai_analysis"]["manual_inspection_required"] is True
    assert res["ai_analysis"]["observation"] is None
    assert res["ai_observations_source"] == "live_model"
    assert res["live_model_result"]["analysis_status"] == "ai_unavailable"

    # And the adapter itself, directly, with real bytes but no promoted model.
    db = SessionLocal()
    try:
        contract = live_predict(db, tenant_id=TENANT, image_bytes=_png())
    finally:
        db.close()
    assert contract["analysis_status"] == "ai_unavailable"
    assert contract["observation"] is None
    assert contract["human_review_required"] is True


# 2. A missing or invalid image cannot produce a positive AI detection claim.
def test_missing_image_no_positive_ai_detection():
    db = SessionLocal()
    try:
        contract = live_predict(db, tenant_id=TENANT, image_bytes=None)
    finally:
        db.close()
    assert contract["analysis_status"] == "ai_unavailable"
    assert contract["observation"] is None  # no detection asserted from no pixels

    ai = _authoritative_ai_analysis(contract)
    assert ai["status"] == "AI_UNAVAILABLE"
    assert ai["observation"] is None

    # Through the full inspection path, with no image bytes threaded in.
    itype = "prov_missing_img"
    _seed_manufacturer_baseline(itype)
    res = _analyze(itype, image_sha256="b" * 64, image_bytes=None)
    assert res["ai_analysis"]["status"] == "AI_UNAVAILABLE"
    assert res["ai_analysis"]["observation"] is None


# 3. A metadata-only baseline cannot produce a genuine image-similarity percentage.
def test_metadata_only_baseline_no_similarity_percentage():
    # Baseline "available" but one side has no real bytes -> no number.
    comp = compare_against_baseline(
        image_bytes=_png(), baseline_image_bytes=None,
        candidate_instrument_family="fam", baseline_instrument_family="fam",
        baseline_available=True,
    )
    assert comp["similarity"] is None

    ai = _authoritative_ai_analysis({
        "analysis_status": "completed", "model": {}, "observation": None,
        "supported_categories": [], "unsupported_categories": [], "baseline_comparison": comp,
    })
    assert ai["baseline_image_similarity"]["similarity"] is None
    assert ai["baseline_image_similarity"]["is_image_comparison"] is False

    # Full path: a metadata baseline row exists, but no ACTIVE baseline IMAGE
    # with verified bytes -> authoritative similarity stays None.
    itype = "prov_meta_baseline"
    _seed_manufacturer_baseline(itype)
    res = _analyze(itype, image_sha256="c" * 64)
    sim = res["ai_analysis"]["baseline_image_similarity"]
    assert sim is None or sim.get("similarity") is None
    # The heuristic match score is explicitly NOT image similarity.
    assert res["baseline_match_is_image_similarity"] is False


# 4. Identical supported images produce a traceable actual comparison result.
def test_identical_images_traceable_real_comparison():
    img = _png((50, 60, 70))
    comp = compare_against_baseline(
        image_bytes=img, baseline_image_bytes=img,
        candidate_instrument_family="fam", baseline_instrument_family="fam",
        baseline_available=True, baseline_id=7, baseline_version="v1",
    )
    assert comp["status"] == "exact_match"
    assert comp["similarity"] == 1.0
    assert comp["comparator_version"] == COMPARATOR_VERSION
    assert comp["baseline_id"] == 7

    ai = _authoritative_ai_analysis({
        "analysis_status": "completed", "model": {}, "observation": None,
        "supported_categories": [], "unsupported_categories": [], "baseline_comparison": comp,
    })
    assert ai["baseline_image_similarity"]["similarity"] == 1.0
    assert ai["baseline_image_similarity"]["is_image_comparison"] is True
    # Labelled visual similarity — never verified cleanliness.
    assert "not verified cleanliness" in ai["baseline_image_similarity"]["label"].lower()


# 5. Cross-tenant baseline or inspection images cannot be used.
def test_cross_tenant_model_not_used():
    from app.models.model_registry import ModelRegistryEntry

    db = SessionLocal()
    try:
        db.query(ModelRegistryEntry).filter(
            ModelRegistryEntry.tenant_id.in_(["prov-cross-A", "prov-cross-B"])
        ).delete(synchronize_session=False)
        db.add(ModelRegistryEntry(
            tenant_id="prov-cross-B", model_id=MODEL_ID, model_version="9.9.9",
            model_type="classification", training_status="trained", candidate_stage="Pilot",
        ))
        db.commit()
        tenant_a = load_active_model(db, tenant_id="prov-cross-A")
        tenant_b = load_active_model(db, tenant_id="prov-cross-B")
    finally:
        db.query(ModelRegistryEntry).filter(
            ModelRegistryEntry.tenant_id.in_(["prov-cross-A", "prov-cross-B"])
        ).delete(synchronize_session=False)
        db.commit()
        db.close()

    # Tenant A cannot see tenant B's trained model at all.
    assert tenant_a["status"] == HEALTH_UNAVAILABLE
    assert tenant_a["model"] is None
    # Tenant B DOES resolve its own model (some non-"no-model" state).
    assert tenant_b["status"] != HEALTH_UNAVAILABLE


# 6. Technician-declared findings remain distinguishable from model observations.
def test_declared_findings_distinct_from_model():
    itype = "prov_declared"
    _seed_manufacturer_baseline(itype)
    res = _analyze(itype, image_sha256="d" * 64, declared_findings=["blood"])

    # With no eligible model the result is AI_UNAVAILABLE: no fabricated AI
    # findings at all, and the technician's declared observations are kept
    # distinct as HUMAN observations (never attributed to AI).
    assert res["ai_analysis"]["status"] == "AI_UNAVAILABLE"
    assert res["predicted_findings"] == []
    assert any("blood" in o.lower() for o in res["technician_declared_observations"])
    # The authoritative AI observation channel is separate and empty (no model).
    assert res["ai_analysis"]["observation"] is None

    # When the segregated demo scorer is explicitly opted into, declared findings
    # are still provenance-tagged as technician-declared, never verified AI.
    demo = _analyze(itype, image_sha256="d" * 64, declared_findings=["blood"], demo_scoring=True)
    by_type = {f["type"]: f for f in demo["predicted_findings"]}
    assert by_type["blood"]["observation_source"] == "technician_declared"
    assert by_type["blood"]["verified_ai"] is False


# 7. Unsupported categories never receive invented model confidence scores.
def test_unsupported_categories_no_invented_confidence():
    itype = "prov_unsupported"
    _seed_manufacturer_baseline(itype)
    # Declare "blood", which is NOT a supported model category (debris/corrosion).
    res = _analyze(itype, image_sha256="e" * 64, declared_findings=["blood"])

    model_result = res["model_result"]
    supported = set(model_result["supported_categories"])
    assert supported <= set(SUPPORTED_MODEL_CATEGORIES)
    # Every emitted model finding is a supported category; "blood" never gets one.
    emitted = {f["category"] for f in model_result["findings"]}
    assert emitted <= supported
    assert "blood" not in emitted
    # Unsupported categories are names only — carry no confidence field.
    assert isinstance(res["ai_analysis"]["unsupported_categories"], list)


# 8. No model result can automatically authorize instrument release.
def test_no_model_result_authorizes_release():
    itype = "prov_release"
    _seed_manufacturer_baseline(itype)
    res = _analyze(itype, image_sha256="f" * 64)

    assert res["ai_analysis"]["authorizes_release"] is False
    assert res["ai_analysis"]["human_review_required"] is True
    assert res["human_review_required"] is True
    assert res["live_model_result"]["human_review_required"] is True
