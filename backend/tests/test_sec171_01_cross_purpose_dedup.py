"""SEC-171-01 — cross-purpose deduplication (adversarial regression tests).

Finding under test: ``retain_image`` / ``retain_reference_image`` deduplicate on
``(tenant_id, sha256)`` alone, so identical bytes retained under one authorization can
be returned to, claimed by, modified by or deleted through a caller acting under a
different authorization.

Property asserted here: a retained image is only ever reused, reassigned, modified or
deleted inside the authorization and ownership scope it was originally retained under.

* a research intake never claims a pre-existing non-research image;
* a non-research caller (inspection, baseline reference, generic ML upload) never
  receives, discloses, labels or lists a research-intake image;
* one research basis (institutional) never claims another basis' (owner-attested) row;
* a generic caller can never mint a row carrying the research-intake source marker.

All image bytes are generated locally. No TRC-001 operator photograph is read, loaded
or committed. Ground truth is never asserted; research rows stay training-ineligible.
"""
from __future__ import annotations

import hashlib
import io
import json
import uuid

import pytest
from app.auth.context import AuthContext, build_oidc_auth_context
from app.db.session import SessionLocal
from app.main import app
from app.models.consent_record import ConsentRecord
from app.models.governance_approval import GovernanceApproval
from app.models.retained_image import ImageLabel, RetainedImage
from app.models.user_role_assignment import UserRoleAssignment
from app.services.image_retention_service import retain_image, retain_reference_image
from fastapi.testclient import TestClient
from research.lens_vision import scientific_authorization as sa
from research.lens_vision.trc001_intake import TRC001_IMAGES, run_trc001_intake

client = TestClient(app)

TENANT = "sec171-01-tenant"
RESEARCH_SOURCE = "trc001_research_intake"
OWNER = "sec171-owner@x"
OWNER_SUBJECT = "sub-sec171-owner"
TECH = "sec171-tech@x"
DIRECTOR = "sec171-dir@x"
AUTH_OPERATOR = {"Authorization": "Bearer operator-token", "x-tenant-id": TENANT}
AUTH_MANAGER = {"Authorization": "Bearer manager-token", "x-tenant-id": TENANT}
_KIT_SIZE = (64, 48)


def _jpeg(color) -> bytes:
    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", _KIT_SIZE, color).save(buf, format="JPEG", quality=92)
    return buf.getvalue()


def _association_model():
    """The per-owner association model exists only on later commits of the stack."""
    try:
        from app.models.research_image_authorization import ResearchImageAuthorization
    except ImportError:
        return None
    return ResearchImageAuthorization


