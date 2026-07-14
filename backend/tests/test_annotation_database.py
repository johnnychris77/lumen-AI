"""Annotation Database & Storage System — checklist tests.

Covers the 11 verbatim checklist items: annotation creation, annotation
versioning, reviewer workflow, disagreement workflow, adjudication,
immutable history, Digital Twin linkage, baseline linkage, export
generation, audit logging, permission enforcement.
"""
from __future__ import annotations

import json
import os

os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")

from app.db.session import SessionLocal
from app.models.audit_log import AuditLog
from app.models.baseline_library import BaselineLibraryEntry
from app.services import annotation_export_service, annotation_ground_truth_service, annotation_review_service
from app.services import annotation_service

TENANT = "annotation-test-tenant"


def _db():
    return SessionLocal()


def _create(db, **overrides):
    fields = dict(
        tenant_id=TENANT, actor="annotator@test", actor_role="operator",
        retained_image_id=1, instrument_family="forceps", manufacturer="Acme",
        primary_observation="probable_retained_debris", severity="moderate",
        location="tip", confidence=0.85,
    )
    fields.update(overrides)
    return annotation_service.create_annotation(db, **fields)


class TestAnnotationCreation:
    def test_create_assigns_permanent_ann_id(self):
        db = _db()
        try:
            annotation = _create(db)
            assert annotation.ann_id.startswith("ANN-")
            assert len(annotation.ann_id.split("-")) == 3
            assert annotation.current_version == 1
        finally:
            db.close()

    def test_invalid_region_type_rejected(self):
        db = _db()
        try:
            try:
                _create(db, region_type="not_a_real_region")
                assert False, "expected InvalidRegionTypeError"
            except annotation_service.InvalidRegionTypeError:
                pass
        finally:
            db.close()


class TestAnnotationVersioning:
    def test_update_creates_new_version(self):
        db = _db()
        try:
            annotation = _create(db)
            updated = annotation_service.update_annotation(
                db, annotation, editor="reviewer1@test", actor_role="spd_manager",
                reason="Corrected severity after review", severity="high",
            )
            assert updated.current_version == 2
            assert updated.severity == "high"

            history = annotation_service.version_history(db, annotation_id=annotation.id)
            assert len(history) == 2
            assert history[0].version_number == 1
            assert history[1].version_number == 2
            assert history[1].reason == "Corrected severity after review"
            assert history[1].previous_version_id == history[0].id
        finally:
            db.close()

    def test_update_requires_reason(self):
        db = _db()
        try:
            annotation = _create(db)
            try:
                annotation_service.update_annotation(
                    db, annotation, editor="reviewer1@test", actor_role="spd_manager",
                    reason="", severity="high",
                )
                assert False, "expected ValueError for blank reason"
            except ValueError:
                pass
        finally:
            db.close()


class TestImmutableHistory:
    def test_prior_version_snapshot_never_changes(self):
        db = _db()
        try:
            annotation = _create(db, severity="low")
            history_before = annotation_service.version_history(db, annotation_id=annotation.id)
            v1_snapshot_before = history_before[0].snapshot_json

            annotation_service.update_annotation(
                db, annotation, editor="reviewer1@test", actor_role="spd_manager",
                reason="Escalated", severity="critical",
            )

            history_after = annotation_service.version_history(db, annotation_id=annotation.id)
            assert len(history_after) == 2
            assert history_after[0].snapshot_json == v1_snapshot_before  # untouched
            v1_data = json.loads(history_after[0].snapshot_json)
            assert v1_data["severity"] == "low"  # original value preserved
        finally:
            db.close()


