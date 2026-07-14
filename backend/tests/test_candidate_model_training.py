"""Genesis — Production Model Training, Scientific Validation & Model
Governance (Sprint 5) tests.

Covers: training reproducibility, dataset integrity (reject-gate), the
multi-class candidate training pipeline, error analysis, confidence
calibration, explainability, model-registry extensions, model-card
generation, the new Candidate promotion ladder, and artifact persistence.
"""
import io
import json

from fastapi.testclient import TestClient
from PIL import Image

from app.db.session import SessionLocal
from app.main import app
from app.models.dataset_governance import DatasetRegistryEntry
from app.models.model_registry import ModelRegistryEntry
from app.models.retained_image import RetainedImage
from app.models.shadow_prediction import ShadowPrediction
from app.services.ml import candidate_promotion, dataset_registry
from app.services.ml import shadow_clinical_review_board
from app.services.ml.candidate_training import (
    DatasetInvalidError,
    export_artifact,
    resolve_candidate_classes,
    run_candidate_training,
    run_full_candidate_pipeline,
)
from app.services.ml.error_analysis import analyze_errors
from app.services.ml.evaluation import calibration_report
from app.services.ml.explainability import explain_prediction
from app.services.ml.training_config import TrainingConfig

client = TestClient(app)
AUTH_ADMIN = {"Authorization": "Bearer dev-token"}
TENANT = "default-tenant"


def _img(brightness, size=300, textured=True):
    im = Image.new("RGB", (size, size), (brightness, brightness, brightness))
    if textured:
        px = im.load()
        for x in range(0, size, 8):
            for y in range(size):
                px[x, y] = (255 - brightness, 255 - brightness, 255 - brightness)
    buf = io.BytesIO()
    im.save(buf, format="PNG")
    return buf.getvalue()


def _diverse_samples(prefix: str, n_per_class: int = 8):
    """A real, diverse (facility/manufacturer/instrument), 3-class sample set."""
    samples = []
    sid = 0
    specs = [("debris", 60, True), ("corrosion", 140, True), ("no_actionable_finding", 220, False)]
    for label, brightness, textured in specs:
        for i in range(n_per_class):
            samples.append({
                "id": f"{prefix}-{sid}",
                "image_bytes": _img(brightness, textured=textured),
                "label": label,
                "inspection_id": sid,
                "facility": f"F{sid % 3}",
                "manufacturer": f"M{sid % 3}",
                "instrument_family": f"inst{sid % 3}",
                "anatomy_zone": "hinge",
                "image_sha256": f"{prefix}-sha-{sid}",
            })
            sid += 1
    return samples


class TestReproducibility:
    def test_identical_seed_reproduces_identical_weights_and_metrics(self):
        samples = _diverse_samples("repro")
        cfg = TrainingConfig(seed=7, epochs=150)
        run1 = run_candidate_training(samples, config=cfg)
        run2 = run_candidate_training(samples, config=cfg)
        assert run1["training_status"] == "trained"
        assert run1["weights_by_class"] == run2["weights_by_class"]
        assert run1["evaluation_metrics"] == run2["evaluation_metrics"]
        assert run1["config_hash"] == run2["config_hash"]

    def test_different_seed_can_change_split_and_augmentation(self):
        samples = _diverse_samples("repro2")
        run_a = run_candidate_training(samples, config=TrainingConfig(seed=1, epochs=50))
        run_b = run_candidate_training(samples, config=TrainingConfig(seed=2, epochs=50))
        assert run_a["config_hash"] != run_b["config_hash"]

    def test_config_hash_is_stable_and_sensitive(self):
        a = TrainingConfig(seed=1, learning_rate=0.3)
        b = TrainingConfig(seed=1, learning_rate=0.3)
        c = TrainingConfig(seed=1, learning_rate=0.5)
        assert a.config_hash() == b.config_hash()
        assert a.config_hash() != c.config_hash()