@pytest.fixture()
def env(tmp_path, monkeypatch):
    """A synthetic two-image kit, an attested verified owner, and full cleanup."""
    monkeypatch.setenv("RETAIN_INSPECTION_IMAGES", "1")
    monkeypatch.setenv("TRC001_RESEARCH_API_ENABLED", "1")
    dataset_id = f"SEC171-01-{uuid.uuid4().hex[:10]}"
    monkeypatch.setenv("TRC001_DATASET_ID", dataset_id)

    images, raw = [], {}
    for index, (image_id, spec) in enumerate(TRC001_IMAGES.items()):
        seed = int(uuid.uuid4().hex[:4], 16)
        data = _jpeg(((seed + index * 37) % 256, (seed // 3) % 256, (seed // 7 + index) % 256))
        raw[image_id] = data
        (tmp_path / f"{image_id}.jpg").write_bytes(data)
        images.append({"image_id": image_id, "filename": f"{image_id}.jpg",
                       "sha256": hashlib.sha256(data).hexdigest(), "content_type": "image/jpeg",
                       "width": _KIT_SIZE[0], "height": _KIT_SIZE[1], "modality": spec["modality"]})
    (tmp_path / "manifest.json").write_text(json.dumps({"instrument_id": "TRC-001", "images": images}))

    s = SessionLocal()
    approvals: list[int] = []
    consents: list[str] = []
    users = [OWNER, TECH, DIRECTOR]
    for username, role in ((OWNER, "technician"), (TECH, "technician"), (DIRECTOR, "quality_director")):
        if s.query(UserRoleAssignment).filter(UserRoleAssignment.username == username).first() is None:
            s.add(UserRoleAssignment(username=username, role=role))
    s.commit()
    ctx = {"s": s, "kit": str(tmp_path), "dataset_id": dataset_id, "raw": raw,
           "hashes": [i["sha256"] for i in images], "approvals": approvals, "consents": consents}
    try:
        yield ctx
    finally:
        s.rollback()
        assoc = _association_model()
        if assoc is not None:
            s.query(assoc).filter(assoc.tenant_id == TENANT).delete(synchronize_session=False)
        s.query(ImageLabel).filter(ImageLabel.tenant_id == TENANT).delete(synchronize_session=False)
        s.query(RetainedImage).filter(RetainedImage.tenant_id == TENANT).delete(synchronize_session=False)
        for approval_id in approvals:
            s.query(GovernanceApproval).filter(GovernanceApproval.id == approval_id).delete()
        s.query(GovernanceApproval).filter(GovernanceApproval.tenant_id == TENANT).delete(
            synchronize_session=False)
        for consent_id in consents:
            s.query(ConsentRecord).filter(ConsentRecord.id == consent_id).delete()
        for username in users:
            s.query(UserRoleAssignment).filter(UserRoleAssignment.username == username).delete()
        s.commit()
        s.close()


def _owner_auth(actor=OWNER, subject=OWNER_SUBJECT):
    return build_oidc_auth_context(actor=actor, role="technician", tenant_id=TENANT,
                                   tenant_name="T", subject=subject, issuer="https://idp.local")


def _attest(env, *, owner=OWNER, subject=OWNER_SUBJECT, dataset_id=None) -> int:
    """A synthetic owner self-attestation for the synthetic kit. Not institutional
    approval, not independent verification, and not a real governance record."""
    payload = {
        "ownership_asserted": True,
        "permissible_research_use": "synthetic test fixture — no real asset",
        "retention_authorized": True,
        "withdrawal_procedure": "synthetic test fixture",
        "attestation_signed": True,
        "declarant_actor": owner,
        "declarant_subject": subject,
        "independent_ownership_verified": False,
        "institutional_approved": False,
        "image_sha256": list(env["hashes"]),
    }
    row = GovernanceApproval(
        tenant_id=TENANT, tenant_name="T", request_type=sa.REQ_OWNER_ATTESTATION,
        target_resource="dataset", target_resource_id=dataset_id or env["dataset_id"],
        requested_by=owner, status="approved", reviewed_by=owner,
        requested_payload=json.dumps(payload))
    env["s"].add(row)
    env["s"].commit()
    env["approvals"].append(row.id)
    return row.id


def _grant_institutional(env, dataset_id: str) -> None:
    s = env["s"]
    for request_type in (sa.REQ_DATA_AUTHORIZATION, sa.REQ_RESEARCH_CONSENT, sa.REQ_RETENTION_AUTHORIZATION):
        row = GovernanceApproval(
            tenant_id=TENANT, tenant_name="T", request_type=request_type, target_resource="dataset",
            target_resource_id=dataset_id, requested_by="sec171-req@x", status="approved",
            reviewed_by=DIRECTOR)
        s.add(row)
        s.commit()
        env["approvals"].append(row.id)
    consent = ConsentRecord(id=str(uuid.uuid4()), tenant_id=TENANT, user_email=OWNER,
                            consent_type="benchmarking_contribution", granted=True)
    s.add(consent)
    s.commit()
    env["consents"].append(consent.id)


def _owner_intake(env, auth=None):
    return run_trc001_intake(
        env["s"], kit_dir=env["kit"], tenant_id=TENANT, dataset_id=env["dataset_id"],
        auth=auth or _owner_auth(), authorization_basis="owner_attested")


def _ingested_ids(report) -> list[int]:
    return [i.retained_image_id for i in report.images if i.retained_image_id is not None]


def _snapshot(row: RetainedImage) -> dict:
    return {
        "source": row.source, "uploaded_by": row.uploaded_by, "instrument_type": row.instrument_type,
        "research_dataset_id": row.research_dataset_id or "",
        "research_owner_subject": row.research_owner_subject or "",
        "research_attestation_id": row.research_attestation_id,
        "label_status": row.label_status, "sha256": row.sha256,
        "bytes_sha256": hashlib.sha256(row.image_bytes or b"").hexdigest(),
    }


def _reload(env, image_id: int) -> RetainedImage | None:
    env["s"].expire_all()
    return env["s"].query(RetainedImage).filter(RetainedImage.id == image_id).first()


def _associations_for(env, image_id: int) -> int:
    assoc = _association_model()
    if assoc is None:
        return 0
    return env["s"].query(assoc).filter(assoc.retained_image_id == image_id).count()


def _preexisting(env, kind: str) -> RetainedImage:
    data = env["raw"]["TRC-001-EXT-001"]
    if kind == "baseline_reference":
        return retain_reference_image(
            env["s"], data=data, tenant_id=TENANT, instrument_type="trocar",
            content_type="image/jpeg", uploaded_by=TECH, usage_rights_attested=True)
    return retain_image(
        env["s"], data=data, tenant_id=TENANT, instrument_type="trocar",
        content_type="image/jpeg", source=kind, uploaded_by=TECH, consent=True)


# ── a research intake never claims a pre-existing non-research image ──────────

@pytest.mark.parametrize("kind", ["inspection", "baseline_reference", "dataset_ingestion"])
def test_research_intake_never_reuses_a_preexisting_non_research_image(env, kind):
    pre = _preexisting(env, kind)
    assert pre is not None and pre.source == kind
    before = _snapshot(pre)
    _attest(env)

    report = _owner_intake(env)

    # The pre-existing row is not reported as a research-ingested image ...
    assert pre.id not in _ingested_ids(report)
    # ... is not modified or reassigned ...
    after = _reload(env, pre.id)
    assert after is not None and _snapshot(after) == before
    # ... and no research authorization is attached to it.
    assert _associations_for(env, pre.id) == 0


@pytest.mark.parametrize("kind", ["inspection", "baseline_reference"])
def test_owner_withdrawal_never_deletes_a_preexisting_non_research_image(env, kind):
    from app.routes.trc001_research import withdraw_owner_attestation

    pre = _preexisting(env, kind)
    before = _snapshot(pre)
    _attest(env)
    _owner_intake(env)

    withdraw_owner_attestation(auth=_owner_auth(), db=env["s"])

    after = _reload(env, pre.id)
    assert after is not None, "a non-research image was deleted by a research withdrawal"
    assert _snapshot(after) == before


# ── a non-research caller never receives a research-intake image ──────────────

def _ingest_and_get_research_ids(env) -> list[int]:
    _attest(env)
    report = _owner_intake(env)
    assert report.status == "INGESTED", report.to_dict()
    return _ingested_ids(report)


def test_inspection_retention_never_returns_a_research_row(env):
    research_ids = _ingest_and_get_research_ids(env)
    before = {i: _snapshot(_reload(env, i)) for i in research_ids}

    row = retain_image(
        env["s"], data=env["raw"]["TRC-001-EXT-001"], tenant_id=TENANT, instrument_type="trocar",
        content_type="image/jpeg", source="inspection", uploaded_by=TECH, consent=True)

    assert row is not None
    assert row.id not in research_ids, "an inspection upload was handed a research-owned image"
    assert row.source == "inspection"
    assert {i: _snapshot(_reload(env, i)) for i in research_ids} == before


def test_baseline_reference_never_returns_a_research_row(env):
    research_ids = _ingest_and_get_research_ids(env)
    before = {i: _snapshot(_reload(env, i)) for i in research_ids}

    row = retain_reference_image(
        env["s"], data=env["raw"]["TRC-001-EXT-001"], tenant_id=TENANT, instrument_type="trocar",
        content_type="image/jpeg", uploaded_by=TECH, usage_rights_attested=True)

    assert row.id not in research_ids, "a baseline reference was bound to a research-owned image"
    assert row.source == "baseline_reference"
    assert {i: _snapshot(_reload(env, i)) for i in research_ids} == before


def test_owner_withdrawal_does_not_delete_another_purposes_copy(env):
    """After a baseline reference of the same bytes is stored, withdrawing the research
    attestation removes the research copy and leaves the baseline copy intact."""
    from app.routes.trc001_research import withdraw_owner_attestation

    research_ids = _ingest_and_get_research_ids(env)
    baseline = retain_reference_image(
        env["s"], data=env["raw"]["TRC-001-EXT-001"], tenant_id=TENANT, instrument_type="trocar",
        content_type="image/jpeg", uploaded_by=TECH, usage_rights_attested=True)
    baseline_id, baseline_before = baseline.id, _snapshot(baseline)

    withdraw_owner_attestation(auth=_owner_auth(), db=env["s"])

    for image_id in research_ids:
        if image_id != baseline_id:
            assert _reload(env, image_id) is None, "research bytes survived the owner's withdrawal"
    after = _reload(env, baseline_id)
    assert after is not None, "the baseline reference lost its image to a research withdrawal"
    assert _snapshot(after) == baseline_before


# ── the generic ML surface cannot reach, mint or modify research images ───────

def _upload(data: bytes, query: str, headers=None):
    return client.post(
        f"/api/ml/images?{query}", files={"images": ("x.jpg", io.BytesIO(data), "image/jpeg")},
        headers=headers or AUTH_OPERATOR)


def test_generic_ml_upload_of_identical_bytes_does_not_disclose_a_research_image(env):
    research_ids = _ingest_and_get_research_ids(env)

    resp = _upload(env["raw"]["TRC-001-EXT-001"], "instrument_type=trocar&consent=true")

    assert resp.status_code == 201, resp.text
    returned = {img["id"] for img in resp.json()["images"]}
    assert returned.isdisjoint(research_ids), "generic upload returned a research image id"


def test_generic_ml_upload_cannot_mint_a_research_source_row(env):
    resp = _upload(_jpeg((1, 2, 3)), f"consent=true&source={RESEARCH_SOURCE}&instrument_type=TRC-001")

    assert resp.status_code in (400, 403, 422), resp.text
    minted = env["s"].query(RetainedImage).filter(
        RetainedImage.tenant_id == TENANT, RetainedImage.source == RESEARCH_SOURCE).count()
    assert minted == 0, "a generic caller created a row carrying the research-intake marker"


def test_retention_service_refuses_an_unscoped_research_source_row(env):
    """Defense in depth below the route: the research source marker cannot be applied
    by a caller that supplies no research scope."""
    try:
        row = retain_image(
            env["s"], data=_jpeg((4, 5, 6)), tenant_id=TENANT, instrument_type="TRC-001",
            content_type="image/jpeg", source=RESEARCH_SOURCE, uploaded_by=TECH, consent=True)
    except (ValueError, PermissionError):
        env["s"].rollback()
        row = None
    assert row is None
    env["s"].expire_all()
    assert env["s"].query(RetainedImage).filter(
        RetainedImage.tenant_id == TENANT, RetainedImage.source == RESEARCH_SOURCE).count() == 0


def test_generic_ml_routes_cannot_list_or_read_research_images(env):
    research_ids = _ingest_and_get_research_ids(env)

    listing = client.get("/api/ml/images", headers=AUTH_OPERATOR)
    assert listing.status_code == 200, listing.text
    body = listing.json()
    listed = {row["id"] for row in (body["images"] if isinstance(body, dict) else body)}
    assert listed.isdisjoint(research_ids), "research images are enumerable through /ml/images"

    for image_id in research_ids:
        resp = client.get(f"/api/ml/images/{image_id}/bytes", headers=AUTH_OPERATOR)
        assert resp.status_code in (403, 404), "research bytes served through the generic ML route"


def test_generic_ml_labelling_cannot_modify_a_research_image(env):
    """Ground truth for research images stays unknown: the generic labelling routes
    must not label, read labels of, or adjudicate a research-intake image."""
    research_ids = _ingest_and_get_research_ids(env)
    image_id = research_ids[0]

    resp = client.post(
        f"/api/ml/images/{image_id}/labels", headers=AUTH_OPERATOR,
        json={"finding_type": "debris", "present": True, "severity": "minor"})
    assert resp.status_code in (403, 404), resp.text
    assert client.get(f"/api/ml/images/{image_id}/labels", headers=AUTH_OPERATOR).status_code in (403, 404)

    row = _reload(env, image_id)
    assert row.label_status == "unlabeled"
    assert env["s"].query(ImageLabel).filter(ImageLabel.image_id == image_id).count() == 0


# ── one research basis never claims another basis' image ──────────────────────

def _institutional_intake(env, dataset_id: str):
    return run_trc001_intake(
        env["s"], kit_dir=env["kit"], tenant_id=TENANT, dataset_id=dataset_id,
        auth=AuthContext(actor=DIRECTOR, role="quality_director", tenant_id=TENANT),
        authorization_basis="institutional")


@pytest.mark.parametrize("same_dataset", [False, True])
def test_institutional_intake_never_claims_an_owner_attested_image(env, same_dataset):
    owner_ids = _ingest_and_get_research_ids(env)
    before = {i: _snapshot(_reload(env, i)) for i in owner_ids}
    institutional_dataset = env["dataset_id"] if same_dataset else f"SEC171-01-INST-{uuid.uuid4().hex[:8]}"
    _grant_institutional(env, institutional_dataset)

    report = _institutional_intake(env, institutional_dataset)

    assert set(_ingested_ids(report)).isdisjoint(owner_ids), (
        "an institutional intake reported an owner-attested image as its own")
    assert {i: _snapshot(_reload(env, i)) for i in owner_ids} == before


@pytest.mark.parametrize("same_dataset", [False, True])
def test_owner_attested_intake_never_claims_an_institutional_image(env, same_dataset):
    institutional_dataset = env["dataset_id"] if same_dataset else f"SEC171-01-INST-{uuid.uuid4().hex[:8]}"
    _grant_institutional(env, institutional_dataset)
    inst_report = _institutional_intake(env, institutional_dataset)
    assert inst_report.status == "INGESTED", inst_report.to_dict()
    inst_ids = _ingested_ids(inst_report)
    before = {i: _snapshot(_reload(env, i)) for i in inst_ids}
    _attest(env)

    report = _owner_intake(env)

    assert set(_ingested_ids(report)).isdisjoint(inst_ids), (
        "an owner-attested intake reported an institutional image as its own")
    for image_id in inst_ids:
        after = _reload(env, image_id)
        assert after is not None
        # Ownership is never written onto another basis' image.
        assert (after.research_owner_subject or "") == before[image_id]["research_owner_subject"]
        assert after.research_attestation_id == before[image_id]["research_attestation_id"]
        assert _snapshot(after)["bytes_sha256"] == before[image_id]["bytes_sha256"]
        assert _associations_for(env, image_id) == 0


def test_institutional_images_survive_another_owners_withdrawal(env):
    from app.routes.trc001_research import withdraw_owner_attestation

    institutional_dataset = f"SEC171-01-INST-{uuid.uuid4().hex[:8]}"
    _grant_institutional(env, institutional_dataset)
    inst_ids = _ingested_ids(_institutional_intake(env, institutional_dataset))
    assert len(inst_ids) == 2
    owner_ids = _ingest_and_get_research_ids(env)

    withdraw_owner_attestation(auth=_owner_auth(), db=env["s"])

    for image_id in inst_ids:
        assert _reload(env, image_id) is not None, "an institutional image was deleted by an owner withdrawal"
    for image_id in set(owner_ids) - set(inst_ids):
        assert _reload(env, image_id) is None, "the owner's bytes survived the owner's withdrawal"


def test_second_owner_never_reassigns_the_first_owners_image(env):
    first_ids = _ingest_and_get_research_ids(env)
    before = {i: _snapshot(_reload(env, i)) for i in first_ids}
    other, other_subject = "sec171-other@x", "sub-sec171-other"
    s = env["s"]
    s.add(UserRoleAssignment(username=other, role="technician"))
    s.commit()
    try:
        _attest(env, owner=other, subject=other_subject)
        _owner_intake(env, auth=_owner_auth(actor=other, subject=other_subject))
        assert {i: _snapshot(_reload(env, i)) for i in first_ids} == before
    finally:
        s.rollback()
        s.query(UserRoleAssignment).filter(UserRoleAssignment.username == other).delete()
        s.commit()


def test_research_images_stay_unlabelled_and_training_ineligible(env):
    _attest(env)
    report = _owner_intake(env)
    assert report.status == "INGESTED", report.to_dict()
    for image in report.images:
        assert image.ground_truth_status == "unknown"
        assert image.baseline_review == "pending_review"
        assert image.research_training_eligible is False
        assert _reload(env, image.retained_image_id).label_status == "unlabeled"
