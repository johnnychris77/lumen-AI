"""Issue #192 — isolated, non-production end-to-end verification.

Run from ``backend/``:

    python scripts/issue192_e2e_verification.py --out <path.json>

It creates a THROWAWAY SQLite database and a throwaway model-artifact
directory under a fresh temporary directory, then exercises the real
inspection pipeline (``analyze_inspection`` -> live inference adapter ->
model registry -> baseline resolver/comparator). Nothing touches a
deployed database, a deployed artifact store, or any network service.

What it establishes:

1. Model inventory: whether any real-data, validated model artifact exists in
   this repository. If none does, the verdict is BLOCKED_NO_VALIDATED_MODEL.
2. Negative controls (fail-closed): no model registered; synthetic
   experimental model (not promoted); artifact missing; artifact checksum
   failure; eligible model but no image bytes; baseline reference image
   PENDING_REVIEW; APPROVED-not-activated; ACTIVE but not matching the
   inspection identity.
3. Positive baseline control: an ACTIVE, matching reference image produces a
   real pixel comparison. This is NOT defect detection.
4. Engineering-mechanics control (NOT clinical): the synthetic, experimental
   model is force-staged to "Candidate" INSIDE THE THROWAWAY DATABASE ONLY,
   solely to prove that the loader and predictor execute and report model
   identity, version, artifact hash and supported categories. Its output is
   from a model trained on synthetic images; it is not validated, it is not a
   finding, and it is labelled ``clinical_use: false``.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib
import io
import json
import os
import pkgutil
import random
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone

WORK = tempfile.mkdtemp(prefix="issue192-e2e-")
os.environ["APP_ENV"] = "test"
os.environ["DATABASE_URL"] = f"sqlite:///{os.path.join(WORK, 'e2e.db')}"
os.environ["LUMENAI_MODEL_ARTIFACT_DIR"] = os.path.join(WORK, "model_artifacts")
os.environ["RETAIN_INSPECTION_IMAGES"] = "true"
os.makedirs(os.environ["LUMENAI_MODEL_ARTIFACT_DIR"], exist_ok=True)
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.makedirs(os.path.join(os.path.dirname(__file__), "..", "data"), exist_ok=True)

import app.db  # noqa: E402,F401  (import order: app.db before app.models avoids a cycle)
import app.models as _models_pkg  # noqa: E402

for _mod in pkgutil.iter_modules(_models_pkg.__path__):
    try:
        importlib.import_module(f"app.models.{_mod.name}")
    except Exception:  # pragma: no cover - optional model modules
        pass

from PIL import Image  # noqa: E402

from app.db.base import Base  # noqa: E402
from app.db.session import SessionLocal, engine  # noqa: E402
from app.models.baseline_library import BaselineLibraryEntry  # noqa: E402
from app.models.model_registry import ModelRegistryEntry  # noqa: E402
from app.services import baseline_image_library_service as bil  # noqa: E402
from app.services import baseline_image_registration_service as bir  # noqa: E402
from app.services.baseline_comparison_scoring_service import analyze_inspection  # noqa: E402
from app.services.ml.experimental_dataset_generator import generate_experimental_dataset  # noqa: E402
from app.services.ml.lens_model_registration import register_lens_model  # noqa: E402
from app.services.ml.lens_training_pipeline import run_lens_training  # noqa: E402
from app.services.ml.training_config import TrainingConfig  # noqa: E402
from app.services.ml.training_eligibility_service import compute_training_eligibility  # noqa: E402

Base.metadata.create_all(bind=engine)

ITYPE, MFR, MDL = "e2e_rigid_scope", "Example Manufacturer", "Model A"
MODEL_EXTS = (".onnx", ".pt", ".pth", ".safetensors", ".pkl", ".joblib", ".h5", ".tflite")


def _png(seed: int, size=(256, 256)) -> bytes:
    rnd = random.Random(seed)
    raw = bytes(rnd.getrandbits(8) for _ in range(size[0] * size[1] * 3))
    buf = io.BytesIO()
    Image.frombytes("RGB", size, raw).save(buf, format="PNG")
    return buf.getvalue()


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _inventory() -> dict:
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    tracked = subprocess.run(["git", "ls-files"], cwd=root, capture_output=True, text=True, check=True).stdout.split()
    weights = [p for p in tracked if p.lower().endswith(MODEL_EXTS)]
    lens = [p for p in tracked if "model_artifacts/" in p]
    return {
        "tracked_weight_files": weights,
        "tracked_lens_artifacts": lens,
        "real_data_validated_model_found": False if not (weights or lens) else None,
    }


def _entry(db):
    db.query(BaselineLibraryEntry).filter(BaselineLibraryEntry.instrument_category == ITYPE).delete()
    db.commit()
    e = BaselineLibraryEntry(
        udi="udi-e2e", instrument_category=ITYPE, manufacturer_name=MFR, model_name=MDL,
        baseline_type="manufacturer", baseline_version="1.0", approval_status="approved", approved_by="seed",
    )
    db.add(e)
    db.commit()
    db.refresh(e)
    return e


def _register(db, tenant, entry, photo, *, review=False, activate=False):
    reg = bir.register_manufacturer_reference_image(
        db, tenant_id=tenant, baseline_library_entry_id=entry.id, image_bytes=photo,
        content_type="image/png", uploaded_by="e2e-operator", source_organization="Manufacturer",
        source_reference="e2e-reference", usage_rights_attested=True, no_phi_attested=True,
    )
    if review:
        bil.review_baseline_image(
            db, link=reg["link"], reviewer="e2e-reviewer", reviewer_role="clinical_reviewer",
            decision="approve", rationale="e2e", source_verification="e2e",
            anatomy_compatibility_confirmed=True, image_quality_assessment="good",
        )
    if activate:
        bil.activate_baseline_image(db, link=reg["link"], actor="e2e-admin", actor_role="admin")
    return reg["link"]


def _analyze(db, tenant, photo, *, mdl=MDL):
    return analyze_inspection(
        db, instrument_type=ITYPE, tenant_id=tenant, has_image=True,
        image_sha256=_sha(photo) if photo else "0" * 64, image_bytes=photo,
        instrument_manufacturer=MFR, instrument_model=mdl, demo_scoring=False,
    )


def _summ(result: dict) -> dict:
    ev = result.get("baseline_evidence") or {}
    live = result.get("live_model_result") or {}
    return {
        "analysis_status": result.get("analysis_status"),
        "ai_status": (result.get("ai_analysis") or {}).get("status"),
        "ai_unavailable_reason_code": (result.get("ai_unavailable_reason") or {}).get("code"),
        "confidence": result.get("confidence"),
        "inspection_score": result.get("inspection_score"),
        "risk_level": result.get("risk_level"),
        "human_review_required": result.get("human_review_required"),
        "live_model_status": (live.get("model") or {}).get("status"),
        "baseline_image_status_code": ev.get("baseline_image_status_code"),
        "baseline_image_lifecycle_states": ev.get("baseline_image_lifecycle_states"),
        "baseline_image_active": ev.get("baseline_image_active"),
        "real_image_comparison_completed": ev.get("real_image_comparison_completed"),
        "comparison_status": ev.get("comparison_status"),
    }


def _train(db, tenant):
    generate_experimental_dataset(db, tenant_id=tenant, samples_per_class=6)
    run = run_lens_training(compute_training_eligibility(db, tenant_id=tenant), config=TrainingConfig(epochs=60))
    return register_lens_model(db, tenant_id=tenant, run=run, model_version="0.1.0-e2e-synthetic"), run


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    out: dict = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "environment": "isolated throwaway SQLite + temp artifact dir (no deployed system touched)",
        "git_head": subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip(),
        "inventory": _inventory(),
        "controls": {},
    }
    c = out["controls"]
    db = SessionLocal()
    try:
        photo = _png(7)

        # ── AI negative controls (baseline metadata present, images neutral) ──
        _entry(db)
        t = "e2e-tenant-a"
        c["N1_no_model_registered"] = _summ(_analyze(db, t, photo))

        model, run = _train(db, t)
        c["N2_synthetic_experimental_model"] = {
            **_summ(_analyze(db, t, photo)),
            "registry_stage": model.candidate_stage,
            "data_provenance": run.get("data_provenance"),
        }

        # Throwaway DB only: stage override to exercise the load path.
        model.candidate_stage = "Candidate"
        db.commit()
        path, checksum = model.artifact_path, model.artifact_checksum
        model.artifact_path = path + ".absent"
        db.commit()
        c["N3_artifact_missing"] = _summ(_analyze(db, t, photo))
        model.artifact_path, model.artifact_checksum = path, "0" * 64
        db.commit()
        c["N4_artifact_checksum_failed"] = _summ(_analyze(db, t, photo))
        model.artifact_checksum = checksum
        db.commit()
        c["N5_eligible_model_no_image_bytes"] = _summ(_analyze(db, t, None))

        # ── Engineering-mechanics control (NOT clinical) ──────────────────────
        with open(path, "rb") as fh:
            artifact_bytes = fh.read()
        artifact = json.loads(artifact_bytes)
        mech = _analyze(db, t, photo)
        live = mech.get("live_model_result") or {}
        c["M1_engineering_mechanics_synthetic_model"] = {
            "clinical_use": False,
            "label": "ENGINEERING MECHANICS ONLY — synthetic-trained experimental model force-staged in a "
                     "throwaway database; not validated; not a finding",
            "model_id": (live.get("model") or {}).get("model_id"),
            "model_version": (live.get("model") or {}).get("model_version"),
            "artifact_sha256": _sha(artifact_bytes),
            "artifact_sha256_matches_registry": _sha(artifact_bytes) == checksum,
            "preprocessing_version": (live.get("model") or {}).get("preprocessing_version"),
            "supported_categories": live.get("supported_categories"),
            "unsupported_categories": live.get("unsupported_categories"),
            "test_image_sha256": _sha(photo),
            "test_image_provenance": "procedurally generated random-pixel PNG (no PHI, no patient, no instrument)",
            "live_analysis_status": live.get("analysis_status"),
            "image_quality": live.get("image_quality"),
            "observation": live.get("observation"),
            "pipeline_outcome": _summ(mech),
            "eligible_classes_in_artifact": artifact.get("eligible_classes"),
        }
        model.candidate_stage = "Experimental"
        db.commit()

        # ── Baseline controls (independent of the model) ─────────────────────
        tb = "e2e-tenant-b"  # no model at all for this tenant
        e = _entry(db)
        ref = _png(21)
        _register(db, tb, e, ref)
        c["B1_reference_pending_review"] = _summ(_analyze(db, tb, ref))
        e = _entry(db)
        tb2 = "e2e-tenant-c"
        _register(db, tb2, e, ref, review=True)
        c["B2_reference_approved_not_active"] = _summ(_analyze(db, tb2, ref))
        e = _entry(db)
        tb3 = "e2e-tenant-d"
        _register(db, tb3, e, ref, review=True, activate=True)
        c["B3_active_reference_identity_mismatch"] = _summ(_analyze(db, tb3, ref, mdl="Model-A"))
        c["B4_active_reference_matching"] = _summ(_analyze(db, tb3, ref))
        c["B5_other_tenant_active_reference"] = _summ(_analyze(db, "e2e-tenant-e", ref))
    finally:
        db.close()

    n_models = 0
    db = SessionLocal()
    try:
        n_models = db.query(ModelRegistryEntry).filter(ModelRegistryEntry.candidate_stage != "Experimental").count()
    finally:
        db.close()
    out["models_left_promoted_in_throwaway_db"] = n_models
    out["verdict"] = (
        "BLOCKED_NO_VALIDATED_MODEL" if not (out["inventory"]["tracked_weight_files"]
                                             or out["inventory"]["tracked_lens_artifacts"]) else "REVIEW_INVENTORY"
    )
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2, sort_keys=True, default=str)
    print(json.dumps({"verdict": out["verdict"],
                      "controls": {k: v.get("ai_unavailable_reason_code") or v.get("pipeline_outcome", {}).get(
                          "ai_unavailable_reason_code") for k, v in c.items()},
                      "baseline": {k: v.get("baseline_image_status_code") for k, v in c.items()
                                   if k.startswith("B")}}, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    finally:
        engine.dispose()
        shutil.rmtree(WORK, ignore_errors=True)  # throwaway DB + artifacts