class TestReviewerWorkflow:
    def test_primary_then_secondary_agreement(self):
        db = _db()
        try:
            annotation = _create(db)
            review = annotation_review_service.start_review(db, tenant_id=TENANT, annotation_id=annotation.id)
            review = annotation_review_service.submit_primary(
                db, review, reviewer="reviewer1@test", actor_role="spd_manager",
                label="probable_retained_debris", confidence=0.9,
            )
            review = annotation_review_service.submit_secondary(
                db, review, reviewer="reviewer2@test", actor_role="spd_manager",
                label="probable_retained_debris", confidence=0.88,
            )
            assert review.agreement is True
        finally:
            db.close()

    def test_secondary_reviewer_cannot_be_same_as_primary(self):
        db = _db()
        try:
            annotation = _create(db)
            review = annotation_review_service.start_review(db, tenant_id=TENANT, annotation_id=annotation.id)
            review = annotation_review_service.submit_primary(
                db, review, reviewer="reviewer1@test", actor_role="spd_manager", label="x",
            )
            try:
                annotation_review_service.submit_secondary(
                    db, review, reviewer="reviewer1@test", actor_role="spd_manager", label="x",
                )
                assert False, "expected ReviewerCannotSelfSecondaryError"
            except annotation_review_service.ReviewerCannotSelfSecondaryError:
                pass
        finally:
            db.close()


class TestDisagreementWorkflow:
    def test_disagreement_computed_correctly(self):
        db = _db()
        try:
            annotation = _create(db)
            review = annotation_review_service.start_review(db, tenant_id=TENANT, annotation_id=annotation.id)
            review = annotation_review_service.submit_primary(
                db, review, reviewer="reviewer1@test", actor_role="spd_manager",
                label="probable_retained_debris",
            )
            review = annotation_review_service.submit_secondary(
                db, review, reviewer="reviewer2@test", actor_role="spd_manager",
                label="probable_corrosion_like_degradation",
            )
            assert review.agreement is False
        finally:
            db.close()

    def test_ground_truth_not_eligible_without_agreement_or_adjudication(self):
        db = _db()
        try:
            annotation = _create(db)
            review = annotation_review_service.start_review(db, tenant_id=TENANT, annotation_id=annotation.id)
            annotation_review_service.submit_primary(
                db, review, reviewer="reviewer1@test", actor_role="spd_manager", label="a",
            )
            review = annotation_review_service.submit_secondary(
                db, review, reviewer="reviewer2@test", actor_role="spd_manager", label="b",
            )
            try:
                annotation_ground_truth_service.promote_to_ground_truth(
                    db, annotation, review, actor="admin@test", actor_role="admin",
                )
                assert False, "expected GroundTruthNotEligibleError"
            except annotation_ground_truth_service.GroundTruthNotEligibleError:
                pass
        finally:
            db.close()


class TestAdjudication:
    def test_adjudication_resolves_disagreement_and_enables_ground_truth(self):
        db = _db()
        try:
            annotation = _create(db)
            review = annotation_review_service.start_review(db, tenant_id=TENANT, annotation_id=annotation.id)
            annotation_review_service.submit_primary(
                db, review, reviewer="reviewer1@test", actor_role="spd_manager", label="a",
            )
            review = annotation_review_service.submit_secondary(
                db, review, reviewer="reviewer2@test", actor_role="spd_manager", label="b",
            )
            review = annotation_review_service.adjudicate(
                db, review, adjudicator="clinical@test", actor_role="clinical_reviewer",
                resolution="a", reason="Adjudicator confirmed reviewer1's label after re-examining the image.",
            )
            assert review.resolution == "a"

            annotation = annotation_ground_truth_service.promote_to_ground_truth(
                db, annotation, review, actor="clinical@test", actor_role="clinical_reviewer",
            )
            assert annotation.ground_truth_status == "ACTIVE"
            assert annotation.ground_truth_version == 1
        finally:
            db.close()

    def test_adjudication_requires_real_disagreement(self):
        db = _db()
        try:
            annotation = _create(db)
            review = annotation_review_service.start_review(db, tenant_id=TENANT, annotation_id=annotation.id)
            annotation_review_service.submit_primary(
                db, review, reviewer="reviewer1@test", actor_role="spd_manager", label="a",
            )
            review = annotation_review_service.submit_secondary(
                db, review, reviewer="reviewer2@test", actor_role="spd_manager", label="a",
            )
            try:
                annotation_review_service.adjudicate(
                    db, review, adjudicator="clinical@test", actor_role="clinical_reviewer",
                    resolution="a", reason="not needed",
                )
                assert False, "expected AdjudicationNotRequiredError"
            except annotation_review_service.AdjudicationNotRequiredError:
                pass
        finally:
            db.close()


