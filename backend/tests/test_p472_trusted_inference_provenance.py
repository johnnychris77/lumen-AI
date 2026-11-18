"""P4.7.2 — trusted inference provenance (positive and adversarial tests).

What makes a stored CV record verified model inference is a server-issued,
sealed provenance row (``app.cv.provenance``) — never a claim in the record.

Positive: a run the server pipeline seals DOES qualify for operational metrics.
Adversarial: nothing else does — not a forged payload, a forged or copied
provenance row, a seal made without the server key, a record moved to another
tenant, a record edited after sealing, or revoked / missing provenance.

Everything here is synthetic. The "model" is a provider object with canned
outputs, its "artifact digests" are constant strings, and the provenance key is
a test value. No model weights, evaluation results, inspection evidence or
authentication records are invented as if they were real; the tests exercise
the trust decision, not detection.

Runs on SQLite and PostgreSQL (whichever ``DATABASE_URL`` selects).
"""
from __future__ import annotations

import base64
import io
import json
import os
import shutil
import subprocess
import sys
import types
import uuid
from pathlib import Path

import pytest
import sqlalchemy as sa
from fastapi.testclient import TestClient
from PIL import Image

from app.cv import provenance
from app.cv.evidence import (
    EVIDENCE_AI_UNAVAILABLE,
    EVIDENCE_FAILED,
    EVIDENCE_LEGACY_UNVERIFIED,
    EVIDENCE_MODEL_INFERENCE,
    EVIDENCE_SIMULATED,
    classify_record,
    classify_records,
    integrity_verified,
    operational_sql_criteria,
)
from app.cv.pipeline import run_analysis
from app.cv.provenance import (
    ProvenanceError,
    issue_provenance,
    revoke_provenance,
    revoke_provenance_for_artifact,
    verify_record,
)
from app.cv.registry import CVRegistry
from app.db import models
from app.db.session import SessionLocal, engine
from app.main import app
from app.models.cv_inference import CVInferenceProvenance, CVInferenceRecord
from app.routers.auth_simple import _make_token
from app.schemas.cv import CVAnalysisRequest, CVInferenceResult, IdentifierReads, InstrumentIdentity

client = TestClient(app)

TEST_KEY = "test-only-provenance-key-not-a-secret-0123456789"
ATTACKER_KEY = "attacker-guessed-key-that-is-long-enough-000000"
CLASSIFIER_DIGEST = "a" * 64
DETECTOR_DIGEST = "b" * 64
UNAPPROVED_DIGEST = "d" * 64
BACKEND_DIR = Path(__file__).resolve().parents[1]
_IS_POSTGRES = engine.dialect.name == "postgresql"


# ── helpers ───────────────────────────────────────────────────────────────────

def _uid(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10]}"


def _b64_png() -> str:
    buf = io.BytesIO()
    Image.new("RGB", (64, 64), (200, 200, 200)).save(buf, "PNG")
    return base64.b64encode(buf.getvalue()).decode()


def _member(prefix: str = "p472") -> tuple[str, str, dict]:
    """A fresh tenant with one enabled member, and that member's signed JWT."""
    tenant = _uid(f"{prefix}-tenant")
    user = f"{_uid(prefix)}@example.com"
    db = SessionLocal()
    try:
        db.add(models.TenantMembership(tenant_id=tenant, user_email=user, role="viewer", is_enabled=True))
        db.commit()
    finally:
        db.close()
    return tenant, user, {"Authorization": f"Bearer {_make_token(user)}"}


class _Session:
    def __init__(self, outputs):
        self.outputs = outputs

    def run(self, *_a, **_k):
        return self.outputs


@pytest.fixture(autouse=True)
def _provenance_environment(monkeypatch):
    """The server holds a provenance key and approves the fixture provider's two
    artifact digests. Individual tests remove one of these to prove fail-closed."""
    monkeypatch.setenv(provenance.KEY_ENV, TEST_KEY)
    monkeypatch.delenv(provenance.KEY_ID_ENV, raising=False)
    monkeypatch.setenv("CV_ONNX_CLASSIFIER_SHA256", CLASSIFIER_DIGEST)
    monkeypatch.setenv("CV_ONNX_DETECTOR_SHA256", DETECTOR_DIGEST)
    monkeypatch.delenv("LUMENAI_MODEL_SHA256", raising=False)
    monkeypatch.delenv("CV_PROVIDER", raising=False)
    CVRegistry.reset()
    from app.limiter import limiter
    if limiter is not None:
        try:
            limiter.reset()
        except Exception:  # noqa: BLE001 - the limiter backend may not support reset
            pass
    yield
    CVRegistry.reset()


