"""Project Canvas — Section 25 backend/integration checklist.

Most of the 18 required checks are already exercised by the sprint-specific
test files this Canvas sprint added or extended:

  * authorized ingestion succeeds / duplicate warning / missing metadata
    rejected -> tests/test_dataset_ingestion.py
  * secondary review remains blind before submission -> tests/test_review_workspace.py
  * agreement enables GT eligibility / disagreement requires adjudication
    -> tests/test_reviewer_queues.py
  * unapproved baseline not presented as authoritative -> tests/test_review_workspace.py
  * region-dependent export does not fabricate annotations -> tests/test_dataset_release.py
  * same reviewer cannot do secondary / approved-annotation edit creates a
    new version / Ground Truth history remains immutable -> tests/test_annotation_database.py
  * frozen dataset version cannot be modified -> tests/test_dataset_registry.py

This file covers the remaining checklist items that don't already have a
dedicated test: cross-tenant access denial, primary-review persistence,
adjudication requiring a rationale, AI predictions never becoming Ground
Truth automatically, and rights/quality gates excluding an image from a
dataset release even when Ground-Truth-approved.
"""
from fastapi.testclient import TestClient

from app.db.session import SessionLocal
from app.main import app
from app.models.retained_image import RetainedImage
from app.services import annotation_service
from app.services.ml import dataset_registry

client = TestClient(app)

AUTH_OPERATOR = {"Authorization": "Bearer operator-token"}
AUTH_MGR = {"Authorization": "Bearer manager-token"}
AUTH_ADMIN = {"Authorization": "Bearer dev-token"}
TENANT = "default-tenant"
OTHER_TENANT = "other-tenant"


def _valid_metadata(**overrides):
    base = dict(
        instrument_family="scissors", manufacturer="Acme", facility="Test Hospital",
        operator="tech1", capture_device="phone", image_resolution="300x300",
    )
    base.update(overrides)
    return base


_sha_counter = [0]


