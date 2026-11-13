"""TRC-001 — real (non-mocked) ingestion-path integration tests.

These exercise the ACTUAL `retain_image` service, `RetainedImage` persistence,
retrieval, checksum integrity and tenant isolation against the real (SQLite) test
database — not a mocked storage function. The image bytes here are LOCALLY GENERATED
JPEGs (not the real TRC-001 operator photographs, which are supplied only in the private
intake kit); they verify the ingestion machinery end-to-end so the pathway is proven for
when the authorized kit arrives.

The real TRC-001 operator kit is absent in this environment, so the runner returns a
BLOCKED report (tested below) — nothing is retained and no IDs are invented.
"""
from __future__ import annotations

import hashlib
import io
import json
import uuid

import pytest

from app.auth.context import AuthContext
from app.db.session import SessionLocal
from app.models.consent_record import ConsentRecord
from app.models.governance_approval import GovernanceApproval
from app.models.retained_image import RetainedImage
from app.models.user_role_assignment import UserRoleAssignment

from research.lens_vision import scientific_authorization as sa
from research.lens_vision.trc001_intake import TRC001_IMAGES, run_trc001_intake

TENANT = "trc001-tenant"
OTHER_TENANT = "trc001-other"


def _jpeg(color=(12, 34, 56), size=(64, 48)) -> bytes:
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format="JPEG", quality=92)
    return buf.getvalue()


@pytest.fixture()
def db():
    s = SessionLocal()
    created = {"users": [], "approvals": [], "consents": [], "retained": []}
    try:
        yield s, created
    finally:
        for i in created["retained"]:
            s.query(RetainedImage).filter(RetainedImage.id == i).delete()
        for u in created["users"]:
            s.query(UserRoleAssignment).filter(UserRoleAssignment.username == u).delete()
        for a in created["approvals"]:
            s.query(GovernanceApproval).filter(GovernanceApproval.id == a).delete()
        for c in created["consents"]:
            s.query(ConsentRecord).filter(ConsentRecord.id == c).delete()
        s.commit()
        s.close()


def _grant_authorization(s, created, dataset_id):
    s.add(UserRoleAssignment(username="dir@x", role="quality_director"))
    created["users"].append("dir@x")
    for rt in (sa.REQ_DATA_AUTHORIZATION, sa.REQ_RESEARCH_CONSENT):
        row = GovernanceApproval(tenant_id=TENANT, tenant_name="T", request_type=rt, target_resource="dataset",
                                 target_resource_id=dataset_id, requested_by="req@x", status="approved",
                                 reviewed_by="dir@x")
        s.add(row)
        s.commit()
        created["approvals"].append(row.id)
    c = ConsentRecord(id=str(uuid.uuid4()), tenant_id=TENANT, user_email="owner@x",
                      consent_type="benchmarking_contribution", granted=True)
    s.add(c)
    s.commit()
    created["consents"].append(c.id)


def _write_kit(tmp_path, *, include_both=True):
    """Write a LOCAL test intake kit (manifest + generated JPEGs). Not the real TRC-001 photos."""
    images = []
    for image_id, spec in TRC001_IMAGES.items():
        data = _jpeg(color=(10, 20, 30) if "EXT" in image_id else (40, 50, 60))
        fname = f"{image_id}.jpg"
        (tmp_path / fname).write_bytes(data)
        images.append({"image_id": image_id, "filename": fname,
                       "sha256": hashlib.sha256(data).hexdigest(),
                       "content_type": "image/jpeg", "modality": spec["modality"]})
        if not include_both:
            break
    (tmp_path / "manifest.json").write_text(json.dumps({"instrument_id": "TRC-001", "images": images}))
    return str(tmp_path)


# ── real ingestion-path verification (end-to-end, not mocked) ────────────────