@pytest.fixture
def model_provider(monkeypatch, tmp_path):
    """A real ``OnnxCVProvider`` object with canned session outputs (no runtime, no
    weights). Its verified-artifact state is what a provider holds after checking
    its pins; installed as the registry's provider for the test."""
    import app.cv.onnx_provider as onnx_mod

    fake_numpy = types.ModuleType("numpy")
    fake_numpy.argmax = lambda seq: max(range(len(seq)), key=seq.__getitem__)
    monkeypatch.setitem(sys.modules, "numpy", fake_numpy)
    monkeypatch.setattr(onnx_mod, "_preprocess_image", lambda raw, size: ("tensor", size))

    provider = object.__new__(onnx_mod.OnnxCVProvider)
    provider.model_dir = tmp_path
    provider._integrity = {"verified": True, "artifacts": {
        "instrument_classifier": CLASSIFIER_DIGEST, "finding_detector": DETECTOR_DIGEST}}
    provider._classifier = _Session([[[0.9, 0.1]]])
    provider._detector = _Session([[[[0.1, 0.1, 0.5, 0.5, 0.91, 0]]]])
    provider._ort = None
    monkeypatch.setattr(CVRegistry, "get_provider", classmethod(lambda cls: provider))
    return provider


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


def _run(db, tenant: str) -> CVInferenceResult:
    return run_analysis(CVAnalysisRequest(image_data_b64=_b64_png(), tenant_id=tenant), db=db)


def _record(db, inference_id: str) -> CVInferenceRecord:
    db.expire_all()
    return db.query(CVInferenceRecord).filter(CVInferenceRecord.inference_id == inference_id).one()


def _provenance_row(db, inference_id: str) -> CVInferenceProvenance | None:
    db.expire_all()
    return db.query(CVInferenceProvenance).filter(
        CVInferenceProvenance.inference_id == inference_id).first()


def _operational_ids(db, tenant: str) -> list[str]:
    rows = db.query(CVInferenceRecord).filter(
        CVInferenceRecord.tenant_id == tenant, *operational_sql_criteria(CVInferenceRecord)).all()
    return [r.inference_id for r in integrity_verified(db, rows)]


def _sql_only_ids(db, tenant: str) -> list[str]:
    return [r.inference_id for r in db.query(CVInferenceRecord).filter(
        CVInferenceRecord.tenant_id == tenant, *operational_sql_criteria(CVInferenceRecord)).all()]


def _forged_record(db, tenant: str, **overrides) -> CVInferenceRecord:
    """A row written by something other than the pipeline, claiming in its own
    payload to be verified model inference."""
    inference_id = _uid("forged")
    payload = CVInferenceResult(
        inference_id=inference_id, status="success", tenant_id=tenant, provider="onnx",
        instrument_identity=InstrumentIdentity(recognized=True, instrument_name="X", confidence=0.9),
        identifier_reads=IdentifierReads(), evidence_class=EVIDENCE_MODEL_INFERENCE,
        model_integrity={"verified": True, "artifacts": {"finding_detector": DETECTOR_DIGEST}},
        contamination_score=10.0, damage_score=10.0, overall_cleanliness_score=10.0,
    ).model_dump_json()
    fields = dict(
        inference_id=inference_id, tenant_id=tenant, provider="onnx", status="success",
        instrument_recognized=True, instrument_confidence=0.9, blood_count=7, finding_count=7,
        overall_cleanliness_score=10.0, result_json=payload,
    )
    fields.update(overrides)
    record = CVInferenceRecord(**fields)
    db.add(record)
    db.commit()
    return record


def _kpi(headers: dict) -> dict:
    return client.get("/api/enterprise/cv/kpi-summary", headers=headers).json()


# ══ POSITIVE — legitimate, trusted model inference qualifies ══════════════════