class TestDigitalTwinLinkage:
    def test_barcode_resolves_tracked_twin_id(self):
        db = _db()
        try:
            annotation = _create(db, instrument_barcode="BC555")
            assert annotation.digital_twin_id == "barcode:BC555"
        finally:
            db.close()

    def test_no_identifier_produces_untracked_twin_id(self):
        db = _db()
        try:
            annotation = _create(db)
            assert annotation.digital_twin_id.startswith("untracked:")
        finally:
            db.close()


class TestBaselineLinkage:
    def test_approved_baseline_resolved_at_creation(self):
        db = _db()
        try:
            db.add(BaselineLibraryEntry(
                instrument_category="forceps", manufacturer_name="Acme", model_name="F-1",
                baseline_type="manufacturer", approval_status="approved",
            ))
            db.commit()

            annotation = _create(db, baseline_type="manufacturer", baseline_version="1.0", baseline_similarity=0.9)
            assert annotation.baseline_id is not None
            assert annotation.baseline_type == "manufacturer"
        finally:
            db.close()


class TestExportGeneration:
    def test_json_export_only_includes_ground_truth(self, tmp_path):
        db = _db()
        try:
            annotation = _create(db, primary_observation="probable_corrosion_like_degradation")
            review = annotation_review_service.start_review(db, tenant_id=TENANT, annotation_id=annotation.id)
            annotation_review_service.submit_primary(
                db, review, reviewer="reviewer1@test", actor_role="spd_manager",
                label="probable_corrosion_like_degradation",
            )
            review = annotation_review_service.submit_secondary(
                db, review, reviewer="reviewer2@test", actor_role="spd_manager",
                label="probable_corrosion_like_degradation",
            )
            annotation_ground_truth_service.promote_to_ground_truth(
                db, annotation, review, actor="admin@test", actor_role="admin",
            )

            manifest = annotation_export_service.export_annotations(
                db, tenant_id=TENANT, export_format="json", output_dir=tmp_path,
            )
            # Other tests share this tenant/db and may have already promoted
            # their own annotations to Ground Truth — assert this export
            # includes ours and every record is genuinely ACTIVE, rather than
            # assuming we're the only Ground Truth annotation in the tenant.
            assert manifest["record_count"] >= 1
            assert all(r["ground_truth_status"] == "ACTIVE" for r in manifest["payload"]["records"])
            assert any(r["ann_id"] == annotation.ann_id for r in manifest["payload"]["records"])
            assert (tmp_path / f"annotations_{TENANT}.json").exists()
        finally:
            db.close()

    def test_yolo_export_never_fabricates_boxes_without_region_data(self, tmp_path):
        db = _db()
        try:
            annotation = _create(db, region_type="whole_image_classification")
            review = annotation_review_service.start_review(db, tenant_id=TENANT, annotation_id=annotation.id)
            annotation_review_service.submit_primary(
                db, review, reviewer="reviewer1@test", actor_role="spd_manager", label="probable_retained_debris",
            )
            review = annotation_review_service.submit_secondary(
                db, review, reviewer="reviewer2@test", actor_role="spd_manager", label="probable_retained_debris",
            )
            annotation_ground_truth_service.promote_to_ground_truth(
                db, annotation, review, actor="admin@test", actor_role="admin",
            )

            manifest = annotation_export_service.export_annotations(
                db, tenant_id=TENANT, export_format="yolo", output_dir=tmp_path,
            )
            record = manifest["payload"]["records"][0]
            assert record["annotation_available"] is False
            assert record["yolo_line"] is None
        finally:
            db.close()

    def test_unsupported_format_rejected(self):
        db = _db()
        try:
            try:
                annotation_export_service.export_annotations(
                    db, tenant_id=TENANT, export_format="not_a_real_format",
                )
                assert False, "expected UnsupportedExportFormatError"
            except annotation_export_service.UnsupportedExportFormatError:
                pass
        finally:
            db.close()


