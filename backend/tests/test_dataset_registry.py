"""Dataset Registry & AI Model Development Foundation — Sprint 4 tests.

Covers: dataset registration, metadata validation, duplicate detection,
dataset versioning (immutability), annotation workflow, double-blind review,
image quality assessment (real pixel computation), split integrity
(leakage-free), model registration/promotion extensions, model card
generation, and the real training-pipeline execution.
"""
import io

from fastapi.testclient import TestClient
from PIL import Image

from app.db.session import SessionLocal
from app.main import app
from app.models.retained_image import RetainedImage
from app.services.ml import dataset_builder, dataset_registry, double_blind_review, image_quality
from app.services.ml.annotation_workflow import InvalidTransitionError, current_state, transition
from app.services.ml.evaluation import roc_auc
from app.services.ml.model_card import generate_model_card

client = TestClient(app)

AUTH_ADMIN = {"Authorization": "Bearer dev-token"}
AUTH_VIEWER = {"Authorization": "Bearer viewer-token"}
TENANT = "default-tenant"


def _png_bytes(brightness=128, textured=True, size=300):
    img = Image.new("RGB", (size, size), (brightness, brightness, brightness))
    if textured:
        px = img.load()
        for x in range(0, size, 8):
            for y in range(size):
                px[x, y] = (255 - brightness, 255 - brightness, 255 - brightness)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _make_retained_image(sha256_suffix: str, data: bytes | None = None) -> int:
    db = SessionLocal()
    try:
        row = RetainedImage(
            tenant_id=TENANT, deident_name="test", instrument_type="scissors",
            content_type="image/png", size_bytes=len(data or b""), sha256="r" * 56 + sha256_suffix,
            exif_stripped=True, source="test", consent_recorded=True, uploaded_by="tester",
            image_bytes=data,
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return row.id
    finally:
        db.close()


def _valid_metadata(**overrides):
    base = dict(
        instrument_family="scissors", manufacturer="Acme", facility="Test Hospital",
        operator="tech1", capture_device="phone", image_resolution="300x300",
    )
    base.update(overrides)
    return base


class TestDatasetRegistration:
    def test_register_image_success(self):
        db = SessionLocal()
        try:
            version = dataset_registry.create_dataset_version(db, tenant_id=TENANT, version_label="test-v-reg-1")
            entry = dataset_registry.register_image(
                db, tenant_id=TENANT, dataset_version_id=version.id, retained_image_id=1,
                image_sha256="s" * 64, **_valid_metadata(),
            )
            assert entry.id is not None
            assert entry.review_status == "UNLABELED"
            assert entry.dataset_version_label == "test-v-reg-1"
        finally:
            db.close()

    def test_metadata_validation_rejects_missing_fields(self):
        missing = dataset_registry.validate_metadata({"instrument_family": "", "manufacturer": "Acme"})
        assert "instrument_family" in missing
        assert "facility" in missing

    def test_register_image_missing_metadata_raises(self):
        db = SessionLocal()
        try:
            version = dataset_registry.create_dataset_version(db, tenant_id=TENANT, version_label="test-v-reg-2")
            try:
                dataset_registry.register_image(
                    db, tenant_id=TENANT, dataset_version_id=version.id, retained_image_id=2,
                    image_sha256="t" * 64, instrument_family="", manufacturer="", facility="",
                    operator="", capture_device="", image_resolution="",
                )
                assert False, "expected MetadataValidationError"
            except dataset_registry.MetadataValidationError as exc:
                assert "instrument_family" in exc.missing_fields
        finally:
            db.close()

    def test_duplicate_image_detection(self):
        db = SessionLocal()
        try:
            version = dataset_registry.create_dataset_version(db, tenant_id=TENANT, version_label="test-v-reg-3")
            dataset_registry.register_image(
                db, tenant_id=TENANT, dataset_version_id=version.id, retained_image_id=3,
                image_sha256="dupe" * 16, **_valid_metadata(),
            )
            try:
                dataset_registry.register_image(
                    db, tenant_id=TENANT, dataset_version_id=version.id, retained_image_id=4,
                    image_sha256="dupe" * 16, **_valid_metadata(),
                )
                assert False, "expected DuplicateImageError"
            except dataset_registry.DuplicateImageError as exc:
                assert exc.image_sha256 == "dupe" * 16
        finally:
            db.close()


class TestDatasetVersioning:
    def test_version_freeze_is_immutable(self):
        db = SessionLocal()
        try:
            version = dataset_registry.create_dataset_version(db, tenant_id=TENANT, version_label="test-v-freeze-1")
            dataset_registry.register_image(
                db, tenant_id=TENANT, dataset_version_id=version.id, retained_image_id=5,
                image_sha256="f" * 64, **_valid_metadata(),
            )
            frozen = dataset_registry.freeze_dataset_version(
                db, tenant_id=TENANT, dataset_version_id=version.id, frozen_by="admin",
            )
            assert frozen.frozen is True
            assert frozen.image_count_at_freeze == 1

            try:
                dataset_registry.register_image(
                    db, tenant_id=TENANT, dataset_version_id=version.id, retained_image_id=6,
                    image_sha256="g" * 64, **_valid_metadata(),
                )
                assert False, "expected DatasetVersionFrozenError"
            except dataset_registry.DatasetVersionFrozenError:
                pass
        finally:
            db.close()

    def test_create_version_is_idempotent_per_label(self):
        db = SessionLocal()
        try:
            v1 = dataset_registry.create_dataset_version(db, tenant_id=TENANT, version_label="test-v-idem")
            v2 = dataset_registry.create_dataset_version(db, tenant_id=TENANT, version_label="test-v-idem")
            assert v1.id == v2.id
        finally:
            db.close()


class TestAnnotationWorkflow:
    def test_valid_transition_sequence(self):
        db = SessionLocal()
        try:
            version = dataset_registry.create_dataset_version(db, tenant_id=TENANT, version_label="test-v-anno-1")
            entry = dataset_registry.register_image(
                db, tenant_id=TENANT, dataset_version_id=version.id, retained_image_id=7,
                image_sha256="h" * 64, **_valid_metadata(),
            )
            assert current_state(db, entry.id) == "UNLABELED"
            transition(db, tenant_id=TENANT, dataset_entry_id=entry.id, to_state="LABELED", reviewer="r1")
            transition(db, tenant_id=TENANT, dataset_entry_id=entry.id, to_state="SECOND_REVIEW", reviewer="r2")
            transition(db, tenant_id=TENANT, dataset_entry_id=entry.id, to_state="APPROVED", reviewer="r2")
            assert current_state(db, entry.id) == "APPROVED"
        finally:
            db.close()

    def test_invalid_transition_rejected(self):
        db = SessionLocal()
        try:
            version = dataset_registry.create_dataset_version(db, tenant_id=TENANT, version_label="test-v-anno-2")
            entry = dataset_registry.register_image(
                db, tenant_id=TENANT, dataset_version_id=version.id, retained_image_id=8,
                image_sha256="i" * 64, **_valid_metadata(),
            )
            try:
                transition(db, tenant_id=TENANT, dataset_entry_id=entry.id, to_state="APPROVED", reviewer="r1")
                assert False, "expected InvalidTransitionError"
            except InvalidTransitionError as exc:
                assert exc.from_state == "UNLABELED"
                assert exc.to_state == "APPROVED"
        finally:
            db.close()

    def test_api_transition_and_history(self):
        rid = _make_retained_image("api1", _png_bytes())
        vr = client.post("/api/dataset-registry/versions", json={"version_label": "test-v-anno-api"}, headers=AUTH_ADMIN)
        vid = vr.json()["id"]
        ir = client.post(
            "/api/dataset-registry/images",
            json={"dataset_version_id": vid, "retained_image_id": rid, "image_sha256": "j" * 64, **_valid_metadata()},
            headers=AUTH_ADMIN,
        )
        eid = ir.json()["id"]
        tr = client.post(
            f"/api/dataset-registry/images/{eid}/annotation-transition",
            json={"to_state": "LABELED", "comments": "first pass"}, headers=AUTH_ADMIN,
        )
        assert tr.status_code == 201
        bad = client.post(
            f"/api/dataset-registry/images/{eid}/annotation-transition",
            json={"to_state": "APPROVED"}, headers=AUTH_ADMIN,
        )
        assert bad.status_code == 409
        hist = client.get(f"/api/dataset-registry/images/{eid}/annotation-history", headers=AUTH_ADMIN)
        assert hist.status_code == 200
        assert hist.json()["current_state"] == "LABELED"
        assert len(hist.json()["events"]) == 1

    def test_viewer_cannot_transition(self):
        rid = _make_retained_image("api2", _png_bytes())
        vr = client.post("/api/dataset-registry/versions", json={"version_label": "test-v-anno-viewer"}, headers=AUTH_ADMIN)
        ir = client.post(
            "/api/dataset-registry/images",
            json={"dataset_version_id": vr.json()["id"], "retained_image_id": rid, "image_sha256": "k" * 64, **_valid_metadata()},
            headers=AUTH_ADMIN,
        )
        eid = ir.json()["id"]
        r = client.post(
            f"/api/dataset-registry/images/{eid}/annotation-transition",
            json={"to_state": "LABELED"}, headers=AUTH_VIEWER,
        )
        assert r.status_code == 403


class TestDoubleBlindReview:
    def test_agreement_computed_when_labels_match(self):
        db = SessionLocal()
        try:
            review = double_blind_review.start_review(db, tenant_id=TENANT, dataset_entry_id=9001)
            review = double_blind_review.submit_primary(db, review=review, reviewer="alice", label="debris")
            review = double_blind_review.submit_independent(db, review=review, reviewer="bob", label="debris")
            assert review.agreement is True
        finally:
            db.close()

    def test_disagreement_requires_adjudication_with_reason(self):
        db = SessionLocal()
        try:
            review = double_blind_review.start_review(db, tenant_id=TENANT, dataset_entry_id=9002)
            review = double_blind_review.submit_primary(db, review=review, reviewer="alice", label="debris")
            review = double_blind_review.submit_independent(db, review=review, reviewer="bob", label="clean")
            assert review.agreement is False
            try:
                double_blind_review.adjudicate(db, review=review, adjudicator="carol", resolution="debris", reason="")
                assert False, "expected ReasonRequiredError"
            except double_blind_review.ReasonRequiredError:
                pass
            resolved = double_blind_review.adjudicate(
                db, review=review, adjudicator="carol", resolution="debris", reason="visible residue confirmed",
            )
            assert resolved.resolution == "debris"
        finally:
            db.close()

    def test_independent_reviewer_cannot_be_same_as_primary(self):
        db = SessionLocal()
        try:
            review = double_blind_review.start_review(db, tenant_id=TENANT, dataset_entry_id=9003)
            review = double_blind_review.submit_primary(db, review=review, reviewer="alice", label="debris")
            try:
                double_blind_review.submit_independent(db, review=review, reviewer="alice", label="debris")
                assert False, "expected ReviewerCannotSelfIndependentError"
            except double_blind_review.ReviewerCannotSelfIndependentError:
                pass
        finally:
            db.close()

    def test_adjudication_not_required_when_agreed(self):
        db = SessionLocal()
        try:
            review = double_blind_review.start_review(db, tenant_id=TENANT, dataset_entry_id=9004)
            review = double_blind_review.submit_primary(db, review=review, reviewer="alice", label="clean")
            review = double_blind_review.submit_independent(db, review=review, reviewer="bob", label="clean")
            try:
                double_blind_review.adjudicate(db, review=review, adjudicator="carol", resolution="clean", reason="n/a")
                assert False, "expected AdjudicationNotRequiredError"
            except double_blind_review.AdjudicationNotRequiredError:
                pass
        finally:
            db.close()


class TestImageQualityAssessment:
    def test_sharp_bright_image_is_excellent_or_good(self):
        result = image_quality.assess_image_bytes(_png_bytes(brightness=150, textured=True))
        assert result["decodable"] is True
        assert result["overall_quality"] in ("Excellent", "Good")

    def test_tiny_image_is_rejected(self):
        result = image_quality.assess_image_bytes(_png_bytes(brightness=128, textured=False, size=20))
        assert result["overall_quality"] == "Reject"

    def test_undecodable_bytes_rejected_not_guessed(self):
        result = image_quality.assess_image_bytes(b"not an image")
        assert result["decodable"] is False
        assert result["overall_quality"] == "Reject"

    def test_reject_quality_excluded_from_training(self):
        assert image_quality.excluded_from_training("Reject") is True
        assert image_quality.excluded_from_training("Good") is False

    def test_api_quality_assessment_persists_and_updates_entry(self):
        rid = _make_retained_image("quality1", _png_bytes(brightness=150))
        vr = client.post("/api/dataset-registry/versions", json={"version_label": "test-v-quality"}, headers=AUTH_ADMIN)
        ir = client.post(
            "/api/dataset-registry/images",
            json={"dataset_version_id": vr.json()["id"], "retained_image_id": rid, "image_sha256": "l" * 64, **_valid_metadata()},
            headers=AUTH_ADMIN,
        )
        eid = ir.json()["id"]
        qr = client.post(f"/api/dataset-registry/images/{eid}/quality-assessment", headers=AUTH_ADMIN)
        assert qr.status_code == 201
        assert qr.json()["overall_quality"] in ("Excellent", "Good", "Marginal", "Poor")
        listed = client.get(f"/api/dataset-registry/images?dataset_version_id={vr.json()['id']}", headers=AUTH_ADMIN)
        entry = next(e for e in listed.json()["images"] if e["id"] == eid)
        assert entry["image_quality"] == qr.json()["overall_quality"]


class TestDatasetBuilderAndSplitIntegrity:
    def test_excludes_rejected_archived_unapproved_and_duplicates(self):
        db = SessionLocal()
        try:
            version = dataset_registry.create_dataset_version(db, tenant_id=TENANT, version_label="test-v-builder-1")

            def _approved_entry(rid_seed, sha, quality="Good", label="debris"):
                e = dataset_registry.register_image(
                    db, tenant_id=TENANT, dataset_version_id=version.id, retained_image_id=rid_seed,
                    image_sha256=sha, image_quality=quality, phi_verification="verified", **_valid_metadata(),
                )
                e.current_label = label
                e.training_eligibility = True
                db.commit()
                transition(db, tenant_id=TENANT, dataset_entry_id=e.id, to_state="LABELED", reviewer="r1")
                transition(db, tenant_id=TENANT, dataset_entry_id=e.id, to_state="SECOND_REVIEW", reviewer="r2")
                transition(db, tenant_id=TENANT, dataset_entry_id=e.id, to_state="APPROVED", reviewer="r2")
                return e

            good1 = _approved_entry(101, "aa" * 32)
            good2 = _approved_entry(102, "bb" * 32)
            rejected = _approved_entry(103, "cc" * 32, quality="Reject")

            eligible, excluded = dataset_builder.eligible_entries(db, tenant_id=TENANT, dataset_version_id=version.id)
            eligible_ids = {e.id for e in eligible}
            assert good1.id in eligible_ids
            assert good2.id in eligible_ids
            assert rejected.id not in eligible_ids
            assert excluded.get("rejected_quality") == 1
        finally:
            db.close()

    def test_build_training_dataset_split_has_no_leakage(self):
        db = SessionLocal()
        try:
            version = dataset_registry.create_dataset_version(db, tenant_id=TENANT, version_label="test-v-builder-2")
            for i in range(20):
                e = dataset_registry.register_image(
                    db, tenant_id=TENANT, dataset_version_id=version.id, retained_image_id=200 + i,
                    image_sha256=f"split{i:03d}" + "0" * 58, image_quality="Good", phi_verification="verified",
                    inspection_id=i, **_valid_metadata(),
                )
                e.current_label = "debris" if i % 2 == 0 else "none"
                e.training_eligibility = True
                db.commit()
                transition(db, tenant_id=TENANT, dataset_entry_id=e.id, to_state="LABELED", reviewer="r1")
                transition(db, tenant_id=TENANT, dataset_entry_id=e.id, to_state="SECOND_REVIEW", reviewer="r2")
                transition(db, tenant_id=TENANT, dataset_entry_id=e.id, to_state="APPROVED", reviewer="r2")

            result = dataset_builder.build_training_dataset(db, tenant_id=TENANT, dataset_version_id=version.id)
            assert result["leakage_free"] is True
            assert result["eligible_count"] == 20
            assert sum(result["split"]["counts"].values()) == 20

            entries = dataset_registry.list_entries(db, tenant_id=TENANT, dataset_version_id=version.id)
            assigned = [e.split_assignment for e in entries]
            assert all(a in ("train", "validation", "test") for a in assigned)
        finally:
            db.close()


class TestModelRegistryAndCard:
    def _register(self, model_id):
        return client.post(
            "/api/model-pipeline/models",
            json={"model_id": model_id, "model_version": "0.1.0", "model_type": "finding"},
            headers=AUTH_ADMIN,
        )

    def test_record_training_result_and_view(self):
        mid = self._register("test-m-training").json()["id"]
        r = client.post(
            f"/api/model-pipeline/models/{mid}/record-training-result",
            json={
                "architecture": "logistic_regression_pure_python", "framework": "pure_python_baseline",
                "hyperparameters": {"epochs": 500}, "git_commit": "abc123",
                "training_status": "trained", "training_metrics": {"accuracy": 0.9},
                "evaluation_metrics": {"accuracy": 0.85},
            },
            headers=AUTH_ADMIN,
        )
        assert r.status_code == 200
        body = r.json()
        assert body["architecture"] == "logistic_regression_pure_python"
        assert body["training_metrics"]["accuracy"] == 0.9

    def test_generate_model_card_contains_required_sections(self):
        mid = self._register("test-m-card").json()["id"]
        r = client.post(f"/api/model-pipeline/models/{mid}/generate-model-card", headers=AUTH_ADMIN)
        assert r.status_code == 200
        card = r.json()["model_card"]
        for section in ("Purpose", "Supported findings", "Unsupported findings", "Known limitations",
                        "Known failure modes", "Ethical considerations", "Clinical limitations"):
            assert section in card
        assert r.json()["model"]["model_card_generated"] is True

    def test_governance_flags_update(self):
        mid = self._register("test-m-flags").json()["id"]
        r = client.patch(
            f"/api/model-pipeline/models/{mid}/governance-flags",
            json={"documentation_complete": True, "clinical_review_complete": True, "metrics_approved": True},
            headers=AUTH_ADMIN,
        )
        assert r.status_code == 200
        assert r.json()["documentation_complete"] is True
        assert r.json()["clinical_review_complete"] is True
        assert r.json()["metrics_approved"] is True

    def test_promotion_readiness_blocks_until_full_checklist_satisfied(self):
        mid = self._register("test-m-readiness").json()["id"]
        r1 = client.get(f"/api/model-pipeline/models/{mid}/promotion-readiness?target_stage=pilot", headers=AUTH_ADMIN)
        assert r1.json()["allowed"] is False
        assert "model_card_generated" in r1.json()["unmet"]

        client.post(f"/api/model-pipeline/models/{mid}/generate-model-card", headers=AUTH_ADMIN)
        client.patch(
            f"/api/model-pipeline/models/{mid}/governance-flags",
            json={"documentation_complete": True, "clinical_review_complete": True, "metrics_approved": True},
            headers=AUTH_ADMIN,
        )
        client.post(
            f"/api/model-pipeline/models/{mid}/record-training-result",
            json={"evaluation_metrics": {"accuracy": 0.9}, "training_status": "trained"},
            headers=AUTH_ADMIN,
        )
        r2 = client.get(f"/api/model-pipeline/models/{mid}/promotion-readiness?target_stage=pilot", headers=AUTH_ADMIN)
        assert "model_card_generated" not in r2.json()["unmet"]
        assert "documentation_complete" not in r2.json()["unmet"]
        assert "evaluation_complete" not in r2.json()["unmet"]

    def test_model_card_service_directly(self):
        from app.models.model_registry import ModelRegistryEntry

        entry = ModelRegistryEntry(
            tenant_id=TENANT, model_id="direct-card", model_version="0.1", model_type="finding",
            known_limitations="Small sample.",
        )
        card = generate_model_card(entry)
        assert "Finding Classifier" in card
        assert "debris" in card  # part of the existing finding label space


class TestTrainingPipelineExecution:
    def test_trains_and_evaluates_with_real_images(self):
        from app.services.ml.training_execution import build_registry_payload, run_training_pipeline

        samples = []
        for i in range(6):
            samples.append({"id": f"pos-{i}", "image_bytes": _png_bytes(brightness=60, textured=True), "label": "debris", "inspection_id": i})
        for i in range(6):
            samples.append({"id": f"neg-{i}", "image_bytes": _png_bytes(brightness=200, textured=False), "label": "none", "inspection_id": 100 + i})

        result = run_training_pipeline(samples, positive_label="debris")
        assert result["training_status"] == "trained"
        assert result["leakage_free"] is True
        assert result["training_metrics"] is not None
        assert result["git_commit"]  # non-empty in a real git repo

        payload = build_registry_payload(result, model_id="pipeline-test", model_version="0.1.0")
        assert payload["training_status"] == "trained"
        assert payload["approval_status"] == "experimental"

    def test_insufficient_data_reported_honestly(self):
        from app.services.ml.training_execution import run_training_pipeline

        samples = [{"id": 1, "image_bytes": _png_bytes(), "label": "debris"}]
        result = run_training_pipeline(samples, positive_label="debris")
        assert result["training_status"] == "insufficient_data"
        assert result["training_metrics"] is None


class TestEvaluationRoc:
    def test_roc_auc_perfect_separation(self):
        assert roc_auc([0, 0, 0, 1, 1, 1], [0.1, 0.2, 0.3, 0.7, 0.8, 0.9]) == 1.0

    def test_roc_auc_none_without_both_classes(self):
        assert roc_auc([0, 0, 0], [0.1, 0.5, 0.9]) is None
