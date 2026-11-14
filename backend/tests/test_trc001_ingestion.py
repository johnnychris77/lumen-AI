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


def _seed_actor(s, created, *, username="dir@x", role="quality_director"):
    """Seed a real authenticated identity (UserRoleAssignment) and register cleanup."""
    if username not in created["users"]:
        s.add(UserRoleAssignment(username=username, role=role))
        s.commit()
        created["users"].append(username)
    return username


def _grant_authorization(s, created, dataset_id):
    """Grant the FULL governed authorization set for a dataset: an authenticated
    approver, institutional data-authorization, dataset research-use consent, the
    dataset-scoped retention approval, and a live tenant research-use consent."""
    _seed_actor(s, created)
    for rt in (sa.REQ_DATA_AUTHORIZATION, sa.REQ_RESEARCH_CONSENT, sa.REQ_RETENTION_AUTHORIZATION):
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


def _auth(tenant_id=TENANT, actor="dir@x", role="quality_director"):
    return AuthContext(actor=actor, role=role, tenant_id=tenant_id)


_KIT_SIZE = (64, 48)


def _write_kit(tmp_path, *, include_both=True, with_dimensions=False):
    """Write a LOCAL test intake kit (manifest + generated JPEGs). Not the real TRC-001 photos."""
    images = []
    for image_id, spec in TRC001_IMAGES.items():
        data = _jpeg(color=(10, 20, 30) if "EXT" in image_id else (40, 50, 60), size=_KIT_SIZE)
        fname = f"{image_id}.jpg"
        (tmp_path / fname).write_bytes(data)
        entry = {"image_id": image_id, "filename": fname,
                 "sha256": hashlib.sha256(data).hexdigest(),
                 "content_type": "image/jpeg", "modality": spec["modality"]}
        if with_dimensions:
            entry["width"], entry["height"] = _KIT_SIZE
        images.append(entry)
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
    # A trusted authenticated actor exists, isolating the no-kit path.
    s, created = db
    _seed_actor(s, created)
    rep = run_trc001_intake(s, kit_dir=None, tenant_id=TENANT, dataset_id="TRC-001-DS", auth=_auth())
    assert rep.status == "BLOCKED_MISSING_INTAKE_KIT" and rep.imported_count == 0
    for img in rep.images:
        assert img.retained_image_id is None and img.ingestion_successful is False
        assert img.ground_truth_status == "unknown" and img.research_training_eligible is False


def test_runner_blocked_without_authorization(db, tmp_path, monkeypatch):
    # Authenticated actor + kit present, but NO governance authorization records.
    s, created = db
    monkeypatch.setenv("RETAIN_INSPECTION_IMAGES", "1")
    _seed_actor(s, created)
    kit = _write_kit(tmp_path)
    rep = run_trc001_intake(s, kit_dir=kit, tenant_id=TENANT, dataset_id="TRC-001-DS", auth=_auth())
    assert rep.status == "BLOCKED_AUTHORIZATION" and rep.imported_count == 0
    assert rep.missing_documentation                 # lists what is missing
    for img in rep.images:
        assert img.retained_image_id is None         # nothing retained, no invented IDs
    # Confirm nothing was persisted for this tenant.
    assert s.query(RetainedImage).filter(RetainedImage.tenant_id == TENANT,
                                         RetainedImage.source == "trc001_research_intake").count() == 0


# ── runner hardening: untrusted actor / cross-tenant / retention authorization ─

def test_runner_refuses_auth_none(db, tmp_path, monkeypatch):
    # auth=None must be refused BEFORE the kit is read; nothing retained.
    s, created = db
    monkeypatch.setenv("RETAIN_INSPECTION_IMAGES", "1")
    _grant_authorization(s, created, "TRC-001-DS")   # full authorization present...
    kit = _write_kit(tmp_path)
    rep = run_trc001_intake(s, kit_dir=kit, tenant_id=TENANT, dataset_id="TRC-001-DS", auth=None)
    assert rep.status == "BLOCKED_AUTHORIZATION" and rep.imported_count == 0
    for img in rep.images:
        assert img.retained_image_id is None
    assert s.query(RetainedImage).filter(RetainedImage.tenant_id == TENANT,
                                         RetainedImage.source == "trc001_research_intake").count() == 0


def test_runner_refuses_cross_tenant_actor(db, tmp_path, monkeypatch):
    # An authenticated actor whose tenant != the ingestion tenant is refused.
    s, created = db
    monkeypatch.setenv("RETAIN_INSPECTION_IMAGES", "1")
    _grant_authorization(s, created, "TRC-001-DS")
    kit = _write_kit(tmp_path)
    rep = run_trc001_intake(s, kit_dir=kit, tenant_id=TENANT, dataset_id="TRC-001-DS",
                            auth=_auth(tenant_id=OTHER_TENANT))
    assert rep.status == "BLOCKED_AUTHORIZATION" and rep.imported_count == 0
    assert s.query(RetainedImage).filter(RetainedImage.tenant_id == TENANT,
                                         RetainedImage.source == "trc001_research_intake").count() == 0