class TestAuditLogging:
    def test_creation_and_ground_truth_promotion_are_audited(self):
        db = _db()
        try:
            annotation = _create(db)
            review = annotation_review_service.start_review(db, tenant_id=TENANT, annotation_id=annotation.id)
            annotation_review_service.submit_primary(
                db, review, reviewer="reviewer1@test", actor_role="spd_manager", label="probable_retained_debris",
            )
            review = annotation_review_service.submit_secondary(
                db, review, reviewer="reviewer2@test", actor_role="spd_manager", label="probable_retained_debris",
            )
            annotation_ground_truth_service.promote_to_ground_truth(
                db, annotation, review, actor="admin@test", actor_role="admin",
            )

            created_events = db.query(AuditLog).filter(
                AuditLog.tenant_id == TENANT, AuditLog.action_type == "annotation_created",
                AuditLog.resource_id == annotation.ann_id,
            ).all()
            promoted_events = db.query(AuditLog).filter(
                AuditLog.tenant_id == TENANT, AuditLog.action_type == "annotation_ground_truth_promoted",
                AuditLog.resource_id == annotation.ann_id,
            ).all()
            assert len(created_events) >= 1
            assert len(promoted_events) >= 1
        finally:
            db.close()


class TestPermissionEnforcement:
    def test_viewer_cannot_adjudicate(self):
        db = _db()
        try:
            annotation = _create(db)
            review = annotation_review_service.start_review(db, tenant_id=TENANT, annotation_id=annotation.id)
            annotation_review_service.submit_primary(
                db, review, reviewer="reviewer1@test", actor_role="spd_manager", label="a",
            )
            review = annotation_review_service.submit_secondary(
                db, review, reviewer="reviewer2@test", actor_role="spd_manager", label="b",
            )
            try:
                annotation_review_service.adjudicate(
                    db, review, adjudicator="viewer@test", actor_role="viewer",
                    resolution="a", reason="attempted by a non-privileged role",
                )
                assert False, "expected PermissionDeniedError"
            except annotation_review_service.PermissionDeniedError:
                pass
        finally:
            db.close()

    def test_annotator_cannot_finalize_ground_truth(self):
        db = _db()
        try:
            annotation = _create(db)
            review = annotation_review_service.start_review(db, tenant_id=TENANT, annotation_id=annotation.id)
            annotation_review_service.submit_primary(
                db, review, reviewer="reviewer1@test", actor_role="spd_manager", label="a",
            )
            review = annotation_review_service.submit_secondary(
                db, review, reviewer="reviewer2@test", actor_role="spd_manager", label="a",
            )
            try:
                annotation_ground_truth_service.promote_to_ground_truth(
                    db, annotation, review, actor="annotator@test", actor_role="operator",
                )
                assert False, "expected PermissionDeniedError"
            except annotation_ground_truth_service.PermissionDeniedError:
                pass
        finally:
            db.close()

    def test_viewer_cannot_submit_review(self):
        db = _db()
        try:
            annotation = _create(db)
            review = annotation_review_service.start_review(db, tenant_id=TENANT, annotation_id=annotation.id)
            try:
                annotation_review_service.submit_primary(
                    db, review, reviewer="viewer@test", actor_role="viewer", label="a",
                )
                assert False, "expected PermissionDeniedError"
            except annotation_review_service.PermissionDeniedError:
                pass
        finally:
            db.close()