class TestDatasetIntegrityGate:
    def test_rejects_low_diversity_dataset(self):
        samples = []
        for i in range(20):
            samples.append({
                "id": i, "image_bytes": _img(100), "label": "debris" if i % 2 == 0 else "no_actionable_finding",
                "facility": "F1", "manufacturer": "M1", "instrument_family": "scissors",
                "image_sha256": f"lowdiv{i}",
            })
        try:
            run_candidate_training(samples, config=TrainingConfig(epochs=10))
            assert False, "expected DatasetInvalidError"
        except DatasetInvalidError as exc:
            assert not exc.report["diversity_check"]["facility_passed"]

    def test_rejects_duplicate_images(self):
        samples = _diverse_samples("dupcheck", n_per_class=6)
        samples[1]["image_sha256"] = samples[0]["image_sha256"]  # force a duplicate
        try:
            run_candidate_training(samples, config=TrainingConfig(epochs=10))
            assert False, "expected DatasetInvalidError"
        except DatasetInvalidError as exc:
            assert exc.report["duplicate_check"]["duplicate_count"] >= 1

    def test_accepts_diverse_valid_dataset(self):
        samples = _diverse_samples("valid1")
        result = run_candidate_training(samples, config=TrainingConfig(epochs=50))
        assert result["training_status"] == "trained"
        assert result["leakage_free"] is True


class TestCandidateScope:
    def test_blood_excluded_when_insufficient_samples(self):
        samples = _diverse_samples("noblood")
        classes = resolve_candidate_classes(samples)
        assert classes == ["debris", "corrosion", "no_actionable_finding"]
        assert "blood" not in classes

    def test_blood_included_when_sufficient_validated_samples(self):
        samples = _diverse_samples("withblood") + [
            {"id": f"blood-{i}", "label": "blood", "image_bytes": _img(90),
             "facility": f"F{i}", "manufacturer": f"M{i}", "instrument_family": "scissors"}
            for i in range(4)
        ]
        classes = resolve_candidate_classes(samples)
        assert "blood" in classes


class TestCandidateTrainingMetrics:
    def test_insufficient_data_reported_honestly(self):
        samples = _diverse_samples("scarce", n_per_class=1)
        result = run_candidate_training(samples, config=TrainingConfig(epochs=10))
        assert result["training_status"] == "insufficient_data"
        assert result["training_metrics"] is None
        assert result["evaluation_metrics"] is None

    def test_trained_run_has_full_metric_suite(self):
        samples = _diverse_samples("metrics1")
        result = run_candidate_training(samples, config=TrainingConfig(seed=3, epochs=150))
        assert result["training_status"] == "trained"
        test_metrics = result["evaluation_metrics"] or result["validation_metrics"]
        assert "confusion_matrix" in test_metrics
        assert "per_class" in test_metrics
        for cls_metrics in test_metrics["per_class"].values():
            assert "sensitivity" in cls_metrics
            assert "specificity" in cls_metrics
        assert "performance_breakdowns" in test_metrics
        assert set(test_metrics["performance_breakdowns"].keys()) >= {"facility", "manufacturer", "instrument_family", "anatomy_zone"}

    def test_error_analysis_and_calibration_present(self):
        samples = _diverse_samples("metrics2")
        result = run_candidate_training(samples, config=TrainingConfig(seed=5, epochs=150))
        assert result["error_analysis"] is not None
        assert "ranked_failure_modes" in result["error_analysis"]
        assert result["calibration_report"] is not None
        assert "expected_calibration_error" in result["calibration_report"]


class TestErrorAnalysisUnit:
    def test_false_negative_ranked_above_unknown(self):
        samples = [
            {"id": 1, "true_label": "debris", "predicted_label": "no_actionable_finding", "confidence": 0.9, "anatomy_zone": "hinge"},
            {"id": 2, "true_label": "debris", "predicted_label": "no_actionable_finding", "confidence": 0.9, "anatomy_zone": "hinge"},
            {"id": 3, "true_label": "no_actionable_finding", "predicted_label": "corrosion", "confidence": 0.6, "blur_flag": True, "anatomy_zone": "hinge"},
        ]
        report = analyze_errors(samples)
        assert report["total_errors"] == 3
        assert report["error_type_counts"]["false_negative"] == 2


