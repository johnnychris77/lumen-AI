"""Project Canvas — Sections 10, 14, 15: blind secondary review, baseline
comparison, and the extended Digital Twin timeline."""
from fastapi.testclient import TestClient

from app.db.session import SessionLocal
from app.main import app
from app.models.baseline_library import BaselineLibraryEntry
from app.models.retained_image import RetainedImage
from app.services.ml import dataset_registry

client = TestClient(app)

AUTH_OPERATOR = {"Authorization": "Bearer operator-token"}
AUTH_MGR = {"Authorization": "Bearer manager-token"}
AUTH_ADMIN = {"Authorization": "Bearer dev-token"}
TENANT = "default-tenant"


def _make_retained_image(sha_suffix: str) -> int:
    db = SessionLocal()
    try:
        row = RetainedImage(
            tenant_id=TENANT, deident_name="test", instrument_type="scissors",
            content_type="image/png", size_bytes=100, sha256="r" * 56 + sha_suffix,
            exif_stripped=True, source="test", consent_recorded=True, uploaded_by="tester",
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return row.id
    finally:
        db.close()


def _create_annotation(image_id: int) -> int:
    r = client.post(
        "/api/annotations",
        json={"retained_image_id": image_id, "primary_observation": "no_observable_abnormality"},
        headers=AUTH_OPERATOR,
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


def test_blind_view_blocked_before_primary_review():
    image_id = _make_retained_image("bbb1")
    annotation_id = _create_annotation(image_id)

    r = client.get(f"/api/annotations/{annotation_id}/review/secondary/blind-view", headers=AUTH_MGR)
    assert r.status_code == 200
    body = r.json()
    assert body["eligible_to_submit_secondary"] is False
    assert "primary" in body["blocked_reason"].lower()
    assert "primary_label" not in body
    assert "agreement" not in body


def test_blind_view_never_exposes_primary_review_fields_after_submission():
    image_id = _make_retained_image("bbb2")
    annotation_id = _create_annotation(image_id)

    client.post(
        f"/api/annotations/{annotation_id}/review/primary",
        json={"label": "probable_retained_debris", "confidence": 0.8, "comments": "secret primary comment"},
        headers=AUTH_MGR,
    )

    r = client.get(f"/api/annotations/{annotation_id}/review/secondary/blind-view", headers=AUTH_ADMIN)
    assert r.status_code == 200
    body = r.json()
    assert body["eligible_to_submit_secondary"] is True
    assert "secret primary comment" not in str(body)
    assert "probable_retained_debris" not in str(body)
    for leaky_key in ("primary_label", "primary_confidence", "primary_comments", "agreement", "primary_reviewer"):
        assert leaky_key not in body


def test_blind_view_blocks_the_primary_reviewer_from_self_secondary():
    image_id = _make_retained_image("bbb3")
    annotation_id = _create_annotation(image_id)

    client.post(
        f"/api/annotations/{annotation_id}/review/primary",
        json={"label": "no_observable_abnormality", "confidence": 0.9},
        headers=AUTH_MGR,
    )

    r = client.get(f"/api/annotations/{annotation_id}/review/secondary/blind-view", headers=AUTH_MGR)
    body = r.json()
    assert body["eligible_to_submit_secondary"] is False
    assert "different reviewer" in body["blocked_reason"].lower()


def _valid_metadata(**overrides):
    base = dict(
        instrument_family="forceps", manufacturer="Acme", facility="Test Hospital",
        operator="tech1", capture_device="phone", image_resolution="300x300",
    )
    base.update(overrides)
    return base


def test_baseline_comparison_reports_unavailable_when_nothing_resolved():
    db = SessionLocal()
    try:
        version = dataset_registry.create_dataset_version(db, tenant_id=TENANT, version_label="baseline-cmp-v1")
        entry = dataset_registry.register_image(
            db, tenant_id=TENANT, dataset_version_id=version.id, retained_image_id=1,
            image_sha256="c" * 60 + "0001", **_valid_metadata(instrument_family="unlinked_instrument_xyz"),
        )
        entry_id = entry.id
    finally:
        db.close()

    r = client.get(f"/api/dataset-registry/images/{entry_id}/baseline-comparison", headers=AUTH_ADMIN)
    assert r.status_code == 200
    body = r.json()
    assert body["baselines"]["manufacturer"]["available"] is False
    assert body["baselines"]["digital_twin"]["available"] is False
    assert body["any_baseline_available"] is False


def test_baseline_comparison_resolves_approved_manufacturer_baseline():
    db = SessionLocal()
    try:
        db.add(BaselineLibraryEntry(
            instrument_category="forceps_baseline_test", manufacturer_name="Acme", model_name="F-1",
            baseline_type="manufacturer", approval_status="approved",
        ))
        db.commit()

        version = dataset_registry.create_dataset_version(db, tenant_id=TENANT, version_label="baseline-cmp-v2")
        entry = dataset_registry.register_image(
            db, tenant_id=TENANT, dataset_version_id=version.id, retained_image_id=2,
            image_sha256="c" * 60 + "0002", **_valid_metadata(instrument_family="forceps_baseline_test"),
        )
        entry_id = entry.id
        assert entry.baseline_id is not None
    finally:
        db.close()

    r = client.get(f"/api/dataset-registry/images/{entry_id}/baseline-comparison", headers=AUTH_ADMIN)
    body = r.json()
    assert body["baselines"]["manufacturer"]["available"] is True
    assert body["baselines"]["manufacturer"]["source"]["approval_status"] == "approved"
    assert body["any_baseline_available"] is True


def test_digital_twin_timeline_includes_per_image_detail():
    db = SessionLocal()
    try:
        version = dataset_registry.create_dataset_version(db, tenant_id=TENANT, version_label="twin-timeline-v1")
        dataset_registry.register_image(
            db, tenant_id=TENANT, dataset_version_id=version.id, retained_image_id=3,
            image_sha256="d" * 60 + "0001", instrument_barcode="BC-TIMELINE-1",
            image_type="after_use", **_valid_metadata(),
        )
    finally:
        db.close()

    r = client.get("/api/dataset-registry/digital-twin/barcode:BC-TIMELINE-1/history", headers=AUTH_ADMIN)
    assert r.status_code == 200
    body = r.json()
    assert body["historical_image_count"] == 1
    assert len(body["timeline"]) == 1
    assert body["timeline"][0]["image_type"] == "after_use"