class TestTrustedInferenceQualifies:
    def test_a_sealed_pipeline_run_is_verified_model_inference(self, db, model_provider):
        tenant = _uid("p472-tenant")

        result = _run(db, tenant)

        assert result.status == "success" and result.evidence_class == EVIDENCE_MODEL_INFERENCE
        assert result.simulated is False and len(result.regions) == 1
        record = _record(db, result.inference_id)
        assert classify_record(record) == EVIDENCE_MODEL_INFERENCE
        assert verify_record(db, record).trusted is True
        assert _operational_ids(db, tenant) == [result.inference_id]

    def test_provenance_binds_tenant_artifacts_digest_and_status(self, db, model_provider):
        tenant = _uid("p472-tenant")
        result = _run(db, tenant)

        row = _provenance_row(db, result.inference_id)
        record = _record(db, result.inference_id)

        assert row is not None
        assert row.record_id == record.id and row.inference_id == record.inference_id
        assert row.tenant_id == tenant                      # the authenticated tenant
        assert row.provider == "onnx" and row.execution_status == "success"
        assert json.loads(row.artifact_digests_json) == {
            "instrument_classifier": CLASSIFIER_DIGEST, "finding_detector": DETECTOR_DIGEST}
        assert row.record_digest == provenance.record_digest(record)
        assert row.state == provenance.STATE_TRUSTED and row.revoked_at == ""
        assert len(row.attestation) == 64 and row.key_id == "default"

    def test_a_sealed_run_reaches_operational_metrics_through_the_api(self, model_provider):
        tenant, _user, headers = _member()

        response = client.post(
            "/api/enterprise/cv/analyze", json={"image_data_b64": _b64_png()}, headers=headers)

        assert response.status_code == 200, response.text
        body = response.json()
        assert body["evidence_class"] == EVIDENCE_MODEL_INFERENCE and body["tenant_id"] == tenant
        kpi = _kpi(headers)
        assert kpi["genuine_analyses"] == 1 and kpi["total_analyses"] == 1
        assert kpi["evidence_basis"] == "model_inference_only"
        history = client.get("/api/enterprise/cv/history", headers=headers).json()
        assert history[0]["evidence_class"] == EVIDENCE_MODEL_INFERENCE
        assert history[0]["operational_evidence"] is True
        assert history[0]["finding_count"] == 1
        assert history[0]["overall_cleanliness_score"] is not None
        stored = client.get(
            f"/api/enterprise/cv/inference/{body['inference_id']}", headers=headers).json()
        assert stored["evidence_class"] == EVIDENCE_MODEL_INFERENCE
        assert stored["model_integrity"]["verified"] is True
        assert stored["model_integrity"]["artifacts"]["finding_detector"] == DETECTOR_DIGEST
        assert len(stored["regions"]) == 1

    def test_the_async_path_seals_its_run_too(self, db, model_provider):
        from app.routes import cv as cv_routes

        tenant = _uid("p472-tenant")
        job_id = _uid("job")
        cv_routes._run_async_task(
            job_id, CVAnalysisRequest(image_data_b64=_b64_png(), tenant_id=tenant), tenant)

        payload = cv_routes._async_results.pop(job_id)
        assert payload["status"] == "complete"
        assert payload["result"]["evidence_class"] == EVIDENCE_MODEL_INFERENCE
        assert _operational_ids(db, tenant) == [payload["result"]["inference_id"]]

    def test_human_annotation_does_not_break_the_seal(self, model_provider):
        """Review fields change legitimately after a run and are not sealed."""
        _tenant, _user, headers = _member()
        inference_id = client.post(
            "/api/enterprise/cv/analyze", json={"image_data_b64": _b64_png()}, headers=headers,
        ).json()["inference_id"]

        annotated = client.post(
            f"/api/enterprise/cv/inference/{inference_id}/annotate", headers=headers,
            json={"annotator_id": "reviewer-1", "notes": "synthetic"})

        assert annotated.status_code == 200, annotated.text
        assert _kpi(headers)["genuine_analyses"] == 1

    def test_a_sealed_run_feeds_a_downstream_service(self, db, model_provider):
        from app.services.accreditation_engine import compute_accreditation_readiness

        tenant = _uid("p472-tenant")
        _run(db, tenant)
        assert compute_accreditation_readiness(tenant, db=db).data_source == "real"


# ══ FAIL-CLOSED — a run that cannot be sealed is withheld ═════════════════════

class TestUnsealableRunsAreWithheld:
    def _assert_withheld(self, db, tenant: str, result: CVInferenceResult) -> None:
        assert result.status == "failed" and result.evidence_class == EVIDENCE_FAILED
        assert result.regions == [] and result.ranking_inputs == {}
        assert result.contamination_score is None and result.overall_cleanliness_score is None
        assert result.model_integrity["verified"] is False
        assert _provenance_row(db, result.inference_id) is None
        assert _operational_ids(db, tenant) == []

    @pytest.mark.parametrize("key", [None, "", "too-short"])
    def test_no_usable_provenance_key(self, db, model_provider, monkeypatch, key):
        if key is None:
            monkeypatch.delenv(provenance.KEY_ENV, raising=False)
        else:
            monkeypatch.setenv(provenance.KEY_ENV, key)
        tenant = _uid("p472-tenant")

        result = _run(db, tenant)

        self._assert_withheld(db, tenant, result)
        stored = _record(db, result.inference_id)
        assert stored.status == "failed" and stored.finding_count == 0

    def test_artifact_is_not_an_approved_pin(self, db, model_provider, monkeypatch):
        monkeypatch.setenv("CV_ONNX_DETECTOR_SHA256", UNAPPROVED_DIGEST)   # the pin changed
        tenant = _uid("p472-tenant")
        self._assert_withheld(db, tenant, _run(db, tenant))

    def test_no_approved_pins_at_all(self, db, model_provider, monkeypatch):
        monkeypatch.delenv("CV_ONNX_CLASSIFIER_SHA256", raising=False)
        monkeypatch.delenv("CV_ONNX_DETECTOR_SHA256", raising=False)
        tenant = _uid("p472-tenant")
        self._assert_withheld(db, tenant, _run(db, tenant))

    def test_provider_reports_no_verified_artifact(self, db, model_provider):
        model_provider._integrity = {"verified": False, "artifacts": {}}
        tenant = _uid("p472-tenant")
        self._assert_withheld(db, tenant, _run(db, tenant))

    def test_a_provider_that_only_claims_integrity_in_its_result(self, db, monkeypatch):
        """A provider whose RESULT says "verified model inference" but which holds no
        verified artifact is not believed."""
        from app.cv.base import BaseCVProvider

        class ClaimingProvider(BaseCVProvider):
            provider_name = "custom"
            model_versions = {"custom": "1"}

            def analyze(self, req):
                return CVInferenceResult(
                    inference_id=_uid("claim"), status="success", tenant_id=req.tenant_id,
                    provider="custom",
                    instrument_identity=InstrumentIdentity(recognized=True, instrument_name="X", confidence=0.9),
                    identifier_reads=IdentifierReads(), evidence_class=EVIDENCE_MODEL_INFERENCE,
                    model_integrity={"verified": True, "artifacts": {"m": DETECTOR_DIGEST}},
                    contamination_score=1.0, damage_score=1.0, overall_cleanliness_score=1.0,
                )

            def identify_instrument(self, image_url, instrument_hint=""):
                return InstrumentIdentity()

            def read_identifiers(self, image_url):
                return IdentifierReads()

            def compare_baseline(self, *args, **kwargs):
                return None

        claiming = ClaimingProvider()
        assert claiming.verified_artifacts() == {}      # it holds no verified artifact
        monkeypatch.setattr(CVRegistry, "get_provider", classmethod(lambda cls: claiming))
        tenant = _uid("p472-tenant")

        self._assert_withheld(db, tenant, _run(db, tenant))

    def test_no_database_session(self, model_provider):
        result = run_analysis(CVAnalysisRequest(image_data_b64=_b64_png(), tenant_id=_uid("t")), db=None)
        assert result.status == "failed" and result.evidence_class == EVIDENCE_FAILED
        assert result.regions == [] and result.overall_cleanliness_score is None


