"""Project Canvas — Section 16: Dataset Eligibility tests."""
from app.db.session import SessionLocal
from app.main import app
from app.services.dataset_eligibility_service import compute_entry_eligibility
from app.services.ml import dataset_registry
from fastapi.testclient import TestClient

client = TestClient(app)

AUTH_ADMIN = {"Authorization": "Bearer dev-token"}
TENANT = "default-tenant"


def _valid_metadata(**overrides):
    base = dict(
        instrument_family="scissors", manufacturer="Acme", facility="Test Hospital",
        operator="tech1", capture_device="phone", image_resolution="300x300",
    )
    base.update(overrides)
    return base


def _register(db, version_id, sha_suffix, **overrides):
    return dataset_registry.register_image(
        db, tenant_id=TENANT, dataset_version_id=version_id, retained_image_id=1,
        image_sha256="e" * 60 + sha_suffix, **_valid_metadata(**overrides),
    )


def test_not_reviewed_state_for_fresh_entry():
    db = SessionLocal()
    try:
        version = dataset_registry.create_dataset_version(db, tenant_id=TENANT, version_label="elig-v1")
        entry = _register(db, version.id, "0001", usage_rights="internal_use_approved")
        state, reason = compute_entry_eligibility(entry)
        assert state == "not_reviewed"
        assert reason
    finally:
        db.close()


def test_rights_restricted_when_usage_rights_blank():
    db = SessionLocal()
    try:
        version = dataset_registry.create_dataset_version(db, tenant_id=TENANT, version_label="elig-v2")
        entry = _register(db, version.id, "0002", usage_rights="")
        state, _ = compute_entry_eligibility(entry)
        assert state == "rights_restricted"
    finally:
        db.close()


def test_review_in_progress_state():
    db = SessionLocal()
    try:
        version = dataset_registry.create_dataset_version(db, tenant_id=TENANT, version_label="elig-v3")
        entry = _register(db, version.id, "0003", usage_rights="internal_use_approved")
        entry.review_status = "SECOND_REVIEW"
        db.commit()
        state, _ = compute_entry_eligibility(entry)
        assert state == "review_in_progress"
    finally:
        db.close()


def test_ground_truth_approved_awaiting_split():
    db = SessionLocal()
    try:
        version = dataset_registry.create_dataset_version(db, tenant_id=TENANT, version_label="elig-v4")
        entry = _register(db, version.id, "0004", usage_rights="internal_use_approved")
        entry.review_status = "APPROVED"
        entry.phi_verification = "verified"
        entry.training_eligibility = True
        db.commit()
        state, _ = compute_entry_eligibility(entry)
        assert state == "ground_truth_approved"
    finally:
        db.close()


def test_eligible_for_training_when_split_assigned():
    db = SessionLocal()
    try:
        version = dataset_registry.create_dataset_version(db, tenant_id=TENANT, version_label="elig-v5")
        entry = _register(db, version.id, "0005", usage_rights="internal_use_approved")
        entry.review_status = "APPROVED"
        entry.phi_verification = "verified"
        entry.training_eligibility = True
        entry.split_assignment = "train"
        db.commit()
        state, _ = compute_entry_eligibility(entry)
        assert state == "eligible_for_training"
    finally:
        db.close()


def test_excluded_when_quality_rejected_despite_approval():
    db = SessionLocal()
    try:
        version = dataset_registry.create_dataset_version(db, tenant_id=TENANT, version_label="elig-v6")
        entry = _register(db, version.id, "0006", usage_rights="internal_use_approved")
        entry.review_status = "APPROVED"
        entry.phi_verification = "verified"
        entry.training_eligibility = True
        entry.image_quality = "Reject"
        db.commit()
        state, reason = compute_entry_eligibility(entry)
        assert state == "excluded_from_training"
        assert "quality" in reason.lower()
    finally:
        db.close()


def test_research_only_when_not_training_eligible():
    db = SessionLocal()
    try:
        version = dataset_registry.create_dataset_version(db, tenant_id=TENANT, version_label="elig-v7")
        entry = _register(db, version.id, "0007", usage_rights="internal_use_approved")
        entry.review_status = "APPROVED"
        entry.phi_verification = "verified"
        entry.training_eligibility = False
        db.commit()
        state, _ = compute_entry_eligibility(entry)
        assert state == "research_only"
    finally:
        db.close()


def test_archived_state_takes_precedence():
    db = SessionLocal()
    try:
        version = dataset_registry.create_dataset_version(db, tenant_id=TENANT, version_label="elig-v8")
        entry = _register(db, version.id, "0008", usage_rights="")
        entry.review_status = "ARCHIVED"
        db.commit()
        state, _ = compute_entry_eligibility(entry)
        assert state == "archived"
    finally:
        db.close()


def test_dataset_eligibility_endpoint_counts_match_entries():
    r = client.get("/api/dataset-eligibility", headers=AUTH_ADMIN)
    assert r.status_code == 200
    body = r.json()
    assert body["entries_checked"] == len(body["entries"])
    assert sum(body["counts"].values()) == body["entries_checked"]
