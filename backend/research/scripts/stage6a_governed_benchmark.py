"""Stage 6A — governed PaDiM/PatchCore execution + benchmark readiness.

Unlike the Stage 5D low-level smoke script, this drives the REAL models through the
**Stage 5C/5D governed localizer interface** (`PadimLocalizer` / `PatchCoreLocalizer`
→ `run_anomaly_experiment`): checkpoint approval + SHA-256 verification → safe,
coverage-verified backbone load → normal-only fit → frozen-threshold calibration →
leakage-checked evaluation.

Two things are produced:

1. **Governed-interface execution verification** (synthetic non-clinical inputs,
   locally-generated research-execution backbone). This proves the governed pipeline
   runs end-to-end and is deterministic. It is **NOT** scientific performance and is
   flagged `synthetic_technical_test`.
2. **Real-image benchmark readiness** via `generate_cohort_readiness_report`. With no
   authorized real cohort present, the real benchmark is reported **BLOCKED**, with
   the precise missing evidence.

No ImageNet / third-party-rights weights are used or downloaded; the backbone is
generated locally this run and approved only as a research-execution checkpoint
(`scientifically_valid=False`). Run ONLY in the isolated research venv.
"""
from __future__ import annotations

import hashlib
import json
import os
import platform
import tempfile


def _blocked(reason: str) -> dict:
    return {"status": "BLOCKED", "reason": reason}


def _make_research_backbone(model_ctor) -> tuple[str, str]:
    """Build a model, snapshot its feature-extractor state dict to a local file
    (random init — NO licensed weights), and return (path, sha256)."""
    import torch  # noqa: PLC0415

    model = model_ctor()
    sd = {k: v.clone() for k, v in model.feature_extractor.state_dict().items()}
    fd, path = tempfile.mkstemp(suffix=".pt", prefix="stage6a_backbone_")
    os.close(fd)
    torch.save(sd, path)
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return path, h.hexdigest()