# ══ ADVERSARIAL — nothing but a valid server seal promotes a record ═══════════

class TestForgedEvidenceIsNeverPromoted:
    def test_forged_payload_without_provenance(self, db):
        tenant, _user, headers = _member()
        record = _forged_record(db, tenant)

        assert classify_record(record) == EVIDENCE_LEGACY_UNVERIFIED
        assert _sql_only_ids(db, tenant) == [] and _operational_ids(db, tenant) == []
        kpi = _kpi(headers)
        assert kpi["genuine_analyses"] == 0 and kpi["blood_detections"] == 0
        assert kpi["legacy_unverified_excluded_count"] == 1

    def test_raw_sql_provenance_row_with_an_invented_seal(self, db):
        """An arbitrary writer inserts a matching provenance row. It has every column
        right except the one thing it cannot produce: a seal under the server key."""
        tenant, _user, headers = _member()
        record = _forged_record(db, tenant)
        db.execute(sa.text(
            "INSERT INTO cv_inference_provenance (record_id, inference_id, tenant_id, provider, "
            "execution_status, model_versions_json, artifact_digests_json, record_digest, state, "
            "key_id, attestation, issued_at, revoked_at, revoked_by, revoked_reason) VALUES "
            "(:rid, :iid, :tenant, 'onnx', 'success', '{}', :artifacts, :digest, 'trusted', "
            "'default', :seal, '2026-11-18T00:00:00+00:00', '', '', '')"
        ), {"rid": record.id, "iid": record.inference_id, "tenant": tenant,
            "artifacts": json.dumps({"finding_detector": DETECTOR_DIGEST}),
            "digest": provenance.record_digest(record), "seal": "f" * 64})
        db.commit()

        # The relational filter is satisfied — which is exactly why it is not enough.
        assert _sql_only_ids(db, tenant) == [record.inference_id]
        # The integrity check is not.
        assert verify_record(db, record).reason == "provenance_seal_invalid"
        assert classify_record(record) == EVIDENCE_LEGACY_UNVERIFIED
        assert _operational_ids(db, tenant) == []
        assert _kpi(headers)["genuine_analyses"] == 0

    def test_seal_made_with_a_key_the_server_does_not_hold(self, db, monkeypatch):
        tenant = _uid("p472-tenant")
        record = _forged_record(db, tenant)
        monkeypatch.setenv(provenance.KEY_ENV, ATTACKER_KEY)       # the attacker's own key
        issue_provenance(db, record, authenticated_tenant_id=tenant,
                         artifacts={"finding_detector": DETECTOR_DIGEST})
        db.commit()
        monkeypatch.setenv(provenance.KEY_ENV, TEST_KEY)           # the server's key

        assert verify_record(db, _record(db, record.inference_id)).reason == "provenance_seal_invalid"
        assert _operational_ids(db, tenant) == []

    def test_provenance_copied_from_a_genuine_run_onto_a_forged_record(self, db, model_provider):
        tenant = _uid("p472-tenant")
        genuine = _run(db, tenant)
        source = _provenance_row(db, genuine.inference_id)
        forged = _forged_record(db, tenant)
        db.add(CVInferenceProvenance(
            record_id=forged.id, inference_id=forged.inference_id, tenant_id=tenant,
            provider=source.provider, execution_status=source.execution_status,
            model_versions_json=source.model_versions_json,
            artifact_digests_json=source.artifact_digests_json,
            record_digest=source.record_digest, state=source.state, key_id=source.key_id,
            attestation=source.attestation, issued_at=source.issued_at,
        ))
        db.commit()

        assert verify_record(db, _record(db, forged.inference_id)).trusted is False
        assert _operational_ids(db, tenant) == [genuine.inference_id]

    def test_a_record_cannot_have_two_provenance_rows(self, db, model_provider):
        tenant = _uid("p472-tenant")
        genuine = _run(db, tenant)
        source = _provenance_row(db, genuine.inference_id)
        db.add(CVInferenceProvenance(
            record_id=source.record_id, inference_id=_uid("other"), tenant_id=tenant,
            provider="onnx", execution_status="success", record_digest="0" * 64,
            key_id="default", attestation="0" * 64, issued_at="x"))
        with pytest.raises(sa.exc.IntegrityError):
            db.commit()
        db.rollback()

    @pytest.mark.parametrize("statement,reason", [
        ("UPDATE cv_inference_records SET blood_count = 1000, finding_count = 1000 WHERE id = :id",
         "record_altered_after_sealing"),
        ("UPDATE cv_inference_records SET overall_cleanliness_score = 99.0 WHERE id = :id",
         "record_altered_after_sealing"),
        ("UPDATE cv_inference_records SET result_json = '{\"evidence_class\":\"model_inference\"}' "
         "WHERE id = :id", "record_altered_after_sealing"),
        ("UPDATE cv_inference_records SET result_json = '{not json' WHERE id = :id",
         "record_altered_after_sealing"),
        ("UPDATE cv_inference_provenance SET artifact_digests_json = '{}' WHERE record_id = :id",
         "provenance_malformed"),
        ("UPDATE cv_inference_provenance SET artifact_digests_json = 'not json' WHERE record_id = :id",
         "provenance_malformed"),
        ("UPDATE cv_inference_provenance SET execution_status = 'partial' WHERE record_id = :id",
         "provenance_run_mismatch"),
        ("UPDATE cv_inference_provenance SET attestation = '' WHERE record_id = :id",
         "provenance_seal_invalid"),
    ])
    def test_tampering_after_sealing_is_detected(self, db, model_provider, statement, reason):
        tenant, _user, headers = _member()
        genuine = _run(db, tenant)
        record_id = _record(db, genuine.inference_id).id

        db.execute(sa.text(statement), {"id": record_id})
        db.commit()

        record = _record(db, genuine.inference_id)
        assert verify_record(db, record).reason == reason
        assert classify_record(record) == EVIDENCE_LEGACY_UNVERIFIED
        assert _operational_ids(db, tenant) == []
        assert _kpi(headers)["genuine_analyses"] == 0

    def test_get_inference_does_not_crash_or_echo_a_malformed_payload(self, db, model_provider):
        tenant, _user, headers = _member()
        genuine = _run(db, tenant)
        db.execute(sa.text("UPDATE cv_inference_records SET result_json = '{not json' WHERE inference_id = :i"),
                   {"i": genuine.inference_id})
        db.commit()

        response = client.get(f"/api/enterprise/cv/inference/{genuine.inference_id}", headers=headers)

        assert response.status_code == 404

    def test_simulated_unavailable_and_failed_stay_what_they_are(self, db):
        """The server will not seal a non-run, and a provenance row written around
        the server cannot turn one into a run."""
        tenant = _uid("p472-tenant")
        rows = {
            EVIDENCE_SIMULATED: _forged_record(db, tenant, provider="mock"),
            EVIDENCE_AI_UNAVAILABLE: _forged_record(db, tenant, provider="unavailable", status="ai_unavailable"),
            EVIDENCE_FAILED: _forged_record(db, tenant, status="failed"),
        }
        for expected, record in rows.items():
            with pytest.raises(ProvenanceError):
                issue_provenance(db, record, authenticated_tenant_id=tenant,
                                 artifacts={"finding_detector": DETECTOR_DIGEST})
            db.rollback()
            db.add(CVInferenceProvenance(
                record_id=record.id, inference_id=record.inference_id, tenant_id=tenant,
                provider=record.provider, execution_status=record.status,
                artifact_digests_json=json.dumps({"finding_detector": DETECTOR_DIGEST}),
                record_digest=provenance.record_digest(record), state="trusted",
                key_id="default", attestation="e" * 64, issued_at="2026-11-18T00:00:00+00:00"))
            db.commit()
            assert classify_record(_record(db, record.inference_id)) == expected
        assert _sql_only_ids(db, tenant) == [] and _operational_ids(db, tenant) == []

    def test_sealing_survives_database_value_normalisation(self, db):
        """Integers written to float columns come back as floats; the seal must be
        over what the database stored, or a genuine run would fail its own check."""
        tenant = _uid("p472-tenant")
        record = CVInferenceRecord(
            inference_id=_uid("norm"), tenant_id=tenant, provider="onnx", status="success",
            instrument_confidence=1, contamination_score=50, overall_cleanliness_score=50,
            finding_count=2, blood_count=2, result_json="{}")
        db.add(record)
        db.flush()
        issue_provenance(db, record, authenticated_tenant_id=tenant,
                         artifacts={"finding_detector": DETECTOR_DIGEST})
        db.commit()

        assert verify_record(db, _record(db, record.inference_id)).trusted is True


