"""Stage 5B — research-only anomaly-localization regression + governance tests.

Runs WITHOUT PyTorch/Anomalib (the real PaDiM/PatchCore paths are governed
blockers and are asserted as blocked). Covers the 12 required safeguard
categories plus the spatial-heatmap correctness/alignment check on deterministic
synthetic fixtures.
"""
from __future__ import annotations

import importlib.util
import json
import os

import pytest

# Initialize the app DB/model layer BEFORE importing research modules (which pull
# app.models submodules), avoiding a cold circular-import in app.db <-> app.models.
from app.db.session import SessionLocal  # noqa: F401,E402  (import-order intentional)

from research.lens_vision.anomaly_contract import AnomalyResult, build_anomaly_result
from research.lens_vision.anomaly_feasibility import AnomalyRegion, ClinicalDiagnosisForbiddenError
from research.lens_vision.anomaly_experiment import (
    LeakageError,
    NormalOnlyViolation,
    compare_localizers,
    run_anomaly_experiment,
    write_anomaly_model_card,
)
from research.lens_vision.anomaly_localization import (
    PadimLocalizer,
    PatchCoreLocalizer,
    StubLocalizer,
)
from research.lens_vision import checkpoint as ckpt
from research.lens_vision.config import ResearchRunConfig
from research.lens_vision.provenance import ResearchProvenanceError
from research.lens_vision.synthetic_fixtures import synthetic_anomaly_dataset

TORCH = importlib.util.find_spec("torch") is not None


def _cfg(checkpoint_id="stub_backbone", **kw):
    base = dict(run_id="anom", seed=11, checkpoint_id=checkpoint_id,
                source_provenance_class="synthetic_experimental", embedder="stub_padim_like")
    base.update(kw)
    return ResearchRunConfig(**base)


# ── 1 & 2 — normal-only eligibility; unlabeled/unknown/abnormal excluded ─────

def test_normal_only_fit_rejects_non_verified_normal():
    normal, test = synthetic_anomaly_dataset(n_normal=6, n_anomalous=4)
    bad = dict(normal[0])
    bad["ground_truth_status"] = "unlabeled"
    with pytest.raises(NormalOnlyViolation):
        run_anomaly_experiment([bad] + normal[1:], test, config=_cfg(), localizer=StubLocalizer())


def test_abnormal_and_unknown_cannot_fit_normal_model():
    normal, test = synthetic_anomaly_dataset(n_normal=6, n_anomalous=4)
    for status in ("abnormal", "unknown"):
        bad = dict(normal[0])
        bad["ground_truth_status"] = status
        with pytest.raises(NormalOnlyViolation):
            run_anomaly_experiment([bad], test, config=_cfg(), localizer=StubLocalizer())


# ── 3 & 4 — license/checkpoint denial; no auto weight download ───────────────

def test_padim_patchcore_blocked_until_backbone_approved():
    with pytest.raises(ckpt.CheckpointNotApprovedError):
        PadimLocalizer(backbone_checkpoint_id="resnet18_imagenet")
    with pytest.raises(ckpt.CheckpointNotApprovedError):
        PatchCoreLocalizer(backbone_checkpoint_id="resnet18_imagenet")
    with pytest.raises(ckpt.CheckpointNotRegisteredError):
        PadimLocalizer(backbone_checkpoint_id="not_a_backbone")


def test_no_auto_download_backbone_requires_verified_file(tmp_path, monkeypatch):
    # An approved backbone still requires a present, hash-verified file — never a download.
    rec = ckpt.CheckpointRecord(
        checkpoint_id="rn18_test", description="t", license="BSD-3", source_url="",
        expected_sha256="deadbeef", approved=True, rights_cleared=True, requires_file=True,
        architecture="resnet18", preprocessing={"resize": [224, 224]},
    )
    monkeypatch.setitem(ckpt._REGISTRY, "rn18_test", rec)
    with pytest.raises(ckpt.CheckpointFileMissingError):
        ckpt.verify_checkpoint("rn18_test", file_path=str(tmp_path / "missing.bin"))


# ── 5 — spatial heatmap correctness + image alignment ───────────────────────

