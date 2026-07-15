"""Project Canvas — Sections 17 & 18: Dataset Release Builder + Export
Preview tests."""
from fastapi.testclient import TestClient

from app.db.session import SessionLocal
from app.main import app
from app.models.retained_image import RetainedImage
from app.services.ml import dataset_registry

client = TestClient(app)

AUTH_OPERATOR = {"Authorization": "Bearer operator-token"}
AUTH_MGR = {"Authorization": "Bearer manager-token"}
AUTH_ADMIN = {"Authorization": "Bearer dev-token"}
TENANT = "default-tenant"


def _valid_metadata(**overrides):
    base = dict(
        instrument_family="scissors", manufacturer="Acme", facility="Test Hospital",
        operator="tech1", capture_device="phone", image_resolution="300x300",
    )
    base.update(overrides)
    return base


def _make_retained_image(sha_suffix: str) -> int:
    db = SessionLocal()
    try:
        row = RetainedImage(
            tenant_id=TENANT, deident_name="test", instrument_type="scissors",
            content_type="image/png", size_bytes=100, sha256="z" * 56 + sha_suffix,
            exif_stripped=True, source="test", consent_recorded=True, uploaded_by="tester",
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return row.id
    finally:
        db.close()


_sha_counter = [0]


def _make_ground_truth_annotation() -> tuple[int, int]:
    """Registers a dataset entry through full GT approval and returns
    (annotation_id, dataset_entry_id)."""
    _sha_counter[0] += 1
    suffix = f"rel{_sha_counter[0]:04d}"
    image_id = _make_retained_image(suffix)

    db = SessionLocal()
    try:
        version = dataset_registry.create_dataset_version(db, tenant_id=TENANT, version_label="release-test-v1")
        entry = dataset_registry.register_image(
            db, tenant_id=TENANT, dataset_version_id=version.id, retained_image_id=image_id,
            image_sha256="z" * 56 + suffix, **_valid_metadata(), usage_rights="internal_use_approved",
        )
        entry.review_status = "APPROVED"
        entry.phi_verification = "verified"
        entry.training_eligibility = True
        db.commit()
        entry_id = entry.id
    finally:
        db.close()

    r = client.post(
        "/api/annotations",
        json={"retained_image_id": image_id, "primary_observation": "no_observable_abnormality"},
        headers=AUTH_OPERATOR,
    )
    annotation_id = r.json()["id"]

    client.post(
        f"/api/annotations/{annotation_id}/review/primary",
        json={"label": "no_observable_abnormality", "confidence": 0.9},
        headers=AUTH_MGR,
    )
    client.post(
        f"/api/annotations/{annotation_id}/review/secondary",
        json={"label": "no_observable_abnormality", "confidence": 0.85},
        headers=AUTH_ADMIN,
    )
    promote = client.post(f"/api/annotations/{annotation_id}/promote-ground-truth", headers=AUTH_ADMIN)
    assert promote.status_code == 200, promote.text
    return annotation_id, entry_id


def test_release_preview_includes_approved_ground_truth_candidate():
    annotation_id, entry_id = _make_ground_truth_annotation()

    r = client.get("/api/dataset-release/preview", headers=AUTH_ADMIN)
    assert r.status_code == 200, r.text
    body = r.json()
    assert annotation_id in body["candidate_annotation_ids"]
    assert entry_id in body["candidate_dataset_entry_ids"]
    assert body["candidate_count"] >= 1
    assert "split_preview" in body
    assert body["split_preview"]["leakage_free"] is True


def test_release_preview_excludes_non_ground_truth_annotations():
    image_id = _make_retained_image("rel2")
    r = client.post(
        "/api/annotations",
        json={"retained_image_id": image_id, "primary_observation": "no_observable_abnormality"},
        headers=AUTH_OPERATOR,
    )
    unreviewed_annotation_id = r.json()["id"]

    preview = client.get("/api/dataset-release/preview", headers=AUTH_ADMIN).json()
    assert unreviewed_annotation_id not in preview["candidate_annotation_ids"]


def test_export_preview_reports_summary_fields():
    _make_ground_truth_annotation()

    r = client.get("/api/dataset-release/export-preview?export_format=classification", headers=AUTH_ADMIN)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["export_format"] == "classification"
    assert body["record_count"] >= 1
    assert "class_distribution" in body
    assert "ground_truth_versions" in body
    assert "export_timestamp" in body


def test_export_preview_yolo_reports_missing_region_warning():
    _make_ground_truth_annotation()

    r = client.get("/api/dataset-release/export-preview?export_format=yolo", headers=AUTH_ADMIN)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["missing_data_warnings"], "whole-image annotations have no bounding box; must warn, not fabricate"


def test_export_preview_rejects_unknown_format():
    r = client.get("/api/dataset-release/export-preview?export_format=not_a_format", headers=AUTH_ADMIN)
    assert r.status_code == 422


def test_release_preview_requires_export_role():
    r = client.get("/api/dataset-release/preview", headers=AUTH_OPERATOR)
    assert r.status_code == 403