# ══ TENANT BINDING ════════════════════════════════════════════════════════════

class TestTenantBinding:
    def test_provenance_cannot_be_issued_for_another_tenant(self, db):
        record = _forged_record(db, _uid("p472-tenant-a"))
        for claimed in (_uid("p472-tenant-b"), "", None):
            with pytest.raises(ProvenanceError):
                issue_provenance(db, record, authenticated_tenant_id=claimed,
                                 artifacts={"finding_detector": DETECTOR_DIGEST})
            db.rollback()
        assert _provenance_row(db, record.inference_id) is None

    def test_a_sealed_record_moved_to_another_tenant_loses_its_trust(self, db, model_provider):
        tenant_a, _ua, headers_a = _member("p472-a")
        tenant_b, _ub, headers_b = _member("p472-b")
        genuine = _run(db, tenant_a)
        assert _kpi(headers_a)["genuine_analyses"] == 1

        db.execute(sa.text("UPDATE cv_inference_records SET tenant_id = :b WHERE inference_id = :i"),
                   {"b": tenant_b, "i": genuine.inference_id})
        db.commit()

        record = _record(db, genuine.inference_id)
        assert verify_record(db, record).reason == "provenance_tenant_mismatch"
        assert _sql_only_ids(db, tenant_b) == [] and _operational_ids(db, tenant_b) == []
        assert _kpi(headers_b)["genuine_analyses"] == 0
        assert _kpi(headers_a)["genuine_analyses"] == 0

    def test_moving_the_record_and_its_provenance_together_still_fails(self, db, model_provider):
        tenant_a, tenant_b = _uid("p472-a"), _uid("p472-b")
        genuine = _run(db, tenant_a)
        for table in ("cv_inference_records", "cv_inference_provenance"):
            db.execute(sa.text(f"UPDATE {table} SET tenant_id = :b WHERE inference_id = :i"),
                       {"b": tenant_b, "i": genuine.inference_id})
        db.commit()

        assert _sql_only_ids(db, tenant_b) == [genuine.inference_id]     # relationally consistent ...
        assert verify_record(db, _record(db, genuine.inference_id)).trusted is False   # ... but unsealed
        assert _operational_ids(db, tenant_b) == []

    def test_one_tenants_sealed_run_never_counts_for_another(self, model_provider):
        _tenant_a, _ua, headers_a = _member("p472-a")
        _tenant_b, _ub, headers_b = _member("p472-b")
        client.post("/api/enterprise/cv/analyze", json={"image_data_b64": _b64_png()}, headers=headers_a)

        assert _kpi(headers_a)["genuine_analyses"] == 1
        assert _kpi(headers_b)["genuine_analyses"] == 0
        assert client.get("/api/enterprise/cv/history", headers=headers_b).json() == []

    def test_a_client_supplied_tenant_is_not_the_sealed_tenant(self, db, model_provider):
        """The sealed tenant is the authenticated one. Naming another tenant in the
        request is refused outright; it never reaches the pipeline."""
        tenant, _user, headers = _member()
        other = _uid("p472-other")

        refused = client.post(
            "/api/enterprise/cv/analyze", headers={**headers, "X-Tenant-Id": other},
            json={"image_data_b64": _b64_png(), "tenant_id": other})
        assert refused.status_code == 403
        assert db.query(CVInferenceProvenance).filter(
            CVInferenceProvenance.tenant_id == other).count() == 0

        accepted = client.post(
            "/api/enterprise/cv/analyze", headers=headers, json={"image_data_b64": _b64_png()})
        assert _provenance_row(db, accepted.json()["inference_id"]).tenant_id == tenant


