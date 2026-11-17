"""Stage 6D — laboratory-confirmation resolution + governed ingestion hand-off.

Lab confirmation must resolve a record-backed, independently-reviewed
VeritasEvidenceProvenanceRecord linked to the EXACT image hash (+ instrument); there
is no boolean short-circuit. Ingestion verifies bytes against the registered hash and
hands off to the existing image-retention service (no new store).
"""
from __future__ import annotations

import hashlib

import pytest

from app.db.session import SessionLocal
from app.models.veritas_evidence import VeritasEvidenceProvenanceRecord

from research.lens_vision import research_acquisition
from research.lens_vision import scientific_authorization as sa

TENANT = "stage6d-tenant"


@pytest.fixture()
def db():
    s = SessionLocal()
    ids = []
    try:
        yield s, ids
    finally:
        for i in ids:
            s.query(VeritasEvidenceProvenanceRecord).filter(VeritasEvidenceProvenanceRecord.id == i).delete()
        s.commit()
        s.close()


def _evidence(db, ids, *, file_hash, tenant=TENANT, instrument="INS-1", approval="approved",
              reviewer="lab@x", evidence_type="corrosion_eds"):
    row = VeritasEvidenceProvenanceRecord(
        tenant_id=tenant, evidence_type=evidence_type, instrument_id=instrument, file_hash=file_hash,
        approval_status=approval, reviewer=reviewer,
    )
    db.add(row)
    db.commit()
    ids.append(row.id)
    return row


# ── §2.4 laboratory confirmation resolution ──────────────────────────────────

def test_lab_confirmation_requires_approved_matching_evidence(db):
    s, ids = db
    h = "d" * 64
    # No evidence -> not confirmed.
    c0 = sa.resolve_lab_confirmation(s, tenant_id=TENANT, image_sha256=h, instrument_id="INS-1")
    assert c0.confirmed is False and c0.reason == "no_approved_evidence_for_image"
    # Pending evidence -> still not confirmed.
    _evidence(s, ids, file_hash=h, approval="pending")
    assert sa.resolve_lab_confirmation(s, tenant_id=TENANT, image_sha256=h, instrument_id="INS-1").confirmed is False
    # Approved + reviewed + matching hash/instrument -> confirmed with identity.
    _evidence(s, ids, file_hash=h, approval="approved", evidence_type="corrosion_eds")
    c = sa.resolve_lab_confirmation(s, tenant_id=TENANT, image_sha256=h, instrument_id="INS-1")
    assert c.confirmed is True and c.identity == "corrosion_eds" and c.evidence_record_id is not None


def test_lab_confirmation_rejects_unreviewed_and_cross_tenant_and_wrong_image(db):
    s, ids = db
    h = "e" * 64
    # Approved but NOT independently reviewed.
    _evidence(s, ids, file_hash=h, approval="approved", reviewer="")
    assert sa.resolve_lab_confirmation(s, tenant_id=TENANT, image_sha256=h).confirmed is False
    # Evidence for a different tenant cannot confirm this tenant's image.
    _evidence(s, ids, file_hash=h, tenant="other", approval="approved", reviewer="lab@x")
    assert sa.resolve_lab_confirmation(s, tenant_id="other", image_sha256="f" * 64).confirmed is False  # wrong hash
    # Correct tenant+hash but wrong instrument filter -> not confirmed.
    good = "a1" * 32
    _evidence(s, ids, file_hash=good, instrument="INS-9", approval="approved", reviewer="lab@x")
    assert sa.resolve_lab_confirmation(
        s, tenant_id=TENANT, image_sha256=good, instrument_id="INS-OTHER").confirmed is False


# ── §4 governed ingestion hand-off ───────────────────────────────────────────

def test_ingestion_verifies_hash_and_records_storage_id(db, monkeypatch):
    s, _ = db
    data = b"real-image-bytes"
    good_hash = hashlib.sha256(data).hexdigest()

    class _Retained:
        id = 4242
        sha256 = good_hash

    calls = {}

    def _fake_retain(db, *, data, tenant_id, **kw):  # noqa: A002
        calls["tenant"] = tenant_id
        return _Retained()

    monkeypatch.setattr("app.services.image_retention_service.retain_image", _fake_retain)

    # Hash matches -> handed off, storage id recorded.
    ok = research_acquisition._ingest_one(s, {"image_id": "x", "image_sha256": good_hash, "image_bytes": data,
                                              "instrument_id": "I1"}, tenant_id=TENANT)
    assert ok["imported"] is True and ok["retained_image_id"] == 4242 and calls["tenant"] == TENANT

    # Hash mismatch -> never handed off.
    bad = research_acquisition._ingest_one(s, {"image_id": "y", "image_sha256": "0" * 64, "image_bytes": data},
                                           tenant_id=TENANT)
    assert bad["imported"] is False and bad["reason"] == "hash_mismatch"

    # No bytes -> nothing imported.
    nob = research_acquisition._ingest_one(s, {"image_id": "z", "image_sha256": good_hash}, tenant_id=TENANT)
    assert nob["imported"] is False and nob["reason"] == "no_bytes_present"