class TestCalibrationUnit:
    def test_recommended_threshold_none_when_unmet(self):
        correct = [False] * 10
        conf = [0.9] * 10
        report = calibration_report(correct, conf, target_accuracy=0.8)
        assert report["recommended_threshold"] is None
        assert report["over_confident_bins"]


class TestExplainability:
    def test_contract_has_required_fields_and_no_visual_explanation(self):
        result = explain_prediction(
            predicted_class="debris", confidence=0.82, model_version="0.1.0",
            image_quality="Good", supported_classes=["debris", "corrosion", "no_actionable_finding"],
        )
        for field in ("supported_class", "confidence", "model_version", "image_quality", "known_limitations"):
            assert field in result
        assert result["human_review_required"] is True
        assert result["visual_explanation"]["available"] is False


class TestArtifactPersistence:
    def test_export_and_reload_artifact(self, tmp_path):
        samples = _diverse_samples("artifact1")
        result = run_candidate_training(samples, config=TrainingConfig(seed=9, epochs=100))
        path = export_artifact(result, model_id="test-artifact-model", model_version="0.1.0", artifact_dir=str(tmp_path))
        assert path
        with open(path) as f:
            payload = json.load(f)
        assert payload["weights_by_class"] == result["weights_by_class"]
        assert payload["config_hash"] == result["config_hash"]

    def test_no_artifact_written_for_insufficient_data(self, tmp_path):
        samples = _diverse_samples("artifact2", n_per_class=1)
        result = run_candidate_training(samples, config=TrainingConfig(epochs=10))
        path = export_artifact(result, model_id="test-artifact-model2", model_version="0.1.0", artifact_dir=str(tmp_path))
        assert path == ""


class TestFullPipelineAndRegistry:
    def test_full_pipeline_registers_model_with_genesis_fields(self, tmp_path):
        db = SessionLocal()
        try:
            samples = _diverse_samples("fullpipe1")
            row = run_full_candidate_pipeline(
                db, tenant_id=TENANT, samples=samples, config=TrainingConfig(seed=13, epochs=100),
                model_id="genesis-test-1", model_version="0.1.0", artifact_dir=str(tmp_path),
            )
            assert row.training_status == "trained"
            assert row.candidate_stage == "Candidate"
            assert row.artifact_path
            assert row.training_run_id
            assert row.architecture == "logistic_regression_one_vs_rest_pure_python"
            assert json.loads(row.evaluation_metrics) != {}
            assert json.loads(row.calibration_report) != {}
            assert json.loads(row.error_analysis_report) != {}
            assert "Intended use" in row.model_card_markdown
            assert "Out-of-scope use" in row.model_card_markdown
            assert "Human oversight requirements" in row.model_card_markdown
            assert "Version history" in row.model_card_markdown
            assert "Confidence calibration" in row.model_card_markdown
        finally:
            db.close()

    def test_insufficient_data_still_registers_honestly(self, tmp_path):
        db = SessionLocal()
        try:
            samples = _diverse_samples("fullpipe2", n_per_class=1)
            row = run_full_candidate_pipeline(
                db, tenant_id=TENANT, samples=samples, config=TrainingConfig(epochs=10),
                model_id="genesis-test-insufficient", model_version="0.1.0", artifact_dir=str(tmp_path),
            )
            assert row.training_status == "insufficient_data"
            assert row.candidate_stage == "Experimental"
            assert row.artifact_path == ""
        finally:
            db.close()