# ══ REVOKED OR MISSING PROVENANCE ═════════════════════════════════════════════

class TestRevokedOrMissingProvenance:
    def test_revoked_provenance_no_longer_qualifies(self, db, model_provider):
        tenant, _user, headers = _member()
        genuine = _run(db, tenant)

        assert revoke_provenance(db, inference_id=genuine.inference_id, tenant_id=tenant,
                                 revoked_by="governance@example.com", reason="synthetic test") is True
        db.commit()

        record = _record(db, genuine.inference_id)
        assert verify_record(db, record).reason == "provenance_revoked"
        assert classify_record(record) == EVIDENCE_LEGACY_UNVERIFIED
        assert _sql_only_ids(db, tenant) == [] and _operational_ids(db, tenant) == []
        kpi = _kpi(headers)
        assert kpi["genuine_analyses"] == 0 and kpi["legacy_unverified_excluded_count"] == 1
        stored = client.get(f"/api/enterprise/cv/inference/{genuine.inference_id}", headers=headers).json()
        assert stored["overall_cleanliness_score"] is None and stored["regions"] == []
        assert stored["model_integrity"] == {"verified": False, "reason": "provenance_revoked"}

    def test_a_revocation_cannot_be_undone_by_editing_columns(self, db, model_provider):
        tenant = _uid("p472-tenant")
        genuine = _run(db, tenant)
        revoke_provenance(db, inference_id=genuine.inference_id, tenant_id=tenant,
                          revoked_by="governance@example.com", reason="synthetic test")
        db.commit()

        db.execute(sa.text(
            "UPDATE cv_inference_provenance SET state = 'trusted', revoked_at = '', revoked_by = '', "
            "revoked_reason = '' WHERE inference_id = :i"), {"i": genuine.inference_id})
        db.commit()

        assert verify_record(db, _record(db, genuine.inference_id)).reason == "provenance_seal_invalid"
        assert _operational_ids(db, tenant) == []

    def test_revocation_is_scoped_to_the_named_tenant(self, db, model_provider):
        tenant = _uid("p472-tenant")
        genuine = _run(db, tenant)
        assert revoke_provenance(db, inference_id=genuine.inference_id, tenant_id=_uid("someone-else"),
                                 revoked_by="x", reason="x") is False
        db.rollback()
        assert _operational_ids(db, tenant) == [genuine.inference_id]

    def test_revoking_an_artifact_revokes_every_run_sealed_with_it(self, db, model_provider):
        tenant = _uid("p472-tenant")
        first, second = _run(db, tenant), _run(db, tenant)
        assert set(_operational_ids(db, tenant)) == {first.inference_id, second.inference_id}

        revoked = revoke_provenance_for_artifact(
            db, sha256=DETECTOR_DIGEST, revoked_by="governance@example.com", reason="model withdrawn")
        db.commit()

        assert revoked >= 2
        assert _operational_ids(db, tenant) == []

    def test_deleted_provenance_means_unverified(self, db, model_provider):
        tenant, _user, headers = _member()
        genuine = _run(db, tenant)
        db.execute(sa.text("DELETE FROM cv_inference_provenance WHERE inference_id = :i"),
                   {"i": genuine.inference_id})
        db.commit()

        record = _record(db, genuine.inference_id)
        assert verify_record(db, record).reason == "no_provenance"
        assert classify_record(record) == EVIDENCE_LEGACY_UNVERIFIED
        assert _kpi(headers)["genuine_analyses"] == 0

    @pytest.mark.parametrize("key", [None, ATTACKER_KEY])
    def test_sealed_runs_are_unverified_without_the_issuing_key(self, db, model_provider, monkeypatch, key):
        tenant = _uid("p472-tenant")
        genuine = _run(db, tenant)
        if key is None:
            monkeypatch.delenv(provenance.KEY_ENV, raising=False)
        else:
            monkeypatch.setenv(provenance.KEY_ENV, key)

        record = _record(db, genuine.inference_id)
        assert verify_record(db, record).trusted is False
        assert classify_record(record) == EVIDENCE_LEGACY_UNVERIFIED
        assert _operational_ids(db, tenant) == []

    def test_a_detached_record_cannot_be_verified(self, db, model_provider):
        genuine = _run(db, _uid("p472-tenant"))
        record = _record(db, genuine.inference_id)
        db.expunge(record)
        assert classify_record(record) == EVIDENCE_LEGACY_UNVERIFIED
        assert classify_records(None, [record]) == {record.id: EVIDENCE_LEGACY_UNVERIFIED}


