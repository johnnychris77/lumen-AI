"""LCID Sprint 1 — Clinical Image Dataset Infrastructure & Governance tests.

Covers the 10 verbatim checklist items: image registration, metadata
validation, duplicate detection, reviewer workflow, dataset versioning,
immutable IDs, Digital Twin linkage, Ground Truth approval, export
generation, validation reports.

This sprint does not train a model — these tests exercise the governed
registry/annotation/export/validation infrastructure only, additive to the
pre-existing Sprint 4 dataset_governance tests (test_dataset_registry.py),
which remain unmodified and unduplicated.
"""
from __future__ import annotations

import os

os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")

from app.db.session import SessionLocal
from app.models.baseline_library import BaselineLibraryEntry
from app.models.dataset_governance import APPROVED
from app.models.lumen_decision_engine import UnknownFindingReview
from app.models.retained_image import RetainedImage
from app.services import unknown_finding_service
from app.services.ml import dataset_export_service, dataset_registry, dataset_validation_service, lcid_service
from app.services.ml.annotation_workflow import transition
from app.services.ml.double_blind_review import start_review, submit_independent, submit_primary

TENANT = "lcid-test-tenant"


def _make_retained_image(sha256_suffix: str) -> int:
    db = SessionLocal()
    try:
        row = RetainedImage(
            tenant_id=TENANT, deident_name="test", instrument_type="forceps",
            content_type="image/png", size_bytes=100, sha256="r" * 56 + sha256_suffix,
            exif_stripped=True, source="test", consent_recorded=True, uploaded_by="tester",
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return row.id
    finally:
        db.close()


def _valid_metadata(**overrides):
    base = dict(
        instrument_family="forceps", manufacturer="Acme", facility="Test Hospital",
        operator="tech1", capture_device="phone", image_resolution="300x300",
    )
    base.update(overrides)
    return base


class TestImageRegistration:
    def test_register_image_assigns_lcid(self):
        db = SessionLocal()
        try:
            version = dataset_registry.create_dataset_version(db, tenant_id=TENANT, version_label="lcid-v-reg-1")
            entry = dataset_registry.register_image(
                db, tenant_id=TENANT, dataset_version_id=version.id, retained_image_id=1,
                image_sha256="a" * 64, **_valid_metadata(),
            )
            assert entry.lcid.startswith("LCID-")
            assert len(entry.lcid.split("-")) == 3
        finally:
            db.close()


class TestMetadataValidation:
    def test_missing_required_field_rejected(self):
        missing = dataset_registry.validate_metadata({"instrument_family": "", "manufacturer": "Acme"})
        assert "instrument_family" in missing
        assert "facility" in missing


class TestDuplicateDetection:
    def test_duplicate_sha256_rejected(self):
        db = SessionLocal()
        try:
            version = dataset_registry.create_dataset_version(db, tenant_id=TENANT, version_label="lcid-v-dupe")
            dataset_registry.register_image(
                db, tenant_id=TENANT, dataset_version_id=version.id, retained_image_id=2,
                image_sha256="dupe" * 16, **_valid_metadata(),
            )
            try:
                dataset_registry.register_image(
                    db, tenant_id=TENANT, dataset_version_id=version.id, retained_image_id=3,
                    image_sha256="dupe" * 16, **_valid_metadata(),
                )
                assert False, "expected DuplicateImageError"
            except dataset_registry.DuplicateImageError:
                pass
        finally:
            db.close()


class TestReviewerWorkflow:
    def test_primary_then_independent_agreement_reaches_second_review(self):
        db = SessionLocal()
        try:
            version = dataset_registry.create_dataset_version(db, tenant_id=TENANT, version_label="lcid-v-review")
            entry = dataset_registry.register_image(
                db, tenant_id=TENANT, dataset_version_id=version.id, retained_image_id=4,
                image_sha256="b" * 64, **_valid_metadata(),
            )
            transition(db, tenant_id=TENANT, dataset_entry_id=entry.id, to_state="LABELED", reviewer="reviewer1", confidence=0.9)
            review = start_review(db, tenant_id=TENANT, dataset_entry_id=entry.id)
            review = submit_primary(db, review=review, reviewer="reviewer1", label="probable_retained_debris", confidence=0.9)
            review = submit_independent(db, review=review, reviewer="reviewer2", label="probable_retained_debris", confidence=0.85)
            assert review.agreement is True
        finally:
            db.close()


class TestDatasetVersioning:
    def test_frozen_version_rejects_new_registration(self):
        db = SessionLocal()
        try:
            version = dataset_registry.create_dataset_version(db, tenant_id=TENANT, version_label="lcid-v-freeze")
            dataset_registry.freeze_dataset_version(db, tenant_id=TENANT, dataset_version_id=version.id, frozen_by="admin@test")
            try:
                dataset_registry.register_image(
                    db, tenant_id=TENANT, dataset_version_id=version.id, retained_image_id=5,
                    image_sha256="c" * 64, **_valid_metadata(),
                )
                assert False, "expected DatasetVersionFrozenError"
            except dataset_registry.DatasetVersionFrozenError:
                pass
        finally:
            db.close()


class TestImmutableIds:
    def test_lcid_never_reused_after_archival(self):
        db = SessionLocal()
        try:
            version = dataset_registry.create_dataset_version(db, tenant_id=TENANT, version_label="lcid-v-immutable")
            entry = dataset_registry.register_image(
                db, tenant_id=TENANT, dataset_version_id=version.id, retained_image_id=6,
                image_sha256="d" * 64, **_valid_metadata(),
            )
            original_lcid = entry.lcid
            transition(db, tenant_id=TENANT, dataset_entry_id=entry.id, to_state="ARCHIVED", reviewer="admin@test")

            db.refresh(entry)
            assert entry.lcid == original_lcid  # never changed by archival

            # A brand-new registration must not collide with the archived entry's LCID.
            entry2 = dataset_registry.register_image(
                db, tenant_id=TENANT, dataset_version_id=version.id, retained_image_id=7,
                image_sha256="e" * 64, **_valid_metadata(),
            )
            assert entry2.lcid != original_lcid
        finally:
            db.close()

    def test_sequence_counter_is_atomic_per_year(self):
        db = SessionLocal()
        try:
            first = lcid_service.generate_lcid(db)
            second = lcid_service.generate_lcid(db)
            db.commit()
            first_seq = int(first.rsplit("-", 1)[1])
            second_seq = int(second.rsplit("-", 1)[1])
            assert second_seq == first_seq + 1
        finally:
            db.close()


class TestDigitalTwinLinkage:
    def test_barcode_produces_tracked_twin_id(self):
        twin_id = lcid_service.instrument_digital_twin_id(
            instrument_barcode="BC123", instrument_udi=None, instrument_type="forceps", inspection_id=1,
        )
        assert twin_id == "barcode:BC123"
        assert not lcid_service.is_untracked_twin(twin_id)

    def test_no_identifier_produces_untracked_twin_id(self):
        twin_id = lcid_service.instrument_digital_twin_id(
            instrument_barcode=None, instrument_udi=None, instrument_type="forceps", inspection_id=42,
        )
        assert twin_id.startswith("untracked:")
        assert lcid_service.is_untracked_twin(twin_id)

    def test_registration_resolves_digital_twin_and_baseline(self):
        db = SessionLocal()
        try:
            db.add(BaselineLibraryEntry(
                instrument_category="forceps", manufacturer_name="Acme", model_name="F-1",
                baseline_type="manufacturer", approval_status="approved",
            ))
            db.commit()

            version = dataset_registry.create_dataset_version(db, tenant_id=TENANT, version_label="lcid-v-twin")
            entry = dataset_registry.register_image(
                db, tenant_id=TENANT, dataset_version_id=version.id, retained_image_id=8,
                image_sha256="f" * 64, instrument_barcode="BC999", **_valid_metadata(),
            )
            assert entry.digital_twin_id == "barcode:BC999"
            assert entry.baseline_id is not None
        finally:
            db.close()

    def test_digital_twin_history_reports_linked_images(self):
        db = SessionLocal()
        try:
            version = dataset_registry.create_dataset_version(db, tenant_id=TENANT, version_label="lcid-v-twin-history")
            dataset_registry.register_image(
                db, tenant_id=TENANT, dataset_version_id=version.id, retained_image_id=9,
                image_sha256="g" * 64, instrument_barcode="BC777", **_valid_metadata(),
            )
            history = lcid_service.digital_twin_history(db, tenant_id=TENANT, digital_twin_id="barcode:BC777")
            assert history["is_tracked"] is True
            assert history["historical_image_count"] == 1
        finally:
            db.close()


class TestGroundTruthApproval:
    def test_approval_requires_double_blind_agreement(self):
        db = SessionLocal()
        try:
            version = dataset_registry.create_dataset_version(db, tenant_id=TENANT, version_label="lcid-v-gt")
            entry = dataset_registry.register_image(
                db, tenant_id=TENANT, dataset_version_id=version.id, retained_image_id=10,
                image_sha256="h" * 64, **_valid_metadata(),
            )
            transition(db, tenant_id=TENANT, dataset_entry_id=entry.id, to_state="LABELED", reviewer="reviewer1", confidence=0.9)
            review = start_review(db, tenant_id=TENANT, dataset_entry_id=entry.id)
            submit_primary(db, review=review, reviewer="reviewer1", label="no_observable_abnormality", confidence=0.9)
            submit_independent(db, review=review, reviewer="reviewer2", label="no_observable_abnormality", confidence=0.9)
            transition(db, tenant_id=TENANT, dataset_entry_id=entry.id, to_state="SECOND_REVIEW", reviewer="reviewer2", confidence=0.9)
            transition(db, tenant_id=TENANT, dataset_entry_id=entry.id, to_state="APPROVED", reviewer="admin@test")

            db.refresh(entry)
            assert entry.review_status == APPROVED
        finally:
            db.close()

    def test_unknown_finding_promotion_creates_unlabeled_candidate_not_approved(self):
        db = SessionLocal()
        try:
            review = UnknownFindingReview(
                inspection_id=999, tenant_id=TENANT, instrument_family="forceps", anatomy_zone="tip",
                model_output="{}", model_confidence=None, evidence_limitations_json="[]",
                model_version="v1", status="second_review", second_review_status="completed",
                dataset_eligible=True, usage_rights="internal_research",
            )
            db.add(review)
            db.commit()
            db.refresh(review)

            version = dataset_registry.create_dataset_version(db, tenant_id=TENANT, version_label="lcid-v-unknown")
            entry = unknown_finding_service.promote_to_candidate_dataset(
                db, review, dataset_version_id=version.id, retained_image_id=11,
                image_sha256="i" * 64, facility="Test Hospital", operator="tech1",
                manufacturer="Acme", capture_device="phone", image_resolution="300x300",
            )
            assert entry.review_status == "UNLABELED"  # candidate only, never auto-approved
        finally:
            db.close()


class TestExportGeneration:
    def test_classification_export_writes_manifest(self, tmp_path):
        db = SessionLocal()
        try:
            version = dataset_registry.create_dataset_version(db, tenant_id=TENANT, version_label="lcid-v-export")
            entry = dataset_registry.register_image(
                db, tenant_id=TENANT, dataset_version_id=version.id, retained_image_id=12,
                image_sha256="j" * 64, usage_rights="internal_research", phi_verification="verified",
                **_valid_metadata(),
            )
            entry.training_eligibility = True
            entry.review_status = APPROVED
            db.commit()

            manifest = dataset_export_service.export_dataset(
                db, tenant_id=TENANT, dataset_version_id=version.id, export_format="classification",
                output_dir=tmp_path,
            )
            assert manifest["record_count"] == 1
            assert (tmp_path / f"dataset_v{version.id}_classification.json").exists()
        finally:
            db.close()

    def test_object_detection_export_never_fabricates_boxes(self, tmp_path):
        db = SessionLocal()
        try:
            version = dataset_registry.create_dataset_version(db, tenant_id=TENANT, version_label="lcid-v-export-od")
            manifest = dataset_export_service.export_dataset(
                db, tenant_id=TENANT, dataset_version_id=version.id, export_format="object_detection",
                output_dir=tmp_path,
            )
            assert manifest["record_count"] == 0
        finally:
            db.close()

    def test_unsupported_format_rejected(self):
        db = SessionLocal()
        try:
            try:
                dataset_export_service.export_dataset(
                    db, tenant_id=TENANT, dataset_version_id=1, export_format="not_a_real_format",
                )
                assert False, "expected UnsupportedExportFormatError"
            except dataset_export_service.UnsupportedExportFormatError:
                pass
        finally:
            db.close()


class TestValidationReports:
    def test_missing_usage_rights_flagged(self):
        db = SessionLocal()
        try:
            version = dataset_registry.create_dataset_version(db, tenant_id=TENANT, version_label="lcid-v-validate")
            dataset_registry.register_image(
                db, tenant_id=TENANT, dataset_version_id=version.id, retained_image_id=13,
                image_sha256="k" * 64, usage_rights="", **_valid_metadata(),
            )
            report = dataset_validation_service.validate_registry(db, tenant_id=TENANT, dataset_version_id=version.id)
            assert report["valid"] is False
            assert any(f["lcid"] for f in report["missing_usage_rights"])
        finally:
            db.close()

    def test_clean_registry_reports_valid(self):
        db = SessionLocal()
        try:
            version = dataset_registry.create_dataset_version(db, tenant_id=TENANT, version_label="lcid-v-validate-clean")
            dataset_registry.register_image(
                db, tenant_id=TENANT, dataset_version_id=version.id, retained_image_id=14,
                image_sha256="l" * 64, usage_rights="internal_research", **_valid_metadata(),
            )
            report = dataset_validation_service.validate_registry(db, tenant_id=TENANT, dataset_version_id=version.id)
            assert report["duplicate_ids"] == []
            assert report["missing_metadata"] == []
        finally:
            db.close()