class TestPromotionRules:
    def _frozen_dataset_with_approved_entries(self, db, prefix: str):
        version = dataset_registry.create_dataset_version(db, tenant_id=TENANT, version_label=f"genesis-{prefix}")
        from app.services.ml.annotation_workflow import transition

        for i in range(3):
            retained = RetainedImage(
                tenant_id=TENANT, deident_name="t", instrument_type="scissors", content_type="image/png",
                size_bytes=10, sha256=f"{prefix}-r{i}", exif_stripped=True, source="test",
                consent_recorded=True, uploaded_by="t", image_bytes=_img(100),
            )
            db.add(retained)
            db.commit()
            db.refresh(retained)
            entry = dataset_registry.register_image(
                db, tenant_id=TENANT, dataset_version_id=version.id, retained_image_id=retained.id,
                image_sha256=f"{prefix}-sha-{i}", instrument_family="scissors", manufacturer="M",
                facility="F", operator="tech", capture_device="phone", image_resolution="300x300",
                phi_verification="verified",
            )
            transition(db, tenant_id=TENANT, dataset_entry_id=entry.id, to_state="LABELED", reviewer="r1")
            transition(db, tenant_id=TENANT, dataset_entry_id=entry.id, to_state="SECOND_REVIEW", reviewer="r2")
            transition(db, tenant_id=TENANT, dataset_entry_id=entry.id, to_state="APPROVED", reviewer="r2")
        frozen = dataset_registry.freeze_dataset_version(db, tenant_id=TENANT, dataset_version_id=version.id, frozen_by="admin")
        return frozen

    def _satisfy_shadow_evidence(self, db, *, model_id: str, model_version: str):
        """Shadow §14 — supplies the 4 additional items required to reach
        Validated Candidate: 30+ reconciled, agreeing shadow predictions
        (inspection volume + performance targets) and an approved clinical
        review board session. No SupervisorReview rows exist in this test,
        so sentinel_ai_health_service._detect_drift honestly reports no
        drift (insufficient data), satisfying model_drift_acceptable too."""
        for i in range(30):
            db.add(ShadowPrediction(
                tenant_id=TENANT, model_id=model_id, model_version=model_version,
                model_type="candidate_finding_multiclass", predicted_label="debris",
                predicted_confidence="0.9", supervisor_final_label="debris",
                agreed_with_human=True, comparison_category="agreement", revealed=True,
            ))
        db.commit()
        shadow_clinical_review_board.record_review_session(
            db, tenant_id=TENANT, model_id=model_id, model_version=model_version,
            reviewers=[{"name": "r1", "role": "clinical_advisor"}],
            readiness_assessment="Ready.", approved=True, decided_by="board",
        )

    def test_checklist_blocked_until_all_items_true(self, tmp_path):
        db = SessionLocal()
        try:
            version = self._frozen_dataset_with_approved_entries(db, "promo1")
            samples = _diverse_samples("promo1")
            model = run_full_candidate_pipeline(
                db, tenant_id=TENANT, samples=samples, config=TrainingConfig(seed=21, epochs=100),
                model_id="genesis-promo-1", model_version="0.1.0", dataset_version_id=version.id,
                artifact_dir=str(tmp_path),
            )
            checklist = candidate_promotion.evaluate_candidate_checklist(db, model)
            assert checklist["dataset_frozen"] is True
            assert checklist["annotation_complete"] is True
            assert checklist["evaluation_complete"] is True
            assert checklist["model_card_generated"] is True
            assert checklist["reproducible_training_confirmed"] is False
            assert checklist["error_analysis_reviewed"] is False
            assert checklist["governance_review_completed"] is False

            decision = candidate_promotion.evaluate_candidate_promotion(
                db, model=model, target_stage="Validated Candidate", approver="reviewer1",
            )
            assert decision["allowed"] is False
            assert "reproducible_training_confirmed" in decision["unmet"]
            # Shadow §14 — the 4 pilot-evidence items also gate Validated
            # Candidate, on top of the base 8.
            assert "inspection_volume_achieved" in decision["unmet"]
            assert "clinical_review_board_approved" in decision["unmet"]

            model.reproducible_training_confirmed = True
            model.error_analysis_reviewed = True
            model.governance_review_completed = True
            db.commit()

            # Still blocked: the base 8 are satisfied, but no shadow-mode
            # pilot evidence exists yet for this model.
            decision_partial = candidate_promotion.evaluate_candidate_promotion(
                db, model=model, target_stage="Validated Candidate", approver="reviewer1",
            )
            assert decision_partial["allowed"] is False
            assert "inspection_volume_achieved" in decision_partial["unmet"]

            self._satisfy_shadow_evidence(db, model_id=model.model_id, model_version=model.model_version)

            decision2 = candidate_promotion.evaluate_candidate_promotion(
                db, model=model, target_stage="Validated Candidate", approver="reviewer1",
            )
            assert decision2["allowed"] is True
        finally:
            db.close()

    def test_cannot_skip_stages(self, tmp_path):
        db = SessionLocal()
        try:
            row = ModelRegistryEntry(
                tenant_id=TENANT, model_id="skip-test", model_version="0.1", model_type="candidate_finding_multiclass",
                candidate_stage="Experimental",
            )
            db.add(row)
            db.commit()
            db.refresh(row)
            decision = candidate_promotion.evaluate_candidate_promotion(
                db, model=row, target_stage="Pilot", approver="reviewer1",
            )
            assert decision["allowed"] is False
            assert "one stage at a time" in decision["reason"]
        finally:
            db.close()

    def test_promote_requires_approver(self, tmp_path):
        db = SessionLocal()
        try:
            version = self._frozen_dataset_with_approved_entries(db, "promo2")
            samples = _diverse_samples("promo2")
            model = run_full_candidate_pipeline(
                db, tenant_id=TENANT, samples=samples, config=TrainingConfig(seed=27, epochs=100),
                model_id="genesis-promo-2", model_version="0.1.0", dataset_version_id=version.id,
                artifact_dir=str(tmp_path),
            )
            decision = candidate_promotion.evaluate_candidate_promotion(
                db, model=model, target_stage="Validated Candidate", approver=None,
            )
            assert decision["allowed"] is False
            assert "approver_required" in decision["unmet"]
        finally:
            db.close()