def test_heatmap_preserves_dims_and_localizes_patch():
    normal, test = synthetic_anomaly_dataset(n_normal=8, n_anomalous=4, size=64)
    loc = StubLocalizer().fit([s["image_bytes"] for s in normal])
    anomalous = next(s for s in test if s["anomaly_label"] == 1)
    heatmap, score = loc.score(anomalous["image_bytes"])
    assert len(heatmap) == 64 and len(heatmap[0]) == 64         # original dims preserved
    # argmax falls inside the known bright-patch region (rows/cols ~38..54).
    best = max(((v, y, x) for y, row in enumerate(heatmap) for x, v in enumerate(row)))
    _, by, bx = best
    assert 38 <= by <= 54 and 38 <= bx <= 54
    assert score > 0


# ── 6 — repeated specimen/session/image leakage prevention ──────────────────

def test_leakage_between_train_and_heldout_is_rejected():
    normal, test = synthetic_anomaly_dataset(n_normal=6, n_anomalous=4)
    leaky = dict(test[0])
    leaky["specimen_id"] = normal[0]["specimen_id"]   # shares a specimen with training
    with pytest.raises(LeakageError):
        run_anomaly_experiment(normal, [leaky], config=_cfg(), localizer=StubLocalizer())


# ── 7 — provenance/tenant/consent restrictions on research inputs ────────────

def test_experiment_rejects_non_research_authorized_provenance():
    normal, test = synthetic_anomaly_dataset(n_normal=6, n_anomalous=4)
    for s in test:
        s["data_provenance_class"] = "real_clinical"
        s["provenance_approval_status"] = "pending"
    with pytest.raises(ResearchProvenanceError):
        run_anomaly_experiment(normal, test, config=_cfg(), localizer=StubLocalizer())


# ── 8 — deterministic synthetic smoke experiment ────────────────────────────

def test_synthetic_experiment_is_deterministic_and_flagged():
    normal, test = synthetic_anomaly_dataset(n_normal=8, n_anomalous=6)
    r1 = run_anomaly_experiment(normal, test, config=_cfg(), localizer=StubLocalizer(), synthetic_technical_test=True)
    r2 = run_anomaly_experiment(normal, test, config=_cfg(), localizer=StubLocalizer(), synthetic_technical_test=True)
    assert r1["synthetic_technical_test"] is True
    scores1 = [res["image_level_anomaly_score"] for res in r1["results"]]
    scores2 = [res["image_level_anomaly_score"] for res in r2["results"]]
    assert scores1 == scores2
    # Metrics are computed (labels + masks exist) but flagged as a technical test.
    assert r1["image_level_metrics"]["measured"] is True
    assert "SYNTHETIC" in r1["image_level_metrics"]["note"]
    # Masks exist on synthetic fixtures -> pixel metrics are computed (technical test).
    assert r1["pixel_level_metrics"].get("mean_dice") is not None
    assert r1["pixel_level_metrics"]["mean_dice"] == r2["pixel_level_metrics"]["mean_dice"]


# ── 9 — anomaly regions never become confirmed diagnoses ────────────────────

def test_anomaly_output_carries_no_diagnosis():
    normal, test = synthetic_anomaly_dataset(n_normal=6, n_anomalous=4)
    report = run_anomaly_experiment(normal, test, config=_cfg(), localizer=StubLocalizer())
    for res in report["results"]:
        assert res["research_only"] is True
        assert res["clinical_promotion_eligible"] is False
        assert res["confirmed_diagnosis"] is None
        assert res["human_review_required"] is True
        assert res["calibration_status"] == "uncalibrated"
        assert res["uncertainty_status"] == "unknown"
    region = AnomalyRegion(x=0, y=0, width=1, height=1, anomaly_score=9.9, uncertainty=float("nan"))
    with pytest.raises(ClinicalDiagnosisForbiddenError):
        region.to_clinical_label()


# ── 10 — no clinical-serving model registration from research ───────────────

def test_research_experiment_registers_no_servable_model():
    import research.lens_vision.anomaly_experiment as exp
    import research.lens_vision.anomaly_localization as loc
    src = ""
    for mod in (exp, loc):
        with open(mod.__file__) as f:
            src += f.read()
    # The research anomaly path never touches the clinical serving/registry layer.
    assert "ModelRegistryEntry" not in src
    assert "live_inference_adapter" not in src
    report = run_anomaly_experiment(*synthetic_anomaly_dataset(n_normal=6, n_anomalous=4),
                                    config=_cfg(), localizer=StubLocalizer())
    assert report["clinical_promotion_eligible"] is False