def test_runner_requires_retention_authorization(db, tmp_path, monkeypatch):
    # Data-authorization + research-use consent granted, but the dataset RETENTION
    # approval is absent -> BLOCKED; consent=True alone does not authorize retention.
    s, created = db
    monkeypatch.setenv("RETAIN_INSPECTION_IMAGES", "1")
    _seed_actor(s, created)
    for rt in (sa.REQ_DATA_AUTHORIZATION, sa.REQ_RESEARCH_CONSENT):   # note: NO retention approval
        row = GovernanceApproval(tenant_id=TENANT, tenant_name="T", request_type=rt, target_resource="dataset",
                                 target_resource_id="TRC-001-DS", requested_by="req@x", status="approved",
                                 reviewed_by="dir@x")
        s.add(row)
        s.commit()
        created["approvals"].append(row.id)
    c = ConsentRecord(id=str(uuid.uuid4()), tenant_id=TENANT, user_email="owner@x",
                      consent_type="benchmarking_contribution", granted=True)
    s.add(c)
    s.commit()
    created["consents"].append(c.id)
    kit = _write_kit(tmp_path)
    rep = run_trc001_intake(s, kit_dir=kit, tenant_id=TENANT, dataset_id="TRC-001-DS", auth=_auth())
    assert rep.status == "BLOCKED_AUTHORIZATION" and rep.imported_count == 0
    assert s.query(RetainedImage).filter(RetainedImage.tenant_id == TENANT,
                                         RetainedImage.source == "trc001_research_intake").count() == 0


def test_runner_rejects_path_traversal_filename(db, tmp_path, monkeypatch):
    # A manifest filename that escapes the kit dir is rejected per-image; nothing retained.
    s, created = db
    monkeypatch.setenv("RETAIN_INSPECTION_IMAGES", "1")
    _grant_authorization(s, created, "TRC-001-DS")
    # Plant a real JPEG OUTSIDE the kit directory and point the manifest at it via '..'.
    outside = tmp_path / "outside"
    outside.mkdir()
    secret = _jpeg(size=_KIT_SIZE)
    (outside / "secret.jpg").write_bytes(secret)
    kit = tmp_path / "kit"
    kit.mkdir()
    images = [{"image_id": image_id, "filename": "../outside/secret.jpg" if i == 0 else f"{image_id}.jpg",
               "sha256": hashlib.sha256(secret).hexdigest(), "content_type": "image/jpeg",
               "modality": spec["modality"]}
              for i, (image_id, spec) in enumerate(TRC001_IMAGES.items())]
    # Second image is a legitimate in-kit file so only the traversal entry is rejected.
    legit = _jpeg(color=(40, 50, 60), size=_KIT_SIZE)
    (kit / f"{images[1]['image_id']}.jpg").write_bytes(legit)
    images[1]["sha256"] = hashlib.sha256(legit).hexdigest()
    (kit / "manifest.json").write_text(json.dumps({"instrument_id": "TRC-001", "images": images}))
    rep = run_trc001_intake(s, kit_dir=str(kit), tenant_id=TENANT, dataset_id="TRC-001-DS", auth=_auth())
    for img in rep.images:
        created["retained"].append(img.retained_image_id)
    traversal = rep.images[0]
    assert traversal.retained_image_id is None and traversal.ingestion_successful is False
    assert "unsafe_filename_rejected" in traversal.reason
    assert rep.status != "INGESTED" and rep.imported_count < len(TRC001_IMAGES)


def test_runner_rejects_dimension_mismatch(db, tmp_path, monkeypatch):
    # Manifest declares wrong dimensions -> the decoded image is rejected, not retained.
    s, created = db
    monkeypatch.setenv("RETAIN_INSPECTION_IMAGES", "1")
    _grant_authorization(s, created, "TRC-001-DS")
    kit = _write_kit(tmp_path, with_dimensions=True)
    manifest_path = tmp_path / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["images"][0]["width"] = _KIT_SIZE[0] + 100     # deliberately wrong
    manifest_path.write_text(json.dumps(manifest))
    rep = run_trc001_intake(s, kit_dir=kit, tenant_id=TENANT, dataset_id="TRC-001-DS", auth=_auth())
    for img in rep.images:
        created["retained"].append(img.retained_image_id)
    mismatched = next(i for i in rep.images if i.image_id == manifest["images"][0]["image_id"])
    assert mismatched.retained_image_id is None and mismatched.ingestion_successful is False
    assert "dimension_mismatch" in mismatched.reason
    assert rep.status != "INGESTED"