class TestApiEndToEnd:
    def test_run_candidate_training_and_promotion_via_api(self, tmp_path, monkeypatch):
        monkeypatch.setenv("LUMENAI_MODEL_ARTIFACT_DIR", str(tmp_path))
        vr = client.post("/api/dataset-registry/versions", json={"version_label": "genesis-api-1"}, headers=AUTH_ADMIN)
        vid = vr.json()["id"]

        db = SessionLocal()
        try:
            specs = [("debris", 60, True), ("corrosion", 140, True), ("no_actionable_finding", 220, False)]
            for label, brightness, textured in specs:
                for i in range(6):
                    retained = RetainedImage(
                        tenant_id=TENANT, deident_name="t", instrument_type="scissors", content_type="image/png",
                        size_bytes=10, sha256=f"api-{label}-{i}", exif_stripped=True, source="test",
                        consent_recorded=True, uploaded_by="t", image_bytes=_img(brightness, textured=textured),
                    )
                    db.add(retained)
                    db.commit()
                    db.refresh(retained)
                    ir = client.post(
                        "/api/dataset-registry/images",
                        json={
                            "dataset_version_id": vid, "retained_image_id": retained.id,
                            "image_sha256": f"api-sha-{label}-{i}", "instrument_family": f"inst{i % 3}",
                            "manufacturer": f"M{i % 3}", "facility": f"F{i % 3}", "operator": "tech",
                            "capture_device": "phone", "image_resolution": "300x300",
                            "anatomy_zone": "hinge", "phi_verification": "verified",
                        },
                        headers=AUTH_ADMIN,
                    )
                    assert ir.status_code == 201, ir.text
                    eid = ir.json()["id"]
                    entry = db.query(DatasetRegistryEntry).filter(DatasetRegistryEntry.id == eid).first()
                    entry.current_label = label
                    entry.training_eligibility = True
                    entry.image_quality = "Good"
                    db.commit()
                    client.post(f"/api/dataset-registry/images/{eid}/annotation-transition", json={"to_state": "LABELED"}, headers=AUTH_ADMIN)
                    client.post(f"/api/dataset-registry/images/{eid}/annotation-transition", json={"to_state": "SECOND_REVIEW"}, headers=AUTH_ADMIN)
                    client.post(f"/api/dataset-registry/images/{eid}/annotation-transition", json={"to_state": "APPROVED"}, headers=AUTH_ADMIN)
        finally:
            db.close()

        run = client.post(
            f"/api/dataset-registry/versions/{vid}/run-candidate-training",
            json={"model_id": "genesis-api-model", "model_version": "0.1.0", "seed": 17, "epochs": 100},
            headers=AUTH_ADMIN,
        )
        assert run.status_code == 201, run.text
        body = run.json()
        assert body["training_status"] == "trained"
        assert body["candidate_stage"] == "Candidate"
        mid = body["id"]

        client.post(f"/api/dataset-registry/versions/{vid}/freeze", headers=AUTH_ADMIN)

        checklist_before = client.get(f"/api/model-pipeline/models/{mid}/candidate-checklist", headers=AUTH_ADMIN)
        assert checklist_before.json()["checklist"]["dataset_frozen"] is True
        assert checklist_before.json()["checklist"]["reproducible_training_confirmed"] is False

        blocked = client.post(
            f"/api/model-pipeline/models/{mid}/candidate-promotion",
            json={"target_stage": "Validated Candidate"}, headers=AUTH_ADMIN,
        )
        assert blocked.status_code == 409

        client.patch(
            f"/api/model-pipeline/models/{mid}/candidate-flags",
            json={
                "error_analysis_reviewed": True, "reproducible_training_confirmed": True,
                "governance_review_completed": True, "reviewer": "dr-review",
                "clinical_review_status": "approved",
            },
            headers=AUTH_ADMIN,
        )
        # Shadow §14 — supply the pilot-evidence items (inspection volume,
        # performance targets, clinical review board approval) the
        # Validated Candidate gate additionally requires.
        db = SessionLocal()
        try:
            for i in range(30):
                db.add(ShadowPrediction(
                    tenant_id=TENANT, model_id="genesis-api-model", model_version="0.1.0",
                    model_type="candidate_finding_multiclass", predicted_label="debris",
                    predicted_confidence="0.9", supervisor_final_label="debris",
                    agreed_with_human=True, comparison_category="agreement", revealed=True,
                ))
            db.commit()
            shadow_clinical_review_board.record_review_session(
                db, tenant_id=TENANT, model_id="genesis-api-model", model_version="0.1.0",
                reviewers=[{"name": "r1", "role": "clinical_advisor"}],
                readiness_assessment="Ready.", approved=True, decided_by="board",
            )
        finally:
            db.close()

        promoted = client.post(
            f"/api/model-pipeline/models/{mid}/candidate-promotion",
            json={"target_stage": "Validated Candidate"}, headers=AUTH_ADMIN,
        )
        assert promoted.status_code == 200, promoted.text
        assert promoted.json()["promoted"] is True

        vp = client.get(f"/api/model-pipeline/models/{mid}/validation-package", headers=AUTH_ADMIN)
        assert vp.status_code == 200
        for key in ("training_report", "evaluation_report", "error_analysis_report", "calibration_report", "model_card", "approval_checklist"):
            assert key in vp.json()

    def test_dataset_integrity_rejection_returns_422(self):
        vr = client.post("/api/dataset-registry/versions", json={"version_label": "genesis-api-bad"}, headers=AUTH_ADMIN)
        vid = vr.json()["id"]
        # No eligible entries at all -> empty sample set -> integrity check fails on diversity.
        r = client.post(
            f"/api/dataset-registry/versions/{vid}/run-candidate-training",
            json={"model_id": "genesis-api-empty", "model_version": "0.1.0"},
            headers=AUTH_ADMIN,
        )
        assert r.status_code == 422