def _make_retained_image(tenant_id: str = TENANT) -> int:
    _sha_counter[0] += 1
    db = SessionLocal()
    try:
        row = RetainedImage(
            tenant_id=tenant_id, deident_name="test", instrument_type="scissors",
            content_type="image/png", size_bytes=100,
            sha256="c" * 56 + f"chk{_sha_counter[0]:04d}",
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


# ── Cross-tenant access denied ──────────────────────────────────────────────

def test_cross_tenant_annotation_access_denied():
    image_id = _make_retained_image(OTHER_TENANT)
    db = SessionLocal()
    try:
        annotation = annotation_service.create_annotation(
            db, tenant_id=OTHER_TENANT, actor="other-tenant-user", actor_role="operator",
            retained_image_id=image_id, primary_observation="no_observable_abnormality",
        )
        annotation_id = annotation.id
    finally:
        db.close()

    # default-tenant caller cannot see an annotation belonging to another
    # tenant — the route filters by tenant, so a cross-tenant lookup
    # behaves as "not found", never leaking the row.
    r = client.get(f"/api/annotations/{annotation_id}", headers=AUTH_ADMIN)
    assert r.status_code == 404


def test_cross_tenant_dataset_image_list_is_isolated():
    db = SessionLocal()
    try:
        version = dataset_registry.create_dataset_version(db, tenant_id=OTHER_TENANT, version_label="chk-other-tenant-v1")
        entry = dataset_registry.register_image(
            db, tenant_id=OTHER_TENANT, dataset_version_id=version.id, retained_image_id=1,
            image_sha256="o" * 60 + "0001", **_valid_metadata(),
        )
        other_entry_id = entry.id
    finally:
        db.close()

    r = client.get("/api/dataset-registry/images", headers=AUTH_ADMIN)
    assert r.status_code == 200
    ids = {img["id"] for img in r.json()["images"]}
    assert other_entry_id not in ids


# ── Primary review persists ──────────────────────────────────────────────────

def test_primary_review_persists_and_is_retrievable():
    image_id = _make_retained_image()
    annotation_id = _create_annotation(image_id)

    submit = client.post(
        f"/api/annotations/{annotation_id}/review/primary",
        json={"label": "probable_retained_debris", "confidence": 0.77, "comments": "clear debris"},
        headers=AUTH_MGR,
    )
    assert submit.status_code == 201, submit.text

    fetched = client.get(f"/api/annotations/{annotation_id}/review", headers=AUTH_ADMIN)
    assert fetched.status_code == 200
    body = fetched.json()
    assert body["primary_reviewer"]
    assert body["primary_label"] == "probable_retained_debris"


# ── Adjudication requires a rationale ────────────────────────────────────────

def test_adjudication_without_reason_rejected():
    image_id = _make_retained_image()
    annotation_id = _create_annotation(image_id)
    client.post(
        f"/api/annotations/{annotation_id}/review/primary",
        json={"label": "no_observable_abnormality", "confidence": 0.9},
        headers=AUTH_MGR,
    )
    client.post(
        f"/api/annotations/{annotation_id}/review/secondary",
        json={"label": "probable_retained_debris", "confidence": 0.6},
        headers=AUTH_ADMIN,
    )

    r = client.post(
        f"/api/annotations/{annotation_id}/review/adjudicate",
        json={"resolution": "probable_retained_debris", "reason": ""},
        headers=AUTH_ADMIN,
    )
    assert r.status_code == 422


# ── AI prediction cannot become Ground Truth directly ────────────────────────

def test_ai_assisted_annotation_cannot_be_promoted_without_human_review():
    image_id = _make_retained_image()
    r = client.post(
        "/api/annotations",
        json={
            "retained_image_id": image_id, "primary_observation": "probable_corrosion_like_degradation",
            "model_version": "ai-model-v3",
        },
        headers=AUTH_OPERATOR,
    )
    annotation_id = r.json()["id"]

    promote = client.post(f"/api/annotations/{annotation_id}/promote-ground-truth", headers=AUTH_ADMIN)
    assert promote.status_code == 409


# ── Rights-restricted / rejected-quality images excluded from release ───────

def test_rights_restricted_image_excluded_from_release_candidates():
    image_id = _make_retained_image()
    db = SessionLocal()
    try:
        version = dataset_registry.create_dataset_version(db, tenant_id=TENANT, version_label="chk-rights-v1")
        entry = dataset_registry.register_image(
            db, tenant_id=TENANT, dataset_version_id=version.id, retained_image_id=image_id,
            image_sha256="r" * 60 + "0001", **_valid_metadata(), usage_rights="",
        )
        entry.review_status = "APPROVED"
        entry.phi_verification = "verified"
        entry.training_eligibility = True
        db.commit()
        entry_id = entry.id
    finally:
        db.close()

    annotation_id = _create_annotation(image_id)
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
    client.post(f"/api/annotations/{annotation_id}/promote-ground-truth", headers=AUTH_ADMIN)

    preview = client.get("/api/dataset-release/preview", headers=AUTH_ADMIN).json()
    assert entry_id not in preview["candidate_dataset_entry_ids"]


def test_rejected_quality_image_excluded_from_release_candidates():
    image_id = _make_retained_image()
    db = SessionLocal()
    try:
        version = dataset_registry.create_dataset_version(db, tenant_id=TENANT, version_label="chk-quality-v1")
        entry = dataset_registry.register_image(
            db, tenant_id=TENANT, dataset_version_id=version.id, retained_image_id=image_id,
            image_sha256="q" * 60 + "0002", **_valid_metadata(), usage_rights="internal_use_approved",
        )
        entry.review_status = "APPROVED"
        entry.phi_verification = "verified"
        entry.training_eligibility = True
        entry.image_quality = "Reject"
        db.commit()
        entry_id = entry.id
    finally:
        db.close()

    annotation_id = _create_annotation(image_id)
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
    client.post(f"/api/annotations/{annotation_id}/promote-ground-truth", headers=AUTH_ADMIN)

    preview = client.get("/api/dataset-release/preview", headers=AUTH_ADMIN).json()
    assert entry_id not in preview["candidate_dataset_entry_ids"]


# ── Frozen dataset version cannot be modified (ingestion path) ──────────────

def test_frozen_dataset_version_rejects_new_ingestion(monkeypatch):
    monkeypatch.setenv("RETAIN_INSPECTION_IMAGES", "true")
    db = SessionLocal()
    try:
        version = dataset_registry.create_dataset_version(db, tenant_id=TENANT, version_label="chk-frozen-v1")
        version_id = version.id
        dataset_registry.freeze_dataset_version(db, tenant_id=TENANT, dataset_version_id=version_id, frozen_by="admin")
    finally:
        db.close()

    r = client.post(
        "/api/dataset-ingestion/images",
        files={"image": ("frozen.png", b"\x89PNG\r\n\x1a\nfakepngbytes", "image/png")},
        data={
            "consent": "true", "dataset_version_id": str(version_id), "usage_rights": "internal_use_approved",
            **_valid_metadata(), "image_type": "after_use",
        },
        headers=AUTH_OPERATOR,
    )
    assert r.status_code == 409