# ── runner: genuine end-to-end ingestion when authorized (proves the path) ───

def test_runner_ingests_when_authorized(db, tmp_path, monkeypatch):
    s, created = db
    monkeypatch.setenv("RETAIN_INSPECTION_IMAGES", "1")
    _grant_authorization(s, created, "TRC-001-DS")
    kit = _write_kit(tmp_path, with_dimensions=True)
    rep = run_trc001_intake(s, kit_dir=kit, tenant_id=TENANT, dataset_id="TRC-001-DS", auth=_auth())
    assert rep.status == "INGESTED" and rep.imported_count == 2
    for img in rep.images:
        created["retained"].append(img.retained_image_id)
        assert img.ingestion_successful is True and img.retained_image_id is not None
        assert img.checksum_match is True and img.retrieval_verified is True
        assert img.tenant_isolation_ok is True and img.tenant_access_authorized is True
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


# ── owner-attested privately controlled asset authorization (Phases B & C) ───

def _kit_hashes(tmp_path):
    """The SHA-256s the kit's manifest declares for the two TRC-001 images."""
    man = json.loads((tmp_path / "manifest.json").read_text())
    return [e["sha256"] for e in man["images"]]


def _grant_owner_attestation(s, created, dataset_id, image_hashes, *, owner="owner@x",
                             role="technician", status="approved", retention=True,
                             ownership=True, hashes_override=None):
    """Create a genuine-looking OWNER attestation GovernanceApproval authored by an
    authenticated owner. Nothing here is institutional or scientific approval."""
    _seed_actor(s, created, username=owner, role=role)
    payload = {
        "ownership_asserted": ownership,
        "permissible_research_use": "independent LumenAI engineering/provenance research",
        "retention_authorized": retention,
        "withdrawal_procedure": "owner emails governance to withdraw; records are deleted",
        "image_sha256": hashes_override if hashes_override is not None else list(image_hashes),
    }
    row = GovernanceApproval(tenant_id=TENANT, tenant_name="T", request_type=sa.REQ_OWNER_ATTESTATION,
                             target_resource="dataset", target_resource_id=dataset_id,
                             requested_by=owner, status=status, reviewed_by=owner,
                             requested_payload=json.dumps(payload))
    s.add(row)
    s.commit()
    created["approvals"].append(row.id)
    return row.id


def test_runner_ingests_owner_attested(db, tmp_path, monkeypatch):
    s, created = db
    monkeypatch.setenv("RETAIN_INSPECTION_IMAGES", "1")
    kit = _write_kit(tmp_path, with_dimensions=True)
    _grant_owner_attestation(s, created, "TRC-001-DS", _kit_hashes(tmp_path))
    rep = run_trc001_intake(s, kit_dir=kit, tenant_id=TENANT, dataset_id="TRC-001-DS",
                            auth=_auth(actor="owner@x", role="technician"),
                            authorization_basis="owner_attested")
    assert rep.status == "INGESTED" and rep.imported_count == 2
    assert rep.authorization_basis == "owner_attested"
    for img in rep.images:
        created["retained"].append(img.retained_image_id)
        assert img.ingestion_successful is True and img.retained_image_id is not None
        assert img.checksum_match is True and img.tenant_access_authorized is True
        # Owner attestation never confers verified-normal / scientific / clinical status.
        assert img.ground_truth_status == "unknown" and img.baseline_review == "pending_review"
        assert img.research_training_eligible is False
        assert "owner_attested" in img.authorization


def test_owner_attested_forged_context_refused(db, tmp_path, monkeypatch):
    # A manually constructed AuthContext with NO backing UserRoleAssignment cannot
    # independently establish authority, even with a valid attestation present.
    s, created = db
    monkeypatch.setenv("RETAIN_INSPECTION_IMAGES", "1")
    kit = _write_kit(tmp_path, with_dimensions=True)
    _grant_owner_attestation(s, created, "TRC-001-DS", _kit_hashes(tmp_path))
    rep = run_trc001_intake(s, kit_dir=kit, tenant_id=TENANT, dataset_id="TRC-001-DS",
                            auth=AuthContext(actor="ghost@nowhere", role="technician", tenant_id=TENANT),
                            authorization_basis="owner_attested")
    assert rep.status == "BLOCKED_AUTHORIZATION" and rep.imported_count == 0
    assert _no_trc_rows(s)