# ══ UNAUTHORIZED PROVENANCE CREATION ══════════════════════════════════════════

class TestProvenanceCannotBeCreatedFromOutside:
    def test_no_api_route_creates_or_edits_provenance(self):
        offenders = [
            route.path for route in app.routes
            if "provenance" in getattr(route, "path", "").lower()
            and "/cv" in getattr(route, "path", "")
        ]
        assert offenders == []

    def test_only_the_pipeline_issues_provenance(self):
        app_dir = Path(provenance.__file__).resolve().parents[1]
        callers = sorted(
            path.relative_to(app_dir).as_posix()
            for path in app_dir.rglob("*.py")
            if "issue_provenance(" in path.read_text(encoding="utf-8")
        )
        assert callers == ["cv/pipeline.py", "cv/provenance.py"]

    def test_client_claims_in_a_request_are_ignored(self, db, monkeypatch):
        """With no approved model on the server, a request that asserts every trust
        field it can think of still gets an explicit unavailable result."""
        monkeypatch.setenv("APP_ENV", "production")
        _tenant, _user, headers = _member()

        response = client.post("/api/enterprise/cv/analyze", headers=headers, json={
            "image_data_b64": _b64_png(), "evidence_class": EVIDENCE_MODEL_INFERENCE,
            "simulated": False, "status": "success", "provenance_trusted": True,
            "model_integrity": {"verified": True, "artifacts": {"finding_detector": DETECTOR_DIGEST}},
            "attestation": "f" * 64, "provenance": {"state": "trusted"},
        })

        assert response.status_code == 200, response.text
        body = response.json()
        assert body["status"] == "ai_unavailable" and body["evidence_class"] == EVIDENCE_AI_UNAVAILABLE
        assert body["regions"] == [] and body["overall_cleanliness_score"] is None
        assert _provenance_row(db, body["inference_id"]) is None
        assert _kpi(headers)["genuine_analyses"] == 0

    def test_annotation_cannot_promote_a_forged_record(self, db):
        tenant, _user, headers = _member()
        record = _forged_record(db, tenant)
        client.post(
            f"/api/enterprise/cv/inference/{record.inference_id}/annotate", headers=headers,
            json={"annotator_id": "a", "notes": "confirmed real", "confirmed_regions": [{"id": 1}]})
        assert classify_record(_record(db, record.inference_id)) == EVIDENCE_LEGACY_UNVERIFIED
        assert _kpi(headers)["genuine_analyses"] == 0

    def test_downstream_services_reject_a_forged_provenance_row(self, db):
        from app.services.accreditation_engine import compute_accreditation_readiness

        tenant = _uid("p472-tenant")
        record = _forged_record(db, tenant, blood_count=1000)
        db.add(CVInferenceProvenance(
            record_id=record.id, inference_id=record.inference_id, tenant_id=tenant,
            provider="onnx", execution_status="success",
            artifact_digests_json=json.dumps({"finding_detector": DETECTOR_DIGEST}),
            record_digest=provenance.record_digest(record), state="trusted", key_id="default",
            attestation="e" * 64, issued_at="2026-11-18T00:00:00+00:00"))
        db.commit()

        assert _sql_only_ids(db, tenant) == [record.inference_id]
        assert compute_accreditation_readiness(tenant, db=db).data_source != "real"
        assert _operational_ids(db, tenant) == []