def run() -> dict:
    try:
        import numpy as np  # noqa: PLC0415
        import torch  # noqa: PLC0415
        import anomalib  # noqa: PLC0415
        from anomalib.models.image.padim.torch_model import PadimModel  # noqa: PLC0415
        from anomalib.models.image.patchcore.torch_model import PatchcoreModel  # noqa: PLC0415
    except Exception as exc:  # pragma: no cover - env-dependent
        return _blocked(f"research dependency missing/incompatible: {type(exc).__name__}: {exc}")

    # Initialize the app DB layer first to avoid a cold circular import when the
    # research governance module pulls app.models (same ordering the tests use).
    from app.db.session import SessionLocal  # noqa: F401, PLC0415

    from research.lens_vision import checkpoint as ckpt  # noqa: PLC0415
    from research.lens_vision.anomaly_experiment import run_anomaly_experiment  # noqa: PLC0415
    from research.lens_vision.anomaly_localization import PadimLocalizer, PatchCoreLocalizer  # noqa: PLC0415
    from research.lens_vision.backbone_loader import set_offline_environment  # noqa: PLC0415
    from research.lens_vision.cohort_readiness import generate_cohort_readiness_report  # noqa: PLC0415
    from research.lens_vision.config import ResearchRunConfig  # noqa: PLC0415
    from research.lens_vision.synthetic_fixtures import synthetic_anomaly_dataset  # noqa: PLC0415

    set_offline_environment()
    torch.manual_seed(0)
    np.random.seed(0)

    record: dict = {
        "status": "EXECUTED",
        "disclaimer": (
            "Governed-interface execution verification on SYNTHETIC non-clinical inputs with a "
            "locally-generated research-execution backbone (scientifically_valid=False). NOT "
            "scientific or clinical performance. The real-image benchmark is BLOCKED (see below)."
        ),
        "environment": {
            "python": platform.python_version(), "torch": torch.__version__,
            "numpy": np.__version__, "anomalib": anomalib.__version__,
            "cuda_available": bool(torch.cuda.is_available()),
        },
        "governed_execution": {},
    }

    policy = {
        "policy_id": "stage6a_research_execution", "reason": "Locally-generated backbone; research execution only.",
        "min_coverage": 1.0, "allow_missing_keys": False, "allow_shape_mismatch": False,
        "scientifically_valid": False,
    }

    specs = [
        ("padim", PadimLocalizer, lambda: PadimModel(backbone="resnet18", layers=["layer1", "layer2", "layer3"],
                                                     pre_trained=False, n_features=100),
         {"resize": [256, 256], "mean": [0.485, 0.456, 0.406], "std": [0.229, 0.224, 0.225]}),
        ("patchcore", PatchCoreLocalizer, lambda: PatchcoreModel(backbone="resnet18", layers=["layer2", "layer3"],
                                                                 pre_trained=False, num_neighbors=5),
         {"resize": [224, 224], "mean": [0.485, 0.456, 0.406], "std": [0.229, 0.224, 0.225]}),
    ]

    normal, test = synthetic_anomaly_dataset(n_normal=10, n_anomalous=6)

    for name, Localizer, ctor, preproc in specs:
        try:
            path, sha = _make_research_backbone(ctor)
            ckpt_id = f"resnet18_research_exec_{name}"
            ckpt.register_operator_approved_checkpoint(
                ckpt_id, file_path=path, architecture="resnet18",
                license="n/a (locally generated this run; no third-party weights)",
                source_url="", description=f"Stage 6A research-execution backbone for {name}.",
                preprocessing=preproc, compatibility_policy=policy,
                approver_id="stage6a-research-operator", research_execution_only=True,
            )
            cfg = ResearchRunConfig(run_id=f"stage6a_{name}", seed=5, checkpoint_id=ckpt_id,
                                    source_provenance_class="synthetic_experimental", embedder=name)

            def _localizer():
                return Localizer(backbone_checkpoint_id=ckpt_id, file_path=path)

            r1 = run_anomaly_experiment(normal, test, config=cfg, localizer=_localizer(),
                                        synthetic_technical_test=True)
            r2 = run_anomaly_experiment(normal, test, config=cfg, localizer=_localizer(),
                                        synthetic_technical_test=True)
            scores1 = [x["image_level_anomaly_score"] for x in r1["results"]]
            scores2 = [x["image_level_anomaly_score"] for x in r2["results"]]
            lz = _localizer()  # for the load report
            lz.fit([normal[0]["image_bytes"]])
            record["governed_execution"][name] = {
                "executed_through_governed_localizer": True,
                "checkpoint_id": ckpt_id,
                "backbone_sha256": sha,
                "backbone_load": lz.load_report.to_dict() if lz.load_report else None,
                "scientifically_valid_backbone": bool(lz.backbone_scientifically_valid),
                "n_fit_normal": r1["n_fit_normal"],
                "n_calibration_normal": r1["n_calibration_normal"],
                "frozen_threshold": r1["frozen_threshold"],
                "deterministic": scores1 == scores2,
                "synthetic_technical_test": True,
                "research_only": r1["research_only"],
                "example_image_level_scores": [round(s, 4) for s in scores1[:4]],
            }
        except Exception as exc:  # pragma: no cover - env-dependent
            import traceback  # noqa: PLC0415
            record["governed_execution"][name] = {
                "executed_through_governed_localizer": False,
                "error": f"{type(exc).__name__}: {exc}", "traceback": traceback.format_exc()[-900:]}

    # Real-image benchmark readiness — no authorized cohort present.
    manifest_path = os.environ.get("STAGE6A_COHORT_MANIFEST")
    manifest = []
    if manifest_path and os.path.exists(manifest_path):
        with open(manifest_path, encoding="utf-8") as f:
            manifest = json.load(f)
    readiness = generate_cohort_readiness_report(manifest)
    missing: list[str] = []
    if not manifest:
        missing.append("no authorized, independently-reviewed real-image cohort present")
    missing.extend(readiness["blockers"])

    # Stage 6C: resolve record-backed scientific-readiness prerequisites (fail-closed).
    scientific_readiness = None
    try:
        from research.lens_vision.scientific_authorization import assess_scientific_readiness  # noqa: PLC0415
        scientific_readiness = assess_scientific_readiness(
            SessionLocal(), tenant_id=os.environ.get("STAGE6C_TENANT", "research-tenant"),
            dataset_id=os.environ.get("STAGE6C_DATASET", ""), dataset_owner_email="",
            checkpoint_id=os.environ.get("STAGE6C_CHECKPOINT", "smoke_stub"),
            statistical_reviewer_username="", statistical_protocol_id="",
        )
        for name, state in scientific_readiness["checks"].items():
            if state != "resolved":
                missing.append(f"scientific_authorization:{name}:{state}")
    except Exception as exc:  # noqa: BLE001
        missing.append(f"scientific_authorization_unavailable:{type(exc).__name__}")

    ready = readiness["ready_for_scientific_benchmark"] and bool(
        scientific_readiness and scientific_readiness["ready_for_scientific_benchmark"])
    record["real_image_benchmark"] = {
        # Explicit sentinel — never substitute random-weight metrics.
        "status": "READY" if ready else "BLOCKED_REAL_IMAGE_BENCHMARK",
        "missing_requirements": missing,
        "cohort_readiness": readiness,
        "scientific_readiness": scientific_readiness,
        "note": "Random-weight execution above is pipeline verification only and is "
                "NEVER real-image scientific performance.",
    }
    return record


if __name__ == "__main__":
    out = json.dumps(run(), indent=2)
    print(out)
    dest = os.environ.get("STAGE6A_OUT")
    if dest:
        with open(dest, "w", encoding="utf-8") as f:
            f.write(out)