# ── 11 — optional dependency isolation (no torch) ───────────────────────────

def test_stage5b_imports_and_stub_run_without_torch():
    from research.lens_vision.deps import torch_available
    assert torch_available() is TORCH
    report = run_anomaly_experiment(*synthetic_anomaly_dataset(n_normal=6, n_anomalous=4),
                                    config=_cfg(), localizer=StubLocalizer())
    assert report["research_only"] is True and report["localizer"] == "stub_padim_like"


# ── 12 — production inference + baseline comparison preserved ────────────────

def test_production_paths_unchanged():
    import io
    from PIL import Image
    from app.services.ml import image_similarity_service
    from app.services.ml.live_inference_adapter import predict
    db = SessionLocal()
    try:
        res = predict(db, tenant_id="s5b-no-model", image_bytes=None)
        assert res["analysis_status"] == "ai_unavailable" and res["observation"] is None
    finally:
        db.close()
    buf = io.BytesIO()
    Image.new("RGB", (100, 100), (80, 80, 80)).save(buf, format="PNG")
    data = buf.getvalue()
    comp = image_similarity_service.compare_image_bytes(data, data)
    assert comp["status"] == image_similarity_service.STATUS_EXACT_MATCH


# ── Compare PaDiM vs PatchCore — both blocked (no fabricated performance) ────

def test_compare_localizers_records_blocked_real_models():
    normal, test = synthetic_anomaly_dataset(n_normal=6, n_anomalous=4)
    out = compare_localizers(
        normal, test,
        config_factory=lambda name: _cfg(run_id=name),
        localizer_factories={
            "stub": lambda: StubLocalizer(),
            "padim": lambda: PadimLocalizer(backbone_checkpoint_id="resnet18_imagenet"),
            "patchcore": lambda: PatchCoreLocalizer(backbone_checkpoint_id="resnet18_imagenet"),
        },
        synthetic_technical_test=True,
    )
    assert out["comparisons"]["stub"]["research_only"] is True
    assert out["comparisons"]["padim"]["status"] == "blocked"
    assert out["comparisons"]["patchcore"]["status"] == "blocked"
    assert "CheckpointNotApprovedError" in out["comparisons"]["padim"]["reason"]


def test_anomaly_model_card_is_research_only(tmp_path):
    normal, test = synthetic_anomaly_dataset(n_normal=6, n_anomalous=4)
    report = run_anomaly_experiment(normal, test, config=_cfg(), localizer=StubLocalizer(),
                                    synthetic_technical_test=True)
    path = os.path.join(tmp_path, "anom_card.json")
    card = write_anomaly_model_card(path, _cfg(), report)
    assert card["research_only"] is True and card["clinical_promotion_eligible"] is False
    with open(path) as f:
        on_disk = json.load(f)
    assert "RESEARCH ONLY" in on_disk["banner"]


def test_build_anomaly_result_contract_fields():
    sample = {"id": 1, "image_sha256": "abc", "data_provenance_class": "synthetic_experimental",
              "tenant_id": "t"}
    res = build_anomaly_result(
        sample=sample, image_score=1.2, heatmap_shape=(8, 8), heatmap_ref="h://1",
        regions=[], config=_cfg(), record=ckpt.get_record("stub_backbone"),
        grouping_reliable=True, validation_limitations=[],
    )
    assert isinstance(res, AnomalyResult)
    d = res.to_dict()
    assert d["clinical_promotion_eligible"] is False and d["confirmed_diagnosis"] is None
    assert d["human_review_required"] is True and d["uncertainty_status"] == "unknown"


@pytest.mark.skipif(not TORCH, reason="torch/anomalib not installed (research extra)")
def test_padim_requires_anomalib_even_with_torch():
    # Even with torch, an unapproved backbone is refused before anything loads.
    with pytest.raises(ckpt.CheckpointNotApprovedError):
        PadimLocalizer(backbone_checkpoint_id="resnet18_imagenet")