# ══ LEGACY DEFAULT AND MIGRATION ══════════════════════════════════════════════

class TestLegacyDefaultAndMigration:
    def test_records_without_provenance_default_to_legacy_unverified(self, db):
        tenant = _uid("p472-tenant")
        completed = [_forged_record(db, tenant, status=s) for s in ("success", "partial")]
        classes = classify_records(db, completed)
        assert set(classes.values()) == {EVIDENCE_LEGACY_UNVERIFIED}

    def test_the_provenance_table_exists_in_the_application_schema(self):
        assert sa.inspect(engine).has_table("cv_inference_provenance")

    @pytest.mark.skipif(not _IS_POSTGRES, reason="the Alembic chain is PostgreSQL-only")
    def test_alembic_migration_creates_no_provenance_and_guards_its_downgrade(self):
        """Real ``alembic`` in a throwaway schema: the upgrade adds the table and
        backfills nothing; a downgrade refuses to drop provenance that exists."""
        schema = f"p472_{uuid.uuid4().hex[:12]}"
        with engine.begin() as conn:
            conn.execute(sa.text(f'CREATE SCHEMA "{schema}"'))
        base = engine.url.render_as_string(hide_password=False)
        url = f"{base}{'&' if '?' in base else '?'}options=-csearch_path={schema}"
        scratch = sa.create_engine(url)

        def alembic(*args, **env):
            return subprocess.run(  # noqa: S603 - fixed argv, no shell
                [shutil.which("alembic"), *args], cwd=BACKEND_DIR, capture_output=True, text=True,
                timeout=300, check=False, env={**os.environ, "DATABASE_URL": url, **env})

        try:
            assert alembic("upgrade", "b5d9e3a71c42").returncode == 0
            with scratch.begin() as conn:
                conn.execute(sa.text(
                    "INSERT INTO cv_inference_records (inference_id, tenant_id, context, provider, status, "
                    "facility_id, image_url, baseline_image_url, instrument_recognized, instrument_name, "
                    "instrument_category, instrument_confidence, match_method, barcode_value, qr_value, "
                    "key_dot_value, barcode_instrument_id, contamination_score, damage_score, "
                    "overall_cleanliness_score, baseline_compared, baseline_match_pct, baseline_verdict, "
                    "finding_count, blood_count, bone_count, tissue_count, corrosion_count, crack_count, "
                    "insulation_count, residue_count, result_json, archived_image_key, provider_cost_usd, "
                    "review_required, review_annotation, review_annotator_id, processing_ms, created_at) "
                    "VALUES ('historic-1', 't', 'inspection', 'onnx', 'success', '', '', '', true, '', '', "
                    "0.9, '', '', '', '', '', 50, 50, 50, false, 0, '', 3, 3, 0, 0, 0, 0, 0, 0, '{}', '', 0, "
                    "false, '', '', 0, now())"))
            assert not sa.inspect(scratch).has_table("cv_inference_provenance")

            upgraded = alembic("upgrade", "head")
            assert upgraded.returncode == 0, upgraded.stderr[-1500:]
            assert sa.inspect(scratch).has_table("cv_inference_provenance")
            with scratch.connect() as conn:
                # No backfill: the historic record has no provenance, so it is unverified.
                assert conn.execute(sa.text("SELECT count(*) FROM cv_inference_provenance")).scalar_one() == 0
                assert conn.execute(sa.text("SELECT count(*) FROM cv_inference_records")).scalar_one() == 1

            # An empty provenance table may be dropped; re-apply for the guarded case.
            assert alembic("downgrade", "b5d9e3a71c42").returncode == 0
            assert alembic("upgrade", "head").returncode == 0
            with scratch.begin() as conn:
                record_id = conn.execute(sa.text("SELECT id FROM cv_inference_records")).scalar_one()
                conn.execute(sa.text(
                    "INSERT INTO cv_inference_provenance (record_id, inference_id, tenant_id, provider, "
                    "execution_status, record_digest, key_id, attestation, issued_at) VALUES "
                    "(:rid, 'historic-1', 't', 'onnx', 'success', :d, 'default', :d, 'x')"),
                    {"rid": record_id, "d": "0" * 64})
            refused = alembic("downgrade", "b5d9e3a71c42")
            assert refused.returncode != 0
            assert sa.inspect(scratch).has_table("cv_inference_provenance")
            allowed = alembic("downgrade", "b5d9e3a71c42", LUMENAI_ALLOW_PROVENANCE_DOWNGRADE="1")
            assert allowed.returncode == 0
        finally:
            scratch.dispose()
            with engine.begin() as conn:
                conn.execute(sa.text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
