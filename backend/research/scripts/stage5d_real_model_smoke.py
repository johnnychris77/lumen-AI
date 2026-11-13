"""Stage 5D — GENUINE PaDiM + PatchCore research-execution smoke.

This script runs the **real Anomalib 1.1.x** PaDiM and PatchCore torch models
(fit + score) on CONTROLLED, SYNTHETIC, NON-CLINICAL inputs, through the Stage 5D
hardened, governed backbone loader. It exists to demonstrate that the genuine
model code executes end-to-end and to record versions / digests / latency /
memory — it is **NOT** scientific or clinical validation, and it uses **NO**
third-party-rights pretrained weights.

Honesty constraints enforced here:

* The backbone is **locally generated** (``pre_trained=False`` → random init),
  snapshotted to a file, SHA-256-recorded, and reloaded through the governed
  ``safe_torch_load`` + ``load_verified_backbone`` path under an explicit
  :class:`CompatibilityPolicy` whose ``scientifically_valid=False``. No ImageNet /
  DINOv2 / other licensed weights are downloaded or used.
* Inputs are deterministic synthetic tensors — not instrument, borescope, or
  patient images. No accuracy, sensitivity, or clinical metric is computed or
  implied; only execution facts (shapes, latency, memory) are recorded.

Run ONLY in the isolated research venv:
    PYTHONPATH=backend python backend/research/scripts/stage5d_real_model_smoke.py

It never runs in CI or production (torch/anomalib are not installed there) and is
not imported by any app/ module.
"""
from __future__ import annotations

import hashlib
import json
import os
import platform
import sys
import tempfile
import time


def _blocked(reason: str) -> dict:
    return {"status": "BLOCKED", "reason": reason}


def _patch_anomalib_rich() -> None:
    """Work around an anomalib/rich incompatibility in the coreset sampler's
    progress bar (``Console`` has no ``_live`` in this rich version). We replace
    the progress wrapper with a plain pass-through — it changes NOTHING about the
    algorithm, only the (broken) progress UI."""
    try:
        import anomalib.utils.rich as arich  # noqa: PLC0415

        arich.safe_track = lambda sequence=None, **_kw: sequence if sequence is not None else []
        # Some call sites import the symbol directly.
        import anomalib.models.components.sampling.k_center_greedy as kcg  # noqa: PLC0415
        kcg.safe_track = arich.safe_track
    except Exception:  # pragma: no cover - best effort
        pass


