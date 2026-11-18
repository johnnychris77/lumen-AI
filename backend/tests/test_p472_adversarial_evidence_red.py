"""P4.7.2 RED-phase adversarial regression tests.

Intentionally assert security requirements not yet implemented. Do not weaken
these assertions to obtain a green CI result. Synthetic SQLite fixtures only.
No external traffic, model, hospital images, or production credentials.
"""
from __future__ import annotations

import json

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models.cv_inference import CVInferenceProvenance, CVInferenceRecord
from app.cv.evidence import (
    EVIDENCE_LEGACY_UNVERIFIED,
    classify_record,
    operational_sql_criteria,
)


def _forged_payload(**overrides):
    payload = {
        "evidence_class": "model_inference",
        "model_integrity": {"verified": True, "sha256": "attacker-controlled"},
        "simulated": False,
    }
    payload.update(overrides)
    return json.dumps(payload, separators=(",", ":"))


@pytest.fixture
def evidence_db():
    engine = create_engine("sqlite:///:memory:")
    # P4.7.2 remediation: the schema now includes the server-owned provenance table that
    # operational qualification joins against. It is created EMPTY here — no test in this
    # file issues provenance — so every assertion below is unchanged.
    Base.metadata.create_all(
        engine, tables=[CVInferenceRecord.__table__, CVInferenceProvenance.__table__])
    with Session(engine) as session:
        yield session
    engine.dispose()


def _insert(session, *, inference_id, tenant_id, provider="onnx",
            status="success", result_json=None):
    record = CVInferenceRecord(
        inference_id=inference_id,
        tenant_id=tenant_id,
        provider=provider,
        status=status,
        result_json=result_json if result_json is not None else _forged_payload(),
        blood_count=7,
        finding_count=7,
    )
    session.add(record)
    session.commit()
    return record


def _operational_ids(session, tenant):
    return {
        row.inference_id for row in session.query(CVInferenceRecord).filter(
            CVInferenceRecord.tenant_id == tenant,
            *operational_sql_criteria(CVInferenceRecord),
        ).all()
    }


def test_forged_json_cannot_promote_untrusted_writer_record(evidence_db):
    """A record inserted without an authenticated model-run attestation is unverified.

    Current implementation uses only mutable result_json text, so this is
    expected to FAIL until server-owned provenance is enforced.
    """
    row = _insert(evidence_db, inference_id="forged-1", tenant_id="tenant-a")
    assert classify_record(row) == EVIDENCE_LEGACY_UNVERIFIED
    assert row.inference_id not in _operational_ids(evidence_db, "tenant-a")


def test_forged_marker_with_false_integrity_is_not_operational(evidence_db):
    """SQL filtering must agree with classify_record, not substring-match JSON."""
    row = _insert(
        evidence_db, inference_id="forged-2", tenant_id="tenant-a",
        result_json=_forged_payload(model_integrity={"verified": False}),
    )
    assert classify_record(row) == EVIDENCE_LEGACY_UNVERIFIED
    assert row.inference_id not in _operational_ids(evidence_db, "tenant-a")


def test_forged_marker_with_simulated_true_is_not_operational(evidence_db):
    row = _insert(
        evidence_db, inference_id="forged-3", tenant_id="tenant-a",
        result_json=_forged_payload(simulated=True),
    )
    assert row.inference_id not in _operational_ids(evidence_db, "tenant-a")


def test_malformed_json_never_qualifies(evidence_db):
    row = _insert(
        evidence_db, inference_id="bad-json", tenant_id="tenant-a",
        result_json='{"evidence_class":"model_inference",',
    )
    assert classify_record(row) == EVIDENCE_LEGACY_UNVERIFIED
    assert row.inference_id not in _operational_ids(evidence_db, "tenant-a")


def test_cross_tenant_forgery_cannot_pollute_other_tenant_aggregate(evidence_db):
    """A tenant B writer must not make an unverified record count in tenant A."""
    _insert(evidence_db, inference_id="b-1", tenant_id="tenant-b")
    _insert(evidence_db, inference_id="a-forged", tenant_id="tenant-a")
    assert _operational_ids(evidence_db, "tenant-a") == set()
    assert _operational_ids(evidence_db, "tenant-b") == set()


def test_sql_filter_rejects_conflicting_provider_and_status(evidence_db):
    _insert(evidence_db, inference_id="mock", tenant_id="tenant-a", provider="mock")
    _insert(evidence_db, inference_id="failed", tenant_id="tenant-a", status="failed")
    _insert(evidence_db, inference_id="unavailable", tenant_id="tenant-a",
            status="ai_unavailable")
    assert _operational_ids(evidence_db, "tenant-a") == set()