def test_real_retain_and_retrieve_roundtrip(db, monkeypatch):
    s, created = db
    monkeypatch.setenv("RETAIN_INSPECTION_IMAGES", "1")
    from app.services.image_retention_service import retain_image
    data = _jpeg()
    row = retain_image(s, data=data, tenant_id=TENANT, instrument_type="TRC-001",
                       content_type="image/jpeg", source="trc001_test", uploaded_by="op", consent=True)
    assert row is not None and row.id is not None
    created["retained"].append(row.id)
    # Retrieve actual stored bytes; verify integrity + readability + tenant isolation.
    fetched = s.query(RetainedImage).filter(RetainedImage.tenant_id == TENANT, RetainedImage.id == row.id).first()
    assert fetched is not None and fetched.image_bytes
    assert hashlib.sha256(fetched.image_bytes).hexdigest() == row.sha256
    from research.lens_vision.trc001_intake import _validate_decode
    assert _validate_decode(fetched.image_bytes)[0] > 0
    assert s.query(RetainedImage).filter(RetainedImage.tenant_id == OTHER_TENANT,
                                         RetainedImage.id == row.id).first() is None


# ── runner: BLOCKED without kit / authorization ──────────────────────────────

def test_runner_blocked_without_kit(db):
    s, _ = db
    rep = run_trc001_intake(s, kit_dir=None, tenant_id=TENANT, dataset_id="TRC-001-DS")
    assert rep.status == "BLOCKED_MISSING_INTAKE_KIT" and rep.imported_count == 0
    for img in rep.images:
        assert img.retained_image_id is None and img.ingestion_successful is False
        assert img.ground_truth_status == "unknown" and img.research_training_eligible is False


def test_runner_blocked_without_authorization(db, tmp_path, monkeypatch):
    s, _ = db
    monkeypatch.setenv("RETAIN_INSPECTION_IMAGES", "1")
    kit = _write_kit(tmp_path)                       # kit present, but NO authorization records
    rep = run_trc001_intake(s, kit_dir=kit, tenant_id=TENANT, dataset_id="TRC-001-DS")
    assert rep.status == "BLOCKED_AUTHORIZATION" and rep.imported_count == 0
    assert rep.missing_documentation                 # lists what is missing
    for img in rep.images:
        assert img.retained_image_id is None         # nothing retained, no invented IDs
    # Confirm nothing was persisted for this tenant.
    assert s.query(RetainedImage).filter(RetainedImage.tenant_id == TENANT,
                                         RetainedImage.source == "trc001_research_intake").count() == 0


# ── runner: genuine end-to-end ingestion when authorized (proves the path) ───

def test_runner_ingests_when_authorized(db, tmp_path, monkeypatch):
    s, created = db
    monkeypatch.setenv("RETAIN_INSPECTION_IMAGES", "1")
    _grant_authorization(s, created, "TRC-001-DS")
    kit = _write_kit(tmp_path)
    rep = run_trc001_intake(s, kit_dir=kit, tenant_id=TENANT, dataset_id="TRC-001-DS",
                            auth=AuthContext(actor="dir@x", role="quality_director", tenant_id=TENANT))
    assert rep.status == "INGESTED" and rep.imported_count == 2
    for img in rep.images:
        created["retained"].append(img.retained_image_id)
        assert img.ingestion_successful is True and img.retained_image_id is not None
        assert img.checksum_match is True and img.retrieval_verified is True
        assert img.tenant_isolation_ok is True
        assert img.ground_truth_status == "unknown" and img.baseline_review == "pending_review"
        assert img.research_training_eligible is False
    # Borescope image flagged as a display photograph, not a raw export.
    bore = next(i for i in rep.images if i.image_id == "TRC-001-BORE-001")
    assert bore.is_borescope_display_photo is True and bore.raw_borescope_export is False


# ── safeguard: unknown-GT images excluded from normal-only fitting ───────────

def test_unknown_ground_truth_excluded_from_normal_only_fit(db):
    from research.lens_vision.anomaly_experiment import NormalOnlyViolation, run_anomaly_experiment
    from research.lens_vision.anomaly_localization import StubLocalizer
    from research.lens_vision.config import ResearchRunConfig
    from research.lens_vision.synthetic_fixtures import synthetic_anomaly_dataset

    normal, test = synthetic_anomaly_dataset(n_normal=6, n_anomalous=2)
    # A TRC-001-style record carries ground_truth_status 'unknown' -> never fits a normal model.
    normal[0]["ground_truth_status"] = "unknown"
    cfg = ResearchRunConfig(run_id="trc", seed=5, checkpoint_id="stub_backbone",
                            source_provenance_class="synthetic_experimental", embedder="stub_padim_like")
    with pytest.raises(NormalOnlyViolation):
        run_anomaly_experiment(normal, test, config=cfg, localizer=StubLocalizer())