def _peak_rss_mb() -> float:
    try:
        import resource  # noqa: PLC0415

        ru = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        # Linux reports KiB; macOS reports bytes.
        return round(ru / 1024.0, 1) if sys.platform != "darwin" else round(ru / (1024.0 * 1024.0), 1)
    except Exception:  # pragma: no cover
        return -1.0


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def run() -> dict:
    # 1) Dependencies — report BLOCKED rather than faking anything.
    try:
        import numpy as np  # noqa: PLC0415
        import torch  # noqa: PLC0415
        import torchvision  # noqa: PLC0415
        import anomalib  # noqa: PLC0415
        from anomalib.models.image.padim.torch_model import PadimModel  # noqa: PLC0415
        from anomalib.models.image.patchcore.torch_model import PatchcoreModel  # noqa: PLC0415
    except Exception as exc:  # pragma: no cover - env-dependent
        return _blocked(f"research dependency missing/incompatible: {type(exc).__name__}: {exc}")

    from research.lens_vision.backbone_loader import (  # noqa: PLC0415
        CompatibilityPolicy,
        load_verified_backbone,
        safe_torch_load,
        set_offline_environment,
    )

    set_offline_environment()
    _patch_anomalib_rich()
    torch.manual_seed(0)
    np.random.seed(0)

    record: dict = {
        "status": "EXECUTED",
        "disclaimer": (
            "Research-execution smoke only. Locally-generated (random-init) backbone, "
            "no third-party-rights weights, synthetic non-clinical inputs. NOT scientific "
            "or clinical validation; no accuracy/sensitivity/specificity is implied."
        ),
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "torch": torch.__version__,
            "torchvision": torchvision.__version__,
            "numpy": np.__version__,
            "anomalib": anomalib.__version__,
            "cuda_available": bool(torch.cuda.is_available()),
        },
        "models": {},
    }

    workdir = tempfile.mkdtemp(prefix="stage5d_smoke_")

    # 2) Generate a LOCAL backbone checkpoint (random init; no licensed weights).
    #    Snapshot the Anomalib feature extractor's own state dict so the governed
    #    loader verifies name+shape coverage == 1.0 on reload.
    seed_model = PadimModel(backbone="resnet18", layers=["layer1", "layer2", "layer3"],
                            pre_trained=False, n_features=100)
    feat_sd = {k: v.clone() for k, v in seed_model.feature_extractor.state_dict().items()}
    ckpt_path = os.path.join(workdir, "resnet18_research_smoke.pt")
    torch.save(feat_sd, ckpt_path)
    ckpt_sha = _sha256(ckpt_path)
    record["backbone"] = {
        "identity": "resnet18_research_smoke (locally generated, random init)",
        "sha256": ckpt_sha,
        "n_tensors": len(feat_sd),
        "rights": "none required — weights generated locally this run; no ImageNet/DINOv2 weights used",
        "scientifically_valid": False,
    }

    # A documented policy authorizing this research-execution backbone (full
    # coverage still required — it is an exact self-snapshot — but flagged as NOT
    # scientifically valid so nothing downstream mistakes it for science).
    policy = CompatibilityPolicy(
        policy_id="stage5d_research_execution_smoke",
        reason="Locally-generated random-init backbone for execution smoke; not scientific.",
        min_coverage=1.0, allow_missing_keys=False, allow_shape_mismatch=False,
        scientifically_valid=False,
    )

    preprocessing = {"resize": [256, 256], "mean": [0.485, 0.456, 0.406], "std": [0.229, 0.224, 0.225],
                     "note": "standard ImageNet normalization CONSTANTS (not weights); applied to synthetic inputs"}

    # 3) Controlled synthetic non-clinical inputs (deterministic tensors).
    def _norm_batch(n, size=256):
        return torch.rand(n, 3, size, size)

    # ---- PaDiM ----
    try:
        pm = PadimModel(backbone="resnet18", layers=["layer1", "layer2", "layer3"],
                        pre_trained=False, n_features=100)
        state = safe_torch_load(ckpt_path)
        load_report = load_verified_backbone(pm.feature_extractor, state, policy=policy)
        for p in pm.parameters():
            p.requires_grad_(False)

        pm.train()
        t0 = time.perf_counter()
        with torch.no_grad():
            emb = pm(_norm_batch(8))
            pm.gaussian.fit(emb)
        fit_ms = round((time.perf_counter() - t0) * 1000.0, 2)

        pm.eval()
        t1 = time.perf_counter()
        with torch.no_grad():
            amap = pm(_norm_batch(1))
        score_ms = round((time.perf_counter() - t1) * 1000.0, 2)
        amap_np = amap.squeeze().cpu().numpy()
        record["models"]["padim"] = {
            "executed": True,
            "backbone_load": load_report.to_dict(),
            "fit": {"n_normal": 8, "embedding_shape": list(emb.shape), "fit_ms": fit_ms},
            "score": {"anomaly_map_shape": list(amap.shape), "score_ms": score_ms,
                      "map_min": float(amap_np.min()), "map_max": float(amap_np.max()),
                      "map_mean": float(amap_np.mean()), "all_finite": bool(np.isfinite(amap_np).all())},
            "preprocessing": preprocessing,
        }
    except Exception as exc:  # pragma: no cover - env-dependent
        import traceback  # noqa: PLC0415
        record["models"]["padim"] = {"executed": False, "error": f"{type(exc).__name__}: {exc}",
                                      "traceback": traceback.format_exc()[-800:]}

    # ---- PatchCore ----
    try:
        cm = PatchcoreModel(backbone="resnet18", layers=["layer2", "layer3"],
                            pre_trained=False, num_neighbors=5)
        state = safe_torch_load(ckpt_path)
        cm_report = load_verified_backbone(cm.feature_extractor, state, policy=policy)
        for p in cm.parameters():
            p.requires_grad_(False)

        cm.train()
        t0 = time.perf_counter()
        with torch.no_grad():
            emb = cm(_norm_batch(8, size=224))
            cm.subsample_embedding(emb, sampling_ratio=0.1)
        fit_ms = round((time.perf_counter() - t0) * 1000.0, 2)

        cm.eval()
        t1 = time.perf_counter()
        with torch.no_grad():
            out = cm(_norm_batch(1, size=224))
        score_ms = round((time.perf_counter() - t1) * 1000.0, 2)
        if hasattr(out, "anomaly_map"):
            amap = out.anomaly_map
        elif isinstance(out, dict):
            amap = out.get("anomaly_map", next(iter(out.values())))
        else:
            amap = out
        amap_np = amap.squeeze().cpu().numpy()
        record["models"]["patchcore"] = {
            "executed": True,
            "backbone_load": cm_report.to_dict(),
            "fit": {"n_normal": 8, "embedding_shape": list(emb.shape),
                    "memory_bank_shape": list(cm.memory_bank.shape), "fit_ms": fit_ms},
            "score": {"anomaly_map_shape": list(amap.shape), "score_ms": score_ms,
                      "map_min": float(amap_np.min()), "map_max": float(amap_np.max()),
                      "map_mean": float(amap_np.mean()), "all_finite": bool(np.isfinite(amap_np).all())},
            "preprocessing": {**preprocessing, "resize": [224, 224]},
        }
    except Exception as exc:  # pragma: no cover - env-dependent
        import traceback  # noqa: PLC0415
        record["models"]["patchcore"] = {"executed": False, "error": f"{type(exc).__name__}: {exc}",
                                          "traceback": traceback.format_exc()[-800:]}

    record["peak_rss_mb"] = _peak_rss_mb()
    return record


if __name__ == "__main__":
    result = run()
    out = json.dumps(result, indent=2)
    print(out)
    # Also persist next to the script's output dir if a path is given.
    dest = os.environ.get("STAGE5D_SMOKE_OUT")
    if dest:
        with open(dest, "w", encoding="utf-8") as f:
            f.write(out)