def test_owner_attested_non_authcontext_refused(db, tmp_path, monkeypatch):
    # A non-AuthContext object (duck-typed) is refused outright.
    import types
    s, created = db
    monkeypatch.setenv("RETAIN_INSPECTION_IMAGES", "1")
    kit = _write_kit(tmp_path, with_dimensions=True)
    _grant_owner_attestation(s, created, "TRC-001-DS", _kit_hashes(tmp_path))
    fake = types.SimpleNamespace(actor="owner@x", role="technician", tenant_id=TENANT)
    rep = run_trc001_intake(s, kit_dir=kit, tenant_id=TENANT, dataset_id="TRC-001-DS",
                            auth=fake, authorization_basis="owner_attested")
    assert rep.status == "BLOCKED_AUTHORIZATION" and rep.imported_count == 0
    assert _no_trc_rows(s)


def test_owner_attested_cross_tenant_refused(db, tmp_path, monkeypatch):
    s, created = db
    monkeypatch.setenv("RETAIN_INSPECTION_IMAGES", "1")
    kit = _write_kit(tmp_path, with_dimensions=True)
    _grant_owner_attestation(s, created, "TRC-001-DS", _kit_hashes(tmp_path))
    rep = run_trc001_intake(s, kit_dir=kit, tenant_id=TENANT, dataset_id="TRC-001-DS",
                            auth=_auth(tenant_id=OTHER_TENANT, actor="owner@x", role="technician"),
                            authorization_basis="owner_attested")
    assert rep.status == "BLOCKED_AUTHORIZATION" and rep.imported_count == 0
    assert _no_trc_rows(s)


def test_owner_attested_missing_ownership_evidence_refused(db, tmp_path, monkeypatch):
    # Authenticated owner, but NO attestation record -> blocked.
    s, created = db
    monkeypatch.setenv("RETAIN_INSPECTION_IMAGES", "1")
    _seed_actor(s, created, username="owner@x", role="technician")
    kit = _write_kit(tmp_path, with_dimensions=True)
    rep = run_trc001_intake(s, kit_dir=kit, tenant_id=TENANT, dataset_id="TRC-001-DS",
                            auth=_auth(actor="owner@x", role="technician"),
                            authorization_basis="owner_attested")
    assert rep.status == "BLOCKED_AUTHORIZATION" and rep.imported_count == 0
    assert _no_trc_rows(s)


def test_owner_attested_withdrawn_refused(db, tmp_path, monkeypatch):
    s, created = db
    monkeypatch.setenv("RETAIN_INSPECTION_IMAGES", "1")
    kit = _write_kit(tmp_path, with_dimensions=True)
    _grant_owner_attestation(s, created, "TRC-001-DS", _kit_hashes(tmp_path), status="withdrawn")
    rep = run_trc001_intake(s, kit_dir=kit, tenant_id=TENANT, dataset_id="TRC-001-DS",
                            auth=_auth(actor="owner@x", role="technician"),
                            authorization_basis="owner_attested")
    assert rep.status == "BLOCKED_AUTHORIZATION" and rep.imported_count == 0
    assert _no_trc_rows(s)


def test_owner_attested_retention_not_authorized_refused(db, tmp_path, monkeypatch):
    s, created = db
    monkeypatch.setenv("RETAIN_INSPECTION_IMAGES", "1")
    kit = _write_kit(tmp_path, with_dimensions=True)
    _grant_owner_attestation(s, created, "TRC-001-DS", _kit_hashes(tmp_path), retention=False)
    rep = run_trc001_intake(s, kit_dir=kit, tenant_id=TENANT, dataset_id="TRC-001-DS",
                            auth=_auth(actor="owner@x", role="technician"),
                            authorization_basis="owner_attested")
    assert rep.status == "BLOCKED_AUTHORIZATION" and rep.imported_count == 0
    assert _no_trc_rows(s)


def test_owner_attested_hash_mismatch_refused(db, tmp_path, monkeypatch):
    # Attestation covers different hashes than the images presented -> blocked.
    s, created = db
    monkeypatch.setenv("RETAIN_INSPECTION_IMAGES", "1")
    kit = _write_kit(tmp_path, with_dimensions=True)
    _grant_owner_attestation(s, created, "TRC-001-DS", _kit_hashes(tmp_path),
                             hashes_override=["deadbeef" * 8, "feedface" * 8])
    rep = run_trc001_intake(s, kit_dir=kit, tenant_id=TENANT, dataset_id="TRC-001-DS",
                            auth=_auth(actor="owner@x", role="technician"),
                            authorization_basis="owner_attested")
    assert rep.status == "BLOCKED_AUTHORIZATION" and rep.imported_count == 0
    assert _no_trc_rows(s)


def _no_trc_rows(s):
    return s.query(RetainedImage).filter(RetainedImage.tenant_id == TENANT,
                                         RetainedImage.source == "trc001_research_intake").count() == 0
