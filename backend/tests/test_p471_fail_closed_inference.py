"""P4.7.1 — Secure fail-closed inference foundation: regression tests.

Findings covered
----------------
SCI-03     fabricated findings from the legacy SHA-256 fallback and the mock
           CV provider are impossible outside an explicit dev/test simulation.
SCI-16     an inference failure is "failed", never an empty/clean result.
SCI-17     simulated / not-evaluated / legacy-unverified records never enter
           defect KPIs, ranking or the annotation queue.
SEC-R2-01  CV routes take the tenant from the verified auth context only.
SEC-R2-02  prohibited image URLs are rejected before any network access.
SEC-R2-03  /api/stream/frame no longer trusts a caller-supplied tenant header.
Step 7     a model loads only after SHA-256 pin verification.

Nothing in this file touches the network: every HTTP/DNS entry point the image
fetcher could use is replaced with a recorder that fails the test if reached.
"""
from __future__ import annotations

import hashlib
import io
import os
import socket
import sys
import types
import uuid

import httpx
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.ai import inference as legacy
from app.ai.inference import LumenAIModel
from app.ai.inference_gate import NOT_EVALUATED, simulation_permitted
from app.ai.local_inference_policy import LocalInferenceUnavailable
from app.cv import safe_fetch
from app.cv.evidence import (
    EVIDENCE_AI_UNAVAILABLE,
    EVIDENCE_FAILED,
    EVIDENCE_LEGACY_UNVERIFIED,
    EVIDENCE_MODEL_INFERENCE,
    EVIDENCE_SIMULATED,
    classify,
)
from app.cv.registry import CVRegistry
from app.cv.safe_fetch import (
    ImageFetchError,
    ImageFetchNotPermittedError,
    UnsafeImageURLError,
    assert_image_url_allowed,
    fetch_image_bytes,
    try_fetch_image_bytes,
)
from app.db import models
from app.db.session import SessionLocal
from app.main import app
from app.models.cv_inference import CVInferenceRecord
from app.routers.auth_simple import _make_token
from app.schemas.cv import CVAnalysisRequest, CVInferenceResult, IdentifierReads, InstrumentIdentity

client = TestClient(app)

DEV_ADMIN = {"Authorization": "Bearer dev-token"}
PUBLIC_URL = "https://fixtures.lumenai.dev/inspection/p471.jpg"

# P4.7.2: a synthetic provenance key and a synthetic "approved" artifact digest, used
# only to exercise the sealing path in tests. Neither is a real secret or a real model.
TEST_PROVENANCE_KEY = "test-only-provenance-key-not-a-secret-0123456789"
SEALED_ARTIFACT = "c" * 64

# Environments in which a simulated finding must be impossible. A stray
# AI_ALLOW_DEMO_SCORING=true is set in each to prove the flag alone is inert.
NON_SIMULATION_ENVS = ["production", "prod", "staging", "research", "qa", None]


# ── helpers ───────────────────────────────────────────────────────────────────

def _uid(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10]}"


def _png(color=(200, 200, 200), size=(64, 64)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, "PNG")
    return buf.getvalue()


def _jwt(username: str) -> dict:
    """A real signed per-user JWT (the kind /auth/login issues)."""
    return {"Authorization": f"Bearer {_make_token(username)}"}


def _add_membership(tenant_id: str, user_email: str, role: str = "viewer") -> None:
    db = SessionLocal()
    try:
        db.add(models.TenantMembership(tenant_id=tenant_id, user_email=user_email, role=role, is_enabled=True))
        db.commit()
    finally:
        db.close()


def _member(prefix: str = "p471") -> tuple[str, str, dict]:
    """A fresh tenant with one enabled member. Returns (tenant, user, headers)."""
    tenant = _uid(f"{prefix}-tenant")
    user = f"{_uid(prefix)}@example.com"
    _add_membership(tenant, user)
    return tenant, user, _jwt(user)


def _set_env(monkeypatch, app_env: str | None, *, stray_demo_flag: bool = True) -> None:
    if app_env is None:
        monkeypatch.delenv("APP_ENV", raising=False)
    else:
        monkeypatch.setenv("APP_ENV", app_env)
    if stray_demo_flag:
        monkeypatch.setenv("AI_ALLOW_DEMO_SCORING", "true")


@pytest.fixture
def no_network(monkeypatch):
    """Replace every route the image fetcher could take to the network with a
    recorder. A test asserts ``calls == []`` to prove nothing was attempted."""
    calls: list[tuple[str, str]] = []

    def _record(kind):
        def _inner(*args, **kwargs):
            calls.append((kind, str(args[0]) if args else ""))
            raise AssertionError(f"network access attempted via {kind}")
        return _inner

    monkeypatch.setattr(safe_fetch, "_open_client", _record("safe_fetch._open_client"))
    monkeypatch.setattr(safe_fetch.socket, "getaddrinfo", _record("socket.getaddrinfo"))
    monkeypatch.setattr(httpx, "get", _record("httpx.get"))
    monkeypatch.setattr(httpx, "post", _record("httpx.post"))
    return calls


@pytest.fixture(autouse=True)
def _reset_shared_state(monkeypatch):
    """Isolate module-level caches and env pins between tests."""
    for var in ("LUMENAI_MODEL_PATH", "LUMENAI_MODEL_SHA256", "CV_PROVIDER",
                "CV_IMAGE_FETCH_ALLOWED_HOSTS", "CV_ONNX_MODEL_DIR",
                "CV_ONNX_CLASSIFIER_SHA256", "CV_ONNX_DETECTOR_SHA256"):
        monkeypatch.delenv(var, raising=False)
    # P4.7.2: the server-side provenance key (verification needs it on every read).
    monkeypatch.setenv("LUMENAI_PROVENANCE_HMAC_KEY", TEST_PROVENANCE_KEY)
    monkeypatch.delenv("LUMENAI_PROVENANCE_HMAC_KEY_ID", raising=False)
    LumenAIModel._shared_model = None
    LumenAIModel._shared_model_key = None
    CVRegistry.reset()
    # /analyze is rate limited (30/minute). The limiter stays ENABLED; its
    # in-memory counters are cleared so this module's many negative requests
    # are not answered with 429 instead of the behaviour under test.
    from app.limiter import limiter
    if limiter is not None:
        try:
            limiter.reset()
        except Exception:
            pass
    yield
    LumenAIModel._shared_model = None
    LumenAIModel._shared_model_key = None
    CVRegistry.reset()


def _assert_nothing_fabricated_legacy(res: dict) -> None:
    assert res["analysis_status"] in ("ai_unavailable", "failed")
    assert res["detected_issue"] == NOT_EVALUATED
    assert res["stain_detected"] is None
    assert res["confidence"] is None
    assert res["risk_score"] is None
    assert res["simulated"] is False
    assert res["human_review_required"] is True
    assert res["inference_mode"] in ("ai_unavailable", "inference_failed")
    assert res["model_name"] == "none"


def _assert_nothing_fabricated_cv(data: dict) -> None:
    assert data["status"] in ("ai_unavailable", "failed")
    assert data["regions"] == []
    assert data["contamination_score"] is None
    assert data["damage_score"] is None
    assert data["overall_cleanliness_score"] is None
    assert data["ranking_inputs"] == {}
    assert data["simulated"] is False
    assert data["evidence_class"] in (EVIDENCE_AI_UNAVAILABLE, EVIDENCE_FAILED)
    assert data["instrument_identity"]["recognized"] is False
    assert data["instrument_identity"]["confidence"] == 0.0
    assert data["baseline_comparison"] is None
    assert data["human_review_required"] is True
    assert data["unavailable_reason"]


# ══ Step 2 / SCI-03 — legacy path ════════════════════════════════════════════

class TestLegacyInferenceFailsClosed:
    @pytest.mark.parametrize("app_env", NON_SIMULATION_ENVS)
    def test_no_fabricated_finding_outside_dev_test(self, monkeypatch, app_env):
        """Production, staging, research, an unrecognised env and an UNSET
        APP_ENV all yield ai_unavailable — even with a stray demo flag."""
        _set_env(monkeypatch, app_env)
        assert simulation_permitted() is False
        res = LumenAIModel().predict(_png())
        _assert_nothing_fabricated_legacy(res)
        assert res["analysis_status"] == "ai_unavailable"

    def test_dev_test_env_without_explicit_optin_is_still_unavailable(self, monkeypatch):
        monkeypatch.setenv("APP_ENV", "test")
        monkeypatch.delenv("AI_ALLOW_DEMO_SCORING", raising=False)
        res = LumenAIModel().predict(_png())
        _assert_nothing_fabricated_legacy(res)

    def test_simulation_is_explicit_and_visibly_labelled(self, enable_demo_scoring):
        res = LumenAIModel().predict(_png())
        assert res["simulated"] is True
        assert res["analysis_status"] == "simulated"
        assert res["inference_mode"] == "deterministic-fallback"
        # No real-looking model identity on a simulated result.
        assert res["model_name"] == "simulated-placeholder"
        assert res["model_version"] == "simulation"
        assert res["model_integrity"]["verified"] is False

    def test_missing_weights_reports_a_reason(self, monkeypatch):
        _set_env(monkeypatch, "production")
        res = LumenAIModel().predict(_png())
        assert res["unavailable_reason"]
        assert res["model_integrity"]["verified"] is False


# ══ Step 7 — model artifact integrity before load ════════════════════════════

class _FakeYOLO:
    """Stands in for ultralytics.YOLO. Records construction; never real."""
    constructed: list[str] = []
    raise_on_construct = False
    raise_on_call = False

    def __init__(self, path):
        if type(self).raise_on_construct:
            raise RuntimeError("corrupt artifact at /secret/path")
        type(self).constructed.append(path)

    def __call__(self, image, verbose=False):
        if type(self).raise_on_call:
            raise RuntimeError("inference blew up")
        return []


@pytest.fixture
def fake_yolo(monkeypatch, tmp_path):
    _FakeYOLO.constructed = []
    _FakeYOLO.raise_on_construct = False
    _FakeYOLO.raise_on_call = False
    monkeypatch.setattr(legacy, "YOLO", _FakeYOLO)
    weights = tmp_path / "lumenai_model.pt"
    weights.write_bytes(b"test-only bytes, not a model")
    monkeypatch.setenv("LUMENAI_MODEL_PATH", str(weights))
    return weights


class TestModelIntegrityBeforeLoad:
    def test_weights_present_but_no_pin_is_not_loaded(self, fake_yolo):
        m = LumenAIModel()
        assert m.model is None
        assert _FakeYOLO.constructed == []          # runtime never opened the file
        assert "SHA-256 pin required" in m.load_reason
        _assert_nothing_fabricated_legacy(m.predict(_png()))

    def test_hash_mismatch_is_not_loaded(self, fake_yolo, monkeypatch):
        monkeypatch.setenv("LUMENAI_MODEL_SHA256", "0" * 64)
        m = LumenAIModel()
        assert m.model is None
        assert _FakeYOLO.constructed == []
        assert "integrity mismatch" in m.load_reason

    def test_malformed_pin_is_not_loaded(self, fake_yolo, monkeypatch):
        monkeypatch.setenv("LUMENAI_MODEL_SHA256", "z" * 64)
        m = LumenAIModel()
        assert m.model is None and _FakeYOLO.constructed == []

    def test_missing_weights_with_pin_is_not_loaded(self, monkeypatch, tmp_path):
        monkeypatch.setattr(legacy, "YOLO", _FakeYOLO)
        _FakeYOLO.constructed = []
        monkeypatch.setenv("LUMENAI_MODEL_PATH", str(tmp_path / "absent.pt"))
        monkeypatch.setenv("LUMENAI_MODEL_SHA256", "a" * 64)
        m = LumenAIModel()
        assert m.model is None and _FakeYOLO.constructed == []

    def test_matching_pin_loads_and_records_integrity(self, fake_yolo, monkeypatch):
        digest = hashlib.sha256(fake_yolo.read_bytes()).hexdigest()
        monkeypatch.setenv("LUMENAI_MODEL_SHA256", digest)
        m = LumenAIModel()
        assert m.model is not None
        assert _FakeYOLO.constructed == [str(fake_yolo)]
        assert m.model_integrity == {"verified": True, "sha256": digest}

    def test_verified_artifact_that_fails_to_load_is_failed_not_simulated(
        self, fake_yolo, monkeypatch, enable_demo_scoring,
    ):
        """Even with the simulation gate OPEN, a model that was configured and
        failed must report 'failed' — never fall back to a simulated finding."""
        monkeypatch.setenv("LUMENAI_MODEL_SHA256", hashlib.sha256(fake_yolo.read_bytes()).hexdigest())
        _FakeYOLO.raise_on_construct = True
        m = LumenAIModel()
        res = m.predict(_png())
        _assert_nothing_fabricated_legacy(res)
        assert res["analysis_status"] == "failed"
        assert res["inference_mode"] == "inference_failed"
        assert "/secret/path" not in res["unavailable_reason"]   # no path leakage

    def test_model_execution_failure_is_failed_not_clean(
        self, fake_yolo, monkeypatch, enable_demo_scoring,
    ):
        monkeypatch.setenv("LUMENAI_MODEL_SHA256", hashlib.sha256(fake_yolo.read_bytes()).hexdigest())
        m = LumenAIModel()
        assert m.model is not None
        # opencv/numpy are absent here, so execution fails; and if they were
        # present the fake model raises. Either way: failed, not clean.
        _FakeYOLO.raise_on_call = True
        res = m.predict(_png())
        _assert_nothing_fabricated_legacy(res)
        assert res["analysis_status"] == "failed"
        assert res["detected_issue"] != "clean"


# ══ Step 2 / SEC-R2-03 — /api/stream/frame ═══════════════════════════════════
#
# NOTE (pre-existing, unrelated to P4.7.1): on ``main`` this route raises before
# it reaches inference — ``app.metering`` / ``app.event_dispatcher`` reference
# models that ``app.db.models`` does not export (e.g. ``TenantQuota``), so every
# request ends in HTTP 500. P4.7.1 does not repair or retire that route (that is
# a product decision). It makes the code BEHIND it fail-closed and
# tenant-verified, so the route cannot fabricate a finding or cross a tenant
# boundary if it is ever repaired. The tests below therefore cover:
#   * the job (``run_inspection``) directly,
#   * the tenant resolver directly, and at HTTP level where it runs first,
#   * the full route with the unrelated metering collaborators stubbed.

def _new_inspection(tenant_id: str = "default-tenant") -> int:
    db = SessionLocal()
    try:
        row = models.Inspection(file_name="frame.png", tenant_id=tenant_id, tenant_name=tenant_id, status="queued")
        db.add(row)
        db.commit()
        db.refresh(row)
        return row.id
    finally:
        db.close()


def _inspection(inspection_id: int):
    db = SessionLocal()
    try:
        return db.query(models.Inspection).filter(models.Inspection.id == inspection_id).first()
    finally:
        db.close()


def _post_frame(headers: dict, *, http=None, **extra_headers):
    return (http or client).post(
        "/api/stream/frame",
        files={"frame": ("frame.png", _png(), "image/png")},
        data={"vendor_name": "p471-vendor"},
        headers={**headers, **extra_headers},
    )


@pytest.fixture
def metering_stubbed(monkeypatch):
    """Stub the route's unrelated, currently-broken metering/event collaborators
    so the P4.7.1 behaviour behind them can be exercised end to end."""
    import app.routes.inspect as inspect_route

    monkeypatch.setattr(inspect_route, "check_quota", lambda *a, **k: {"allowed": True, "used": 0, "limit": 0})
    monkeypatch.setattr(inspect_route, "record_usage_event", lambda *a, **k: None)
    monkeypatch.setattr(inspect_route, "dispatch_event", lambda *a, **k: None)


class TestLegacyInspectionJobFailsClosed:
    @pytest.mark.parametrize("app_env", NON_SIMULATION_ENVS)
    def test_job_stores_no_finding_outside_dev_test(self, monkeypatch, app_env):
        from app.jobs.inspection_job import run_inspection

        _set_env(monkeypatch, app_env)
        reports: list[int] = []
        monkeypatch.setattr("app.jobs.inspection_job.generate_report", lambda row: reports.append(row.id))

        inspection_id = _new_inspection()
        run_inspection(inspection_id, _png())

        row = _inspection(inspection_id)
        assert row.status == "ai_unavailable"            # not "completed"
        assert row.detected_issue == NOT_EVALUATED
        assert row.inference_mode == "ai_unavailable"
        assert row.risk_score == 0 and row.confidence == 0.0
        assert row.stain_detected is False
        assert row.model_name == "none" and row.model_version == "none"
        assert row.ai_analysis_status == "AI_UNAVAILABLE"
        assert reports == []                             # no report for an un-evaluated image

    def test_simulated_row_is_never_a_completed_inspection(self, monkeypatch, enable_demo_scoring):
        from app.jobs.inspection_job import run_inspection

        reports: list[int] = []
        monkeypatch.setattr("app.jobs.inspection_job.generate_report", lambda row: reports.append(row.id))
        inspection_id = _new_inspection()
        run_inspection(inspection_id, _png())

        row = _inspection(inspection_id)
        assert row.status == "simulated"
        assert row.inference_mode == "deterministic-fallback"
        assert row.model_name == "simulated-placeholder"
        assert row.ai_analysis_status == "AI_UNAVAILABLE"
        assert reports == []

    def test_failed_model_marks_the_row_failed_not_clean(self, fake_yolo, monkeypatch, enable_demo_scoring):
        from app.jobs.inspection_job import run_inspection

        monkeypatch.setenv("LUMENAI_MODEL_SHA256", hashlib.sha256(fake_yolo.read_bytes()).hexdigest())
        _FakeYOLO.raise_on_call = True
        monkeypatch.setattr("app.jobs.inspection_job.generate_report", lambda row: None)
        inspection_id = _new_inspection()
        run_inspection(inspection_id, _png())

        row = _inspection(inspection_id)
        assert row.status == "failed"
        assert row.inference_mode == "inference_failed"
        assert row.detected_issue == NOT_EVALUATED


class TestStreamFrameRoute:
    def test_route_never_returns_a_fabricated_finding(self, monkeypatch):
        """Holds whether or not the unrelated metering defect is ever repaired."""
        _set_env(monkeypatch, "production")
        tolerant = TestClient(app, raise_server_exceptions=False)
        res = _post_frame(DEV_ADMIN, http=tolerant)
        if res.status_code == 200:
            body = res.json()
            assert body["status"] in ("ai_unavailable", "failed")
            assert body["ai_evaluated"] is False

    @pytest.mark.parametrize("app_env", ["production", "research", None])
    def test_production_configured_route_reports_unavailable(self, monkeypatch, metering_stubbed, app_env):
        _set_env(monkeypatch, app_env)
        res = _post_frame(DEV_ADMIN)
        assert res.status_code == 200, res.text
        body = res.json()
        assert body["status"] == "ai_unavailable"
        assert body["ai_evaluated"] is False
        assert body["inference_mode"] == "ai_unavailable"
        assert body["human_review_required"] is True

        row = _inspection(body["inspection"]["id"])
        assert row.status == "ai_unavailable" and row.detected_issue == NOT_EVALUATED


class TestStreamFrameTenantCannotBeSpoofed:
    @pytest.fixture
    def manager_role(self, monkeypatch):
        """Give test JWT users a role permitted on the route. Role still comes
        from the server-side resolver, never from a header."""
        import app.routers.auth_simple as auth_simple
        monkeypatch.setattr(auth_simple, "_user_role", lambda username: "spd_manager")

    def test_spoofed_tenant_header_is_rejected(self, manager_role):
        """The verified tenant is resolved BEFORE the upload is read, quota is
        checked or inference runs — so this is a clean 403."""
        _tenant, _user, headers = _member("p471-frame")
        victim = _uid("p471-victim-tenant")
        res = _post_frame(headers, **{"X-Tenant-Id": victim})
        assert res.status_code == 403
        db = SessionLocal()
        try:
            assert db.query(models.Inspection).filter(models.Inspection.tenant_id == victim).count() == 0
        finally:
            db.close()

    def test_user_without_any_membership_is_rejected(self, manager_role):
        res = _post_frame(_jwt(f"{_uid('p471-nobody')}@example.com"))
        assert res.status_code == 403

    def test_write_lands_in_the_verified_tenant(self, manager_role, metering_stubbed):
        tenant, _user, headers = _member("p471-frame")
        res = _post_frame(headers)
        assert res.status_code == 200, res.text
        assert res.json()["inspection"]["tenant_id"] == tenant

    def test_own_tenant_header_is_accepted(self, manager_role, metering_stubbed):
        tenant, _user, headers = _member("p471-frame")
        res = _post_frame(headers, **{"X-Tenant-Id": tenant})
        assert res.status_code == 200, res.text
        assert res.json()["inspection"]["tenant_id"] == tenant

    def test_tenant_name_header_is_not_trusted(self, manager_role, metering_stubbed):
        _tenant, _user, headers = _member("p471-frame")
        res = _post_frame(headers, **{"X-Tenant-Name": "Some Other Hospital"})
        assert res.status_code == 200, res.text
        assert res.json()["inspection"]["tenant_name"] != "Some Other Hospital"

    def test_resolver_rules(self, manager_role):
        """Direct coverage of the resolver, independent of the route."""
        from fastapi import HTTPException

        from app.deps import get_current_user
        from app.routes.inspect import _verified_write_tenant

        tenant, user, _headers = _member("p471-frame")
        db = SessionLocal()
        try:
            principal = get_current_user(authorization=f"Bearer {_make_token(user)}", db=db)
            outsider = get_current_user(
                authorization=f"Bearer {_make_token(_uid('p471-out') + '@example.com')}", db=db,
            )
        finally:
            db.close()

        assert _verified_write_tenant(principal, None)["tenant_id"] == tenant
        assert _verified_write_tenant(principal, tenant)["tenant_id"] == tenant
        assert _verified_write_tenant(principal, "   ")["tenant_id"] == tenant
        for requested in ("some-other-tenant", "default-tenant"):
            with pytest.raises(HTTPException) as exc:
                _verified_write_tenant(principal, requested)
            assert exc.value.status_code == 403
        with pytest.raises(HTTPException) as exc:
            _verified_write_tenant(outsider, None)
        assert exc.value.status_code == 403


# ══ Step 2 / SCI-03 — CV provider ════════════════════════════════════════════

class TestCVProviderFailsClosed:
    @pytest.mark.parametrize("app_env", NON_SIMULATION_ENVS)
    def test_default_provider_is_unavailable_outside_dev_test(self, monkeypatch, app_env):
        _set_env(monkeypatch, app_env)
        assert CVRegistry.get_provider().provider_name == "unavailable"

    @pytest.mark.parametrize("app_env", NON_SIMULATION_ENVS)
    def test_explicit_mock_is_refused_outside_dev_test(self, monkeypatch, app_env):
        _set_env(monkeypatch, app_env)
        monkeypatch.setenv("CV_PROVIDER", "mock")
        provider = CVRegistry.get_provider()
        assert provider.provider_name == "unavailable"
        assert "disabled outside" in provider.reason

    def test_unknown_provider_never_falls_back_to_mock(self, enable_demo_scoring, monkeypatch):
        """Previously an unknown CV_PROVIDER silently selected the mock."""
        monkeypatch.setenv("CV_PROVIDER", "openai")
        assert CVRegistry.get_provider().provider_name == "unavailable"

    def test_gate_is_not_cached_across_calls(self, monkeypatch):
        monkeypatch.setenv("APP_ENV", "test")
        monkeypatch.setenv("AI_ALLOW_DEMO_SCORING", "true")
        assert CVRegistry.get_provider().provider_name == "mock"
        monkeypatch.setenv("APP_ENV", "production")
        assert CVRegistry.get_provider().provider_name == "unavailable"

    @pytest.mark.parametrize("app_env", ["production", "research", None])
    def test_analyze_returns_explicit_unavailable(self, monkeypatch, no_network, app_env):
        _set_env(monkeypatch, app_env)
        res = client.post("/api/enterprise/cv/analyze", json={"image_url": PUBLIC_URL}, headers=DEV_ADMIN)
        assert res.status_code == 200, res.text
        data = res.json()
        _assert_nothing_fabricated_cv(data)
        assert data["status"] == "ai_unavailable"
        assert data["provider"] == "unavailable"
        assert no_network == []

    def test_analyze_and_rank_does_not_rank_an_unevaluated_image(self, monkeypatch, no_network):
        _set_env(monkeypatch, "production")
        res = client.post("/api/enterprise/cv/analyze-and-rank", json={"image_url": PUBLIC_URL}, headers=DEV_ADMIN)
        assert res.status_code == 200, res.text
        body = res.json()
        _assert_nothing_fabricated_cv(body["cv"])
        assert body["ranking"]["ranking_mode"] == "not_ranked"
        assert "priority_score" not in body["ranking"]

    def test_video_analysis_is_unavailable_not_a_synthesized_timeline(self, monkeypatch, no_network):
        _set_env(monkeypatch, "production")
        res = client.post(
            "/api/enterprise/cv/analyze-video",
            json={"video_url": "https://fixtures.lumenai.dev/video/p471.mp4"}, headers=DEV_ADMIN,
        )
        assert res.status_code == 200, res.text
        data = res.json()
        assert data["status"] == "ai_unavailable"
        assert data["frames_analyzed"] == 0
        assert data["finding_timeline"] == [] and data["composite_regions"] == []
        assert data["worst_contamination_score"] is None and data["worst_damage_score"] is None
        assert data["total_duration_sec"] == 0.0

    def test_provider_info_reports_unavailable(self, monkeypatch):
        _set_env(monkeypatch, "production")
        data = client.get("/api/enterprise/cv/provider/info", headers=DEV_ADMIN).json()
        assert data["provider"] == "unavailable"
        assert data["available"] is False and data["simulated"] is False
        assert data["capabilities"] == []

    def test_simulated_output_is_explicitly_labelled(self, enable_demo_scoring, no_network):
        res = client.post("/api/enterprise/cv/analyze", json={"image_url": PUBLIC_URL}, headers=DEV_ADMIN)
        data = res.json()
        assert data["provider"] == "mock"
        assert data["simulated"] is True
        assert data["evidence_class"] == EVIDENCE_SIMULATED
        assert data["model_integrity"]["verified"] is False
        assert any("SIMULATED" in w for w in data["warnings"])
        assert all(r["simulated"] is True for r in data["regions"])
        assert all("SIMULATED" in r["evidence_description"] for r in data["regions"])
        assert no_network == []          # the mock never fetches the image


# ══ Step 3 / SEC-R2-01 — tenant authorization on CV routes ═══════════════════

class TestCVTenantAuthorization:
    def _analyze(self, headers: dict, **body):
        payload = {"image_url": PUBLIC_URL, **body}
        return client.post("/api/enterprise/cv/analyze", json=payload, headers=headers)

    def test_unauthenticated_request_is_rejected_before_any_work(self, no_network):
        res = client.post("/api/enterprise/cv/analyze", json={"image_url": "http://169.254.169.254/x.png"})
        assert res.status_code == 401
        assert no_network == []

    def test_body_tenant_id_is_ignored(self, no_network):
        tenant_a, _ua, headers_a = _member()
        tenant_b, _ub, headers_b = _member()
        res = self._analyze(headers_a, tenant_id=tenant_b)
        assert res.status_code == 200, res.text
        assert res.json()["tenant_id"] == tenant_a          # not the body value
        inference_id = res.json()["inference_id"]

        history_b = client.get("/api/enterprise/cv/history", headers=headers_b).json()
        assert all(h["inference_id"] != inference_id for h in history_b)
        history_a = client.get("/api/enterprise/cv/history", headers=headers_a).json()
        assert any(h["inference_id"] == inference_id for h in history_a)

    def test_cross_tenant_inference_retrieval_is_404(self, no_network):
        _ta, _ua, headers_a = _member()
        _tb, _ub, headers_b = _member()
        inference_id = self._analyze(headers_a).json()["inference_id"]

        assert client.get(f"/api/enterprise/cv/inference/{inference_id}", headers=headers_a).status_code == 200
        other = client.get(f"/api/enterprise/cv/inference/{inference_id}", headers=headers_b)
        assert other.status_code == 404
        assert inference_id not in other.text or "not found" in other.text.lower()

    def test_cross_tenant_annotation_is_404_and_changes_nothing(self, no_network):
        _ta, _ua, headers_a = _member()
        _tb, _ub, headers_b = _member()
        inference_id = self._analyze(headers_a).json()["inference_id"]

        res = client.post(
            f"/api/enterprise/cv/inference/{inference_id}/annotate",
            json={"annotator_id": "intruder", "notes": "tampered"}, headers=headers_b,
        )
        assert res.status_code == 404
        db = SessionLocal()
        try:
            rec = db.query(CVInferenceRecord).filter(CVInferenceRecord.inference_id == inference_id).first()
            assert rec.review_annotation == "" and rec.review_completed_at is None
        finally:
            db.close()

    @pytest.mark.parametrize("path", ["history", "review-queue", "provider/metrics", "kpi-summary"])
    def test_query_string_tenant_id_is_ignored(self, no_network, path):
        tenant_a, _ua, headers_a = _member()
        _tb, _ub, headers_b = _member()
        inference_id = self._analyze(headers_a).json()["inference_id"]

        res = client.get(f"/api/enterprise/cv/{path}?tenant_id={tenant_a}", headers=headers_b)
        assert res.status_code == 200, res.text
        assert inference_id not in res.text
        if path == "provider/metrics":
            assert res.json()["total_inferences"] == 0
        if path == "kpi-summary":
            body = res.json()
            assert body["total_analyses"] == 0 and body["unavailable_or_failed_count"] == 0

    def test_spoofed_tenant_header_is_rejected(self, no_network):
        _ta, _ua, headers_a = _member()
        tenant_b, _ub, _hb = _member()
        res = self._analyze({**headers_a, "X-Tenant-Id": tenant_b})
        assert res.status_code == 403
        assert client.get(
            "/api/enterprise/cv/history", headers={**headers_a, "X-Tenant-Id": tenant_b},
        ).status_code == 403

    def test_user_without_membership_is_rejected(self, no_network):
        headers = _jwt(f"{_uid('p471-nobody')}@example.com")
        assert self._analyze(headers).status_code == 403
        assert client.get("/api/enterprise/cv/kpi-summary", headers=headers).status_code == 403

    def test_async_job_is_invisible_to_another_tenant(self, no_network):
        _ta, _ua, headers_a = _member()
        _tb, _ub, headers_b = _member()
        sub = client.post("/api/enterprise/cv/analyze-async", json={"image_url": PUBLIC_URL}, headers=headers_a)
        assert sub.status_code == 202, sub.text
        inference_id = sub.json()["inference_id"]

        mine = client.get(f"/api/enterprise/cv/inference/{inference_id}/status", headers=headers_a).json()
        assert mine["status"] in ("processing", "complete")
        assert "tenant_id" not in mine
        theirs = client.get(f"/api/enterprise/cv/inference/{inference_id}/status", headers=headers_b).json()
        assert theirs == {"inference_id": inference_id, "status": "not_found"}

    def test_baseline_compare_and_video_use_the_verified_tenant(self, no_network, enable_demo_scoring):
        tenant_a, _ua, headers_a = _member()
        tenant_b, _ub, _hb = _member()
        res = client.post(
            "/api/enterprise/cv/baseline-compare",
            json={"inspection_image_url": PUBLIC_URL, "baseline_image_url": PUBLIC_URL, "tenant_id": tenant_b},
            headers=headers_a,
        )
        assert res.status_code == 200, res.text
        assert res.json()["tenant_id"] == tenant_a


# ══ Step 4 / SEC-R2-02 — SSRF ════════════════════════════════════════════════

PROHIBITED_URLS = [
    "http://fixtures.lumenai.dev/a.png",            # plain http
    "ftp://fixtures.lumenai.dev/a.png",
    "file:///etc/passwd",
    "gopher://fixtures.lumenai.dev/",
    "data:image/png;base64,AAAA",
    "//fixtures.lumenai.dev/a.png",                 # scheme-relative
    "https://localhost/a.png",
    "https://LOCALHOST./a.png",
    "https://127.0.0.1/a.png",
    "https://127.1/a.png",                          # short-form loopback
    "https://2130706433/a.png",                     # decimal loopback
    "https://0x7f000001/a.png",                     # hex loopback
    "https://0177.0.0.1/a.png",                     # octal-looking
    "https://0.0.0.0/a.png",
    "https://10.0.0.5/a.png",
    "https://172.16.4.4/a.png",
    "https://192.168.1.10/a.png",
    "https://100.64.0.1/a.png",                     # CGNAT
    "https://169.254.169.254/latest/meta-data/",    # cloud metadata
    "https://[::1]/a.png",
    "https://[fe80::1]/a.png",
    "https://[fc00::1]/a.png",
    "https://[::ffff:127.0.0.1]/a.png",             # IPv4-mapped loopback
    "https://[::ffff:169.254.169.254]/a.png",
    "https://metadata.google.internal/computeMetadata/v1/",
    "https://lumen-ai-db.internal/a.png",
    "https://printer.local/a.png",
    "https://intranet/a.png",                       # single-label host
    "https://user:pass@fixtures.lumenai.dev/a.png", # credentials
    "https://fixtures.lumenai.dev:8443/a.png",      # non-default port
    "https://fixtures.lumenai.dev:22/a.png",
    "https://fixtures.lumenai.dev/a.png\r\nHost: evil",
    "https:///a.png",                               # no host
    "not a url",
]


class TestSSRFStaticValidation:
    @pytest.mark.parametrize("url", PROHIBITED_URLS)
    def test_prohibited_url_is_rejected_without_network(self, url, no_network):
        with pytest.raises(UnsafeImageURLError):
            assert_image_url_allowed(url)
        assert try_fetch_image_bytes(url) is None
        assert no_network == []

    def test_public_https_url_passes_static_validation(self, no_network):
        target = assert_image_url_allowed(PUBLIC_URL)
        assert target.host == "fixtures.lumenai.dev" and target.port == 443
        assert no_network == []

    def test_error_messages_do_not_echo_credentials(self):
        with pytest.raises(UnsafeImageURLError) as exc:
            assert_image_url_allowed("https://alice:hunter2@fixtures.lumenai.dev/a.png")
        assert "hunter2" not in str(exc.value) and "alice" not in str(exc.value)


class TestSSRFAtTheAPIBoundary:
    @pytest.mark.parametrize("url", PROHIBITED_URLS)
    def test_analyze_rejects_prohibited_url_before_any_fetch(self, url, no_network, enable_demo_scoring):
        res = client.post("/api/enterprise/cv/analyze", json={"image_url": url}, headers=DEV_ADMIN)
        assert res.status_code == 422, (url, res.text)
        assert no_network == []

    @pytest.mark.parametrize("field,route,extra", [
        ("baseline_image_url", "/api/enterprise/cv/analyze", {"image_url": PUBLIC_URL}),
        ("baseline_image_url", "/api/enterprise/cv/baseline-compare", {"inspection_image_url": PUBLIC_URL}),
        ("inspection_image_url", "/api/enterprise/cv/baseline-compare", {"baseline_image_url": PUBLIC_URL}),
        ("image_url", "/api/enterprise/cv/analyze-and-rank", {}),
        ("image_url", "/api/enterprise/cv/analyze-async", {}),
        ("video_url", "/api/enterprise/cv/analyze-video", {}),
    ])
    def test_every_image_reference_on_every_route_is_validated(
        self, field, route, extra, no_network, enable_demo_scoring,
    ):
        payload = {**extra, field: "https://169.254.169.254/latest/meta-data/iam/"}
        res = client.post(route, json=payload, headers=DEV_ADMIN)
        assert res.status_code == 422, res.text
        assert no_network == []

    def test_rejected_request_is_not_persisted(self, no_network, enable_demo_scoring):
        tenant, _user, headers = _member()
        res = client.post(
            "/api/enterprise/cv/analyze", json={"image_url": "https://10.0.0.5/a.png"}, headers=headers,
        )
        assert res.status_code == 422
        assert client.get("/api/enterprise/cv/history", headers=headers).json() == []

    def test_invalid_uploaded_payload_is_rejected(self, no_network, enable_demo_scoring):
        res = client.post(
            "/api/enterprise/cv/analyze", json={"image_data_b64": "@@@not-base64@@@"}, headers=DEV_ADMIN,
        )
        assert res.status_code == 422


class _Recorder:
    def __init__(self):
        self.requests: list[httpx.Request] = []


def _client_factory(handler, recorder: _Recorder):
    def _handler(request: httpx.Request) -> httpx.Response:
        recorder.requests.append(request)
        return handler(request)

    def _factory(connect_timeout, read_timeout):
        return httpx.Client(transport=httpx.MockTransport(_handler), follow_redirects=False, trust_env=False)
    return _factory


def _resolver(*addresses: str):
    def _getaddrinfo(host, port, *args, **kwargs):
        return [(socket.AF_INET6 if ":" in a else socket.AF_INET, socket.SOCK_STREAM, 6, "", (a, port))
                for a in addresses]
    return _getaddrinfo


class TestSSRFFetchPolicy:
    HOST = "images.allowlisted-partner.example"
    URL = f"https://{HOST}/scans/frame-001.png?v=2"

    @pytest.fixture
    def allowlisted(self, monkeypatch):
        monkeypatch.setenv("CV_IMAGE_FETCH_ALLOWED_HOSTS", self.HOST)

    def test_public_url_is_not_fetched_unless_host_is_allowlisted(self, no_network):
        with pytest.raises(ImageFetchNotPermittedError):
            fetch_image_bytes(PUBLIC_URL)
        assert no_network == []          # refused before DNS, before any client

    def test_allowlisted_host_resolving_to_private_address_is_rejected(self, allowlisted, monkeypatch):
        """DNS rebinding: the name is allow-listed but resolves internally."""
        opened: list[int] = []
        monkeypatch.setattr(safe_fetch.socket, "getaddrinfo", _resolver("10.0.0.5"))
        monkeypatch.setattr(safe_fetch, "_open_client", lambda *a: opened.append(1))
        with pytest.raises(UnsafeImageURLError):
            fetch_image_bytes(self.URL)
        assert opened == []

    @pytest.mark.parametrize("addresses", [
        ("93.184.216.34", "127.0.0.1"),
        ("93.184.216.34", "169.254.169.254"),
        ("::1",),
        ("fe80::1%eth0",),
    ])
    def test_any_prohibited_resolved_address_rejects_the_whole_fetch(self, allowlisted, monkeypatch, addresses):
        opened: list[int] = []
        monkeypatch.setattr(safe_fetch.socket, "getaddrinfo", _resolver(*addresses))
        monkeypatch.setattr(safe_fetch, "_open_client", lambda *a: opened.append(1))
        with pytest.raises(UnsafeImageURLError):
            fetch_image_bytes(self.URL)
        assert opened == []

    def test_connection_is_pinned_to_the_validated_address(self, allowlisted, monkeypatch):
        rec = _Recorder()
        monkeypatch.setattr(safe_fetch.socket, "getaddrinfo", _resolver("93.184.216.34"))
        monkeypatch.setattr(
            safe_fetch, "_open_client",
            _client_factory(lambda r: httpx.Response(200, content=b"\x89PNG-bytes"), rec),
        )
        assert fetch_image_bytes(self.URL) == b"\x89PNG-bytes"
        assert len(rec.requests) == 1
        req = rec.requests[0]
        assert req.url.host == "93.184.216.34"            # connected to the validated IP
        assert req.headers["host"] == self.HOST           # Host header is the real name
        assert req.extensions["sni_hostname"] == self.HOST  # TLS verified against the name
        assert req.url.path == "/scans/frame-001.png" and req.url.query == b"v=2"

    @pytest.mark.parametrize("status,location", [
        (301, "https://169.254.169.254/latest/meta-data/"),
        (302, "http://localhost/admin"),
        (307, "https://images.allowlisted-partner.example/other.png"),
        (308, "file:///etc/passwd"),
    ])
    def test_redirects_are_never_followed(self, allowlisted, monkeypatch, status, location):
        rec = _Recorder()
        monkeypatch.setattr(safe_fetch.socket, "getaddrinfo", _resolver("93.184.216.34"))
        monkeypatch.setattr(
            safe_fetch, "_open_client",
            _client_factory(lambda r: httpx.Response(status, headers={"location": location}), rec),
        )
        with pytest.raises(ImageFetchError):
            fetch_image_bytes(self.URL)
        assert len(rec.requests) == 1                     # the redirect target was never requested

    def test_declared_oversize_body_is_rejected(self, allowlisted, monkeypatch):
        rec = _Recorder()
        monkeypatch.setattr(safe_fetch.socket, "getaddrinfo", _resolver("93.184.216.34"))
        monkeypatch.setattr(
            safe_fetch, "_open_client",
            _client_factory(lambda r: httpx.Response(200, content=b"x" * 64), rec),
        )
        with pytest.raises(ImageFetchError):
            fetch_image_bytes(self.URL, max_bytes=16)

    def test_streamed_oversize_body_is_rejected_without_a_content_length(self, allowlisted, monkeypatch):
        def _chunks():
            for _ in range(8):
                yield b"x" * 16

        rec = _Recorder()
        monkeypatch.setattr(safe_fetch.socket, "getaddrinfo", _resolver("93.184.216.34"))
        monkeypatch.setattr(
            safe_fetch, "_open_client",
            _client_factory(lambda r: httpx.Response(200, content=_chunks()), rec),
        )
        with pytest.raises(ImageFetchError):
            fetch_image_bytes(self.URL, max_bytes=40)

    @pytest.mark.parametrize("status", [401, 403, 404, 500])
    def test_non_200_is_a_failure(self, allowlisted, monkeypatch, status):
        rec = _Recorder()
        monkeypatch.setattr(safe_fetch.socket, "getaddrinfo", _resolver("93.184.216.34"))
        monkeypatch.setattr(safe_fetch, "_open_client", _client_factory(lambda r: httpx.Response(status), rec))
        with pytest.raises(ImageFetchError):
            fetch_image_bytes(self.URL)

    def test_transport_errors_do_not_leak_detail(self, allowlisted, monkeypatch):
        def _boom(request):
            raise httpx.ConnectError("connect to 93.184.216.34 with token=SECRET failed")

        rec = _Recorder()
        monkeypatch.setattr(safe_fetch.socket, "getaddrinfo", _resolver("93.184.216.34"))
        monkeypatch.setattr(safe_fetch, "_open_client", _client_factory(_boom, rec))
        with pytest.raises(ImageFetchError) as exc:
            fetch_image_bytes(self.URL)
        assert "SECRET" not in str(exc.value)

    def test_client_is_built_without_redirects_or_env_proxies(self):
        with safe_fetch._open_client(1.0, 1.0) as c:
            assert c.follow_redirects is False
            assert c.trust_env is False
            assert c.timeout.connect == 1.0 and c.timeout.read == 1.0


class TestNoOtherFetchRoutes:
    """Every former httpx.get call site now goes through the safe fetcher."""

    def test_no_direct_http_calls_remain_in_app_cv(self):
        import pathlib
        cv_dir = pathlib.Path(safe_fetch.__file__).parent
        offenders = []
        for path in cv_dir.glob("*.py"):
            if path.name == "safe_fetch.py":
                continue
            text = path.read_text()
            for needle in ("httpx.get(", "httpx.post(", "requests.get(", "urlopen(", "follow_redirects=True"):
                if needle in text:
                    offenders.append((path.name, needle))
        assert offenders == []

    def test_archive_does_not_fetch_when_no_backend_is_configured(self, monkeypatch, no_network):
        import app.cv.image_store as store
        # Set explicitly: another test module may have reloaded the store with
        # a backend configured, and this check must never be skipped.
        monkeypatch.setattr(store, "_BACKEND", "noop")
        result = store.archive_image(image_bytes=None, image_url=PUBLIC_URL, inference_id="inf-x", tenant_id="t")
        assert result.stored is False and no_network == []

    @pytest.mark.parametrize("url", [PUBLIC_URL, "https://169.254.169.254/latest/meta-data/",
                                     "http://127.0.0.1/x.png"])
    def test_archive_with_a_backend_still_obeys_the_fetch_policy(self, monkeypatch, tmp_path, no_network, url):
        """With an archive backend configured, a URL that is prohibited or not
        on the (default-empty) allow-list is still never retrieved."""
        import app.cv.image_store as store
        monkeypatch.setattr(store, "_BACKEND", "local")
        monkeypatch.setattr(store, "_LOCAL_DIR", tmp_path)
        monkeypatch.delenv("CV_IMAGE_FETCH_ALLOWED_HOSTS", raising=False)
        result = store.archive_image(image_bytes=None, image_url=url, inference_id="inf-x", tenant_id="t")
        assert result.stored is False and no_network == []
        assert list(tmp_path.rglob("*.bin")) == []

    def test_archive_key_cannot_escape_via_tenant_or_id(self):
        import app.cv.image_store as store
        assert "/" not in store._safe_component("../../etc")
        assert ".." not in store._safe_component("../../etc")

    def test_identifier_decoder_does_not_fetch_prohibited_urls(self, no_network):
        from app.cv.identifier_decoder import decode_from_url
        decoded = decode_from_url("https://169.254.169.254/x.png")
        assert decoded.barcode_value == "" and no_network == []

    def test_baseline_similarity_is_unavailable_not_mocked(self, monkeypatch, no_network):
        from app.cv.ssim_comparator import compare_images
        _set_env(monkeypatch, "production")
        result = compare_images(PUBLIC_URL, PUBLIC_URL)
        assert result.backend == "unavailable"
        assert result.match_pct == 0.0 and result.diff_regions == []
        assert no_network == []


# ══ Step 5 / SCI-16 + Step 7 — ONNX fault injection ══════════════════════════

class _Session:
    def __init__(self, outputs=None, error: Exception | None = None):
        self.outputs, self.error, self.calls = outputs, error, 0

    def run(self, *_a, **_k):
        self.calls += 1
        if self.error is not None:
            raise self.error
        return self.outputs


@pytest.fixture
def onnx_provider(monkeypatch, tmp_path):
    """An OnnxCVProvider with injected sessions (no onnxruntime, no numpy)."""
    import app.cv.onnx_provider as onnx_mod

    fake_numpy = types.ModuleType("numpy")
    fake_numpy.argmax = lambda seq: max(range(len(seq)), key=seq.__getitem__)
    monkeypatch.setitem(sys.modules, "numpy", fake_numpy)
    monkeypatch.setattr(onnx_mod, "_preprocess_image", lambda raw, size: ("tensor", size))

    provider = object.__new__(onnx_mod.OnnxCVProvider)
    provider.model_dir = tmp_path
    provider._integrity = {"verified": True, "artifacts": {"instrument_classifier": "a" * 64,
                                                           "finding_detector": "b" * 64}}
    provider._classifier = _Session(outputs=[[[0.9, 0.1]]])
    provider._detector = _Session(outputs=[[[[0.1, 0.1, 0.5, 0.5, 0.91, 0]]]])
    provider._ort = None
    return provider


def _b64_png() -> str:
    import base64
    return base64.b64encode(_png()).decode()


class TestOnnxFailureIsNeverClean:
    def test_detector_exception_is_failed_not_empty_success(self, onnx_provider):
        onnx_provider._detector = _Session(error=RuntimeError("CUDA out of memory at /models/x"))
        result = onnx_provider.analyze(CVAnalysisRequest(image_data_b64=_b64_png()))
        data = result.model_dump()
        assert data["status"] == "failed"
        _assert_nothing_fabricated_cv(data)
        assert data["evidence_class"] == EVIDENCE_FAILED
        assert "/models/x" not in data["unavailable_reason"]

    def test_classifier_exception_is_failed(self, onnx_provider):
        onnx_provider._classifier = _Session(error=ValueError("bad input shape"))
        data = onnx_provider.analyze(CVAnalysisRequest(image_data_b64=_b64_png())).model_dump()
        assert data["status"] == "failed"
        _assert_nothing_fabricated_cv(data)
        assert onnx_provider._detector.calls == 0

    def test_missing_detector_is_unavailable_not_no_findings(self, onnx_provider):
        onnx_provider._detector = None
        data = onnx_provider.analyze(CVAnalysisRequest(image_data_b64=_b64_png())).model_dump()
        assert data["status"] == "ai_unavailable"
        _assert_nothing_fabricated_cv(data)

    def test_unobtainable_image_is_unavailable_and_not_fetched(self, onnx_provider, no_network):
        data = onnx_provider.analyze(CVAnalysisRequest(image_url=PUBLIC_URL)).model_dump()
        assert data["status"] == "ai_unavailable"
        _assert_nothing_fabricated_cv(data)
        assert onnx_provider._classifier.calls == 0 and onnx_provider._detector.calls == 0
        assert no_network == []

    def test_prohibited_image_url_is_never_fetched_by_the_provider(self, onnx_provider, no_network):
        data = onnx_provider.analyze(
            CVAnalysisRequest(image_url="https://169.254.169.254/latest/meta-data/"),
        ).model_dump()
        assert data["status"] == "ai_unavailable"
        assert no_network == []

    def test_undecodable_upload_is_unavailable(self, onnx_provider):
        data = onnx_provider.analyze(CVAnalysisRequest(image_data_b64="%%%")).model_dump()
        assert data["status"] == "ai_unavailable"
        _assert_nothing_fabricated_cv(data)

    def test_successful_run_is_marked_as_verified_model_inference(self, onnx_provider):
        result = onnx_provider.analyze(CVAnalysisRequest(image_data_b64=_b64_png()))
        assert result.status == "success"
        assert result.simulated is False
        assert result.evidence_class == EVIDENCE_MODEL_INFERENCE
        assert result.model_integrity["verified"] is True
        assert len(result.regions) == 1 and result.regions[0].simulated is False
        assert result.human_review_required is True

    def test_empty_detections_from_a_working_model_is_a_real_result(self, onnx_provider):
        """Distinct from failure: the detector RAN and reported nothing."""
        onnx_provider._detector = _Session(outputs=[[[]]])
        result = onnx_provider.analyze(CVAnalysisRequest(image_data_b64=_b64_png()))
        assert result.status == "success" and result.regions == []
        assert result.ranking_inputs == {}          # no invented finding to rank
        assert onnx_provider._detector.calls == 1


class TestOnnxArtifactIntegrity:
    @pytest.fixture
    def fake_ort(self, monkeypatch, tmp_path):
        sessions: list[str] = []
        ort = types.ModuleType("onnxruntime")
        ort.InferenceSession = lambda path: sessions.append(path) or _Session(outputs=[[[1.0]]])
        monkeypatch.setitem(sys.modules, "onnxruntime", ort)
        (tmp_path / "instrument_classifier.onnx").write_bytes(b"classifier-bytes")
        (tmp_path / "finding_detector.onnx").write_bytes(b"detector-bytes")
        monkeypatch.setenv("CV_ONNX_MODEL_DIR", str(tmp_path))
        return sessions, tmp_path

    def _pin(self, monkeypatch, tmp_path, *, classifier=True, detector=True):
        if classifier:
            monkeypatch.setenv("CV_ONNX_CLASSIFIER_SHA256",
                               hashlib.sha256((tmp_path / "instrument_classifier.onnx").read_bytes()).hexdigest())
        if detector:
            monkeypatch.setenv("CV_ONNX_DETECTOR_SHA256",
                               hashlib.sha256((tmp_path / "finding_detector.onnx").read_bytes()).hexdigest())

    def test_artifacts_without_pins_are_never_loaded(self, fake_ort):
        from app.cv.onnx_provider import OnnxCVProvider
        sessions, _ = fake_ort
        with pytest.raises(LocalInferenceUnavailable):
            OnnxCVProvider()
        assert sessions == []

    def test_classifier_hash_mismatch_is_never_loaded(self, fake_ort, monkeypatch):
        from app.cv.onnx_provider import OnnxCVProvider
        sessions, tmp_path = fake_ort
        self._pin(monkeypatch, tmp_path, classifier=False)
        monkeypatch.setenv("CV_ONNX_CLASSIFIER_SHA256", "0" * 64)
        with pytest.raises(LocalInferenceUnavailable):
            OnnxCVProvider()
        assert sessions == []

    def test_detector_without_pin_fails_closed(self, fake_ort, monkeypatch):
        from app.cv.onnx_provider import OnnxCVProvider
        _sessions, tmp_path = fake_ort
        self._pin(monkeypatch, tmp_path, detector=False)
        with pytest.raises(LocalInferenceUnavailable):
            OnnxCVProvider()

    def test_pinned_artifacts_load_and_record_their_digests(self, fake_ort, monkeypatch):
        from app.cv.onnx_provider import OnnxCVProvider
        sessions, tmp_path = fake_ort
        self._pin(monkeypatch, tmp_path)
        provider = OnnxCVProvider()
        assert len(sessions) == 2
        assert provider._integrity["verified"] is True
        assert set(provider._integrity["artifacts"]) == {"instrument_classifier", "finding_detector"}

    def test_registry_resolves_a_broken_onnx_config_to_unavailable_not_mock(
        self, fake_ort, monkeypatch, enable_demo_scoring,
    ):
        """With the simulation gate OPEN and CV_PROVIDER=onnx misconfigured, the
        registry must still not hand back the mock."""
        monkeypatch.setenv("CV_PROVIDER", "onnx")
        provider = CVRegistry.get_provider()
        assert provider.provider_name == "unavailable"
        assert provider.status == "failed"
        result = provider.analyze(CVAnalysisRequest(image_url=PUBLIC_URL))
        _assert_nothing_fabricated_cv(result.model_dump())

    def test_missing_runtime_is_unavailable(self, monkeypatch):
        monkeypatch.setitem(sys.modules, "onnxruntime", None)
        monkeypatch.setenv("CV_PROVIDER", "onnx")
        assert CVRegistry.get_provider().provider_name == "unavailable"


# ══ Step 6 / SCI-17 — simulated vs operational evidence ══════════════════════

def _result_json(**overrides) -> str:
    base = dict(
        inference_id=_uid("inf"), status="success", tenant_id="t",
        instrument_identity=InstrumentIdentity(recognized=True, instrument_name="X", confidence=0.9),
        identifier_reads=IdentifierReads(), provider="onnx",
        contamination_score=75.0, damage_score=100.0, overall_cleanliness_score=85.0,
    )
    base.update(overrides)
    return CVInferenceResult(**base).model_dump_json()


def _seed_record(tenant: str, *, provider: str, status: str = "success", blood: int = 0,
                 result_json: str | None = None, review_required: bool = False) -> str:
    inference_id = _uid("inf")
    db = SessionLocal()
    try:
        db.add(CVInferenceRecord(
            inference_id=inference_id, tenant_id=tenant, provider=provider, status=status,
            instrument_recognized=True, instrument_confidence=0.9, blood_count=blood,
            finding_count=blood, overall_cleanliness_score=85.0, review_required=review_required,
            result_json=result_json if result_json is not None else _result_json(provider=provider, status=status),
        ))
        db.commit()
    finally:
        db.close()
    return inference_id


def _seed_trusted_record(tenant: str, *, blood: int = 0) -> str:
    """A record sealed exactly the way the pipeline seals a completed model run:
    stored, then given server-issued provenance for an APPROVED artifact digest.

    The digest and key are synthetic test values — no model ran. What this fixture
    represents is "the server sealed this run", which is the only thing that makes a
    record verified model inference."""
    from app.cv.provenance import issue_provenance

    inference_id = _uid("inf")
    saved = os.environ.get("CV_ONNX_DETECTOR_SHA256")
    os.environ["CV_ONNX_DETECTOR_SHA256"] = SEALED_ARTIFACT   # approved only while sealing
    db = SessionLocal()
    try:
        record = CVInferenceRecord(
            inference_id=inference_id, tenant_id=tenant, provider="onnx", status="success",
            instrument_recognized=True, instrument_confidence=0.9, blood_count=blood,
            finding_count=blood, overall_cleanliness_score=85.0,
            result_json=_result_json(provider="onnx", status="success"),
        )
        db.add(record)
        db.flush()
        issue_provenance(
            db, record, authenticated_tenant_id=tenant,
            artifacts={"finding_detector": SEALED_ARTIFACT}, model_versions={"finding_detector": "test"},
        )
        db.commit()
    finally:
        db.close()
        if saved is None:
            os.environ.pop("CV_ONNX_DETECTOR_SHA256", None)
        else:
            os.environ["CV_ONNX_DETECTOR_SHA256"] = saved
    return inference_id


def _seed_mixed_tenant() -> tuple[dict, dict[str, str]]:
    tenant, _user, headers = _member("p471-kpi")
    ids = {
        # Legacy row written by the old default provider — simulated.
        "simulated": _seed_record(tenant, provider="mock", blood=3, review_required=True),
        "unavailable": _seed_record(tenant, provider="unavailable", status="ai_unavailable"),
        "failed": _seed_record(tenant, provider="onnx", status="failed"),
        # A pre-provenance "onnx success" row.
        "legacy": _seed_record(tenant, provider="onnx", blood=2),
        # P4.7.2: a row that CLAIMS to be verified model inference in its own payload
        # and has no server-issued provenance. Until P4.7.2 this was how these tests
        # built their "genuine" row — which is exactly the forgery being closed.
        "forged": _seed_record(
            tenant, provider="onnx", blood=7,
            result_json=_result_json(evidence_class=EVIDENCE_MODEL_INFERENCE,
                                     model_integrity={"verified": True, "artifacts": {}}),
        ),
        "genuine": _seed_trusted_record(tenant, blood=1),
    }
    return headers, ids


class TestEvidenceClassification:
    @pytest.mark.parametrize("kwargs,expected", [
        (dict(provider="mock", status="success", simulated=None, provenance_trusted=False), EVIDENCE_SIMULATED),
        # A mock row can never be promoted, even if provenance were somehow presented.
        (dict(provider="mock", status="success", simulated=False, provenance_trusted=True), EVIDENCE_SIMULATED),
        # A stored "simulated" claim still DEMOTES a record.
        (dict(provider="onnx", status="success", simulated=True, provenance_trusted=True), EVIDENCE_SIMULATED),
        (dict(provider="unavailable", status="success", simulated=None, provenance_trusted=True),
         EVIDENCE_AI_UNAVAILABLE),
        (dict(provider="onnx", status="ai_unavailable", simulated=None, provenance_trusted=True),
         EVIDENCE_AI_UNAVAILABLE),
        (dict(provider="onnx", status="failed", simulated=None, provenance_trusted=True), EVIDENCE_FAILED),
        # A completed run with no trusted provenance is never model inference.
        (dict(provider="onnx", status="success", simulated=None, provenance_trusted=False),
         EVIDENCE_LEGACY_UNVERIFIED),
        (dict(provider="onnx", status="partial", simulated=False, provenance_trusted=False),
         EVIDENCE_LEGACY_UNVERIFIED),
        (dict(provider="onnx", status="success", simulated=False, provenance_trusted=True),
         EVIDENCE_MODEL_INFERENCE),
        (dict(provider="onnx", status="partial", simulated=False, provenance_trusted=True),
         EVIDENCE_MODEL_INFERENCE),
        # An unknown status is not a completed run, whatever else is presented.
        (dict(provider="onnx", status="queued", simulated=False, provenance_trusted=True),
         EVIDENCE_LEGACY_UNVERIFIED),
        (dict(provider="", status="", simulated=None, provenance_trusted=False), EVIDENCE_LEGACY_UNVERIFIED),
    ])
    def test_classify(self, kwargs, expected):
        assert classify(**kwargs) == expected

    def test_classify_has_no_parameter_a_stored_payload_can_supply(self):
        """The rule takes provenance as a verified boolean; the claim fields that
        P4.7.1 read from ``result_json`` are gone from its signature."""
        import inspect

        parameters = set(inspect.signature(classify).parameters)
        assert parameters == {"provider", "status", "simulated", "provenance_trusted"}


class TestSimulatedNeverCountsAsEvidence:
    def test_kpis_count_only_verified_model_inference(self):
        headers, _ids = _seed_mixed_tenant()
        body = client.get("/api/enterprise/cv/kpi-summary", headers=headers).json()
        assert body["evidence_basis"] == "model_inference_only"
        assert body["total_analyses"] == 1 and body["genuine_analyses"] == 1
        assert body["blood_detections"] == 1          # NOT 1 + 3 (simulated) + 2 (legacy) + 7 (forged)
        assert body["simulated_excluded_count"] == 1
        assert body["unavailable_or_failed_count"] == 2
        assert body["legacy_unverified_excluded_count"] == 2   # the legacy row AND the forged row
        assert body["review_queue_size"] == 0         # the simulated row was flagged; it is not counted

    @pytest.mark.parametrize("app_env", NON_SIMULATION_ENVS)
    def test_include_simulated_is_ignored_outside_dev_test(self, monkeypatch, app_env):
        headers, _ids = _seed_mixed_tenant()
        _set_env(monkeypatch, app_env)
        body = client.get("/api/enterprise/cv/kpi-summary?include_simulated=true", headers=headers).json()
        assert body["evidence_basis"] == "model_inference_only"
        assert body["blood_detections"] == 1 and body["simulated_excluded_count"] == 1

    def test_include_simulated_is_explicit_and_labelled_in_dev_test(self, enable_demo_scoring):
        headers, _ids = _seed_mixed_tenant()
        body = client.get("/api/enterprise/cv/kpi-summary?include_simulated=true", headers=headers).json()
        assert body["evidence_basis"] == "includes_simulated_dev_test_only"
        assert body["blood_detections"] == 4          # genuine 1 + simulated 3; legacy + forged excluded
        assert body["legacy_unverified_excluded_count"] == 2

    def test_history_distinguishes_every_row(self):
        headers, ids = _seed_mixed_tenant()
        rows = {r["inference_id"]: r for r in client.get("/api/enterprise/cv/history", headers=headers).json()}
        expected = {
            "simulated": EVIDENCE_SIMULATED, "unavailable": EVIDENCE_AI_UNAVAILABLE, "failed": EVIDENCE_FAILED,
            "legacy": EVIDENCE_LEGACY_UNVERIFIED, "forged": EVIDENCE_LEGACY_UNVERIFIED,
            "genuine": EVIDENCE_MODEL_INFERENCE,
        }
        for key, cls in expected.items():
            row = rows[ids[key]]
            assert row["evidence_class"] == cls
            assert row["simulated"] is (cls == EVIDENCE_SIMULATED)
            assert row["operational_evidence"] is (cls == EVIDENCE_MODEL_INFERENCE)
        # A stored score or defect metric is never presented for a row whose inference
        # was not established — including the row that forges its own evidence claim.
        for key in ("unavailable", "failed", "legacy", "forged"):
            assert rows[ids[key]]["overall_cleanliness_score"] is None
            assert rows[ids[key]]["finding_count"] is None
            assert rows[ids[key]]["baseline_match_pct"] is None
        assert rows[ids["genuine"]]["overall_cleanliness_score"] == 85.0
        assert rows[ids["genuine"]]["finding_count"] == 1

    def test_legacy_record_is_not_promoted_on_retrieval(self):
        headers, ids = _seed_mixed_tenant()
        legacy_row = client.get(f"/api/enterprise/cv/inference/{ids['legacy']}", headers=headers).json()
        assert legacy_row["evidence_class"] == EVIDENCE_LEGACY_UNVERIFIED
        assert legacy_row["simulated"] is False
        assert legacy_row["overall_cleanliness_score"] is None

        simulated_row = client.get(f"/api/enterprise/cv/inference/{ids['simulated']}", headers=headers).json()
        assert simulated_row["evidence_class"] == EVIDENCE_SIMULATED and simulated_row["simulated"] is True

        genuine_row = client.get(f"/api/enterprise/cv/inference/{ids['genuine']}", headers=headers).json()
        assert genuine_row["evidence_class"] == EVIDENCE_MODEL_INFERENCE
        assert genuine_row["overall_cleanliness_score"] == 85.0
        assert genuine_row["model_integrity"]["verified"] is True
        assert genuine_row["model_integrity"]["artifacts"] == {"finding_detector": SEALED_ARTIFACT}

        # P4.7.2: the forged row's own claims are not echoed back as if verified.
        forged_row = client.get(f"/api/enterprise/cv/inference/{ids['forged']}", headers=headers).json()
        assert forged_row["evidence_class"] == EVIDENCE_LEGACY_UNVERIFIED
        assert forged_row["overall_cleanliness_score"] is None
        assert forged_row["model_integrity"] == {"verified": False, "reason": "no_provenance"}
        assert forged_row["regions"] == []

    def test_metrics_report_an_evidence_breakdown(self):
        headers, _ids = _seed_mixed_tenant()
        body = client.get("/api/enterprise/cv/provider/metrics", headers=headers).json()
        assert body["evidence_breakdown"] == {
            EVIDENCE_SIMULATED: 1, EVIDENCE_AI_UNAVAILABLE: 1, EVIDENCE_FAILED: 1,
            EVIDENCE_LEGACY_UNVERIFIED: 2, EVIDENCE_MODEL_INFERENCE: 1,
        }

    def test_review_queue_labels_simulated_rows(self):
        headers, ids = _seed_mixed_tenant()
        queue = client.get("/api/enterprise/cv/review-queue", headers=headers).json()
        assert [q["inference_id"] for q in queue] == [ids["simulated"]]
        assert queue[0]["simulated"] is True and queue[0]["evidence_class"] == EVIDENCE_SIMULATED

    def test_a_new_simulated_analysis_is_stored_as_simulated_and_excluded(self, enable_demo_scoring, no_network):
        tenant, _user, headers = _member("p471-kpi")
        res = client.post("/api/enterprise/cv/analyze", json={"image_url": PUBLIC_URL}, headers=headers)
        inference_id = res.json()["inference_id"]

        db = SessionLocal()
        try:
            rec = db.query(CVInferenceRecord).filter(CVInferenceRecord.inference_id == inference_id).first()
            assert rec.provider == "mock" and rec.tenant_id == tenant
            assert rec.review_required is False       # simulated rows never enter the annotation queue
        finally:
            db.close()

        body = client.get("/api/enterprise/cv/kpi-summary", headers=headers).json()
        assert body["total_analyses"] == 0 and body["simulated_excluded_count"] == 1
        assert body["blood_detections"] == 0 and body["recognition_rate_pct"] == 0.0

    def test_a_new_unavailable_analysis_is_stored_as_unavailable(self, monkeypatch, no_network):
        _set_env(monkeypatch, "production")
        _tenant, _user, headers = _member("p471-kpi")
        inference_id = client.post(
            "/api/enterprise/cv/analyze", json={"image_url": PUBLIC_URL}, headers=headers,
        ).json()["inference_id"]
        rows = client.get("/api/enterprise/cv/history", headers=headers).json()
        assert rows[0]["inference_id"] == inference_id
        assert rows[0]["evidence_class"] == EVIDENCE_AI_UNAVAILABLE
        # P4.7.2: a not-evaluated row presents no defect metric at all — not even a zero.
        assert rows[0]["overall_cleanliness_score"] is None and rows[0]["finding_count"] is None

    def test_simulated_ranking_is_stamped(self, enable_demo_scoring, no_network):
        res = client.post(
            "/api/enterprise/cv/analyze-and-rank",
            json={"image_url": "https://fixtures.lumenai.dev/baselines/frazier-suction-8fr.jpg"}, headers=DEV_ADMIN,
        ).json()
        if res["cv"]["regions"]:
            assert res["ranking"]["simulated"] is True
            assert res["ranking"]["evidence_class"] == EVIDENCE_SIMULATED
        else:
            assert res["ranking"]["ranking_mode"] == "not_ranked"


# ══ Step 6 / SCI-17 — downstream consumers of stored CV records ══════════════

class TestDownstreamConsumersUseOperationalEvidenceOnly:
    """Accreditation, benchmarking, prediction, digital-twin, vendor-intelligence
    and copilot services all read ``cv_inference_records``. Before P4.7.1 they
    read every row, so a simulated row was aggregated as real data."""

    def test_sql_criteria_select_only_verified_model_inference(self):
        from app.cv.evidence import operational_sql_criteria

        headers, ids = _seed_mixed_tenant()
        tenant = client.get("/api/enterprise/cv/history", headers=headers)  # ensure tenant resolves
        assert tenant.status_code == 200
        db = SessionLocal()
        try:
            all_ids = set(ids.values())
            rows = (
                db.query(CVInferenceRecord)
                .filter(CVInferenceRecord.inference_id.in_(all_ids),
                        *operational_sql_criteria(CVInferenceRecord))
                .all()
            )
            assert [r.inference_id for r in rows] == [ids["genuine"]]
        finally:
            db.close()

    def test_every_reader_of_cv_records_applies_the_evidence_filter(self):
        """Static guard: any app module that imports ``CVInferenceRecord`` must
        apply the shared evidence filter. A new unfiltered reader fails here."""
        import pathlib
        import re

        app_dir = pathlib.Path(safe_fetch.__file__).parents[1]
        exempt = {
            "models/cv_inference.py",   # the model itself
            "cv/pipeline.py",           # the writer (seals before committing)
            "cv/provenance.py",         # issues and verifies provenance
            "cv/evidence.py",           # defines the criteria and the integrity check
            "routes/cv.py",             # classifies every row with classify_record(s)
        }
        importers, offenders = [], []
        for path in sorted(app_dir.rglob("*.py")):
            rel = path.relative_to(app_dir).as_posix()
            text = path.read_text(encoding="utf-8")
            if not re.search(r"^\s*from app\.models\.cv_inference import|^\s*import app\.models\.cv_inference",
                             text, re.MULTILINE):
                continue
            importers.append(rel)
            if rel in exempt:
                continue
            filtered = text.count("*operational_sql_criteria(CVInferenceRecord)")
            verified = text.count("integrity_verified(")
            # P4.7.2: the relational filter alone cannot check a provenance seal, so
            # every filtered query must also pass its rows through integrity_verified.
            if filtered == 0 or verified < filtered:
                offenders.append((rel, filtered, verified))
        assert offenders == []
        # The guard must actually be looking at the known readers.
        for expected in ("services/accreditation_engine.py", "services/benchmark_engine.py",
                         "services/prediction_engine.py", "services/digital_twin_engine.py",
                         "services/copilot_engine.py", "services/vendor_intelligence_engine.py"):
            assert expected in importers

    def test_accreditation_does_not_treat_simulated_rows_as_real_data(self):
        from app.services.accreditation_engine import compute_accreditation_readiness

        tenant = _uid("p471-accr-tenant")
        _seed_record(tenant, provider="mock", blood=5)                 # simulated
        _seed_record(tenant, provider="onnx", blood=4)                 # legacy, unverified
        _seed_record(tenant, provider="unavailable", status="ai_unavailable")
        db = SessionLocal()
        try:
            result = compute_accreditation_readiness(tenant, db=db)
        finally:
            db.close()
        assert result.data_source != "real"

    def test_accreditation_uses_verified_model_inference(self):
        from app.services.accreditation_engine import compute_accreditation_readiness

        tenant = _uid("p471-accr-tenant")
        _seed_trusted_record(tenant, blood=1)
        db = SessionLocal()
        try:
            result = compute_accreditation_readiness(tenant, db=db)
        finally:
            db.close()
        assert result.data_source == "real"

    def test_accreditation_ignores_a_row_that_forges_its_own_evidence_claim(self):
        from app.services.accreditation_engine import compute_accreditation_readiness

        tenant = _uid("p471-accr-tenant")
        _seed_record(
            tenant, provider="onnx", blood=9,
            result_json=_result_json(evidence_class=EVIDENCE_MODEL_INFERENCE,
                                     model_integrity={"verified": True, "artifacts": {}}),
        )
        db = SessionLocal()
        try:
            result = compute_accreditation_readiness(tenant, db=db)
        finally:
            db.close()
        assert result.data_source != "real"

    def test_cross_hospital_signals_ignore_simulated_rows(self):
        """vendor_intelligence_engine sums finding counts across ALL tenants."""
        from sqlalchemy import func

        from app.cv.evidence import operational_sql_criteria

        tenant = _uid("p471-signal-tenant")
        _seed_record(tenant, provider="mock", blood=1000)
        db = SessionLocal()
        try:
            unfiltered = db.query(func.sum(CVInferenceRecord.blood_count)).filter(
                CVInferenceRecord.tenant_id == tenant).scalar() or 0
            filtered = db.query(func.sum(CVInferenceRecord.blood_count)).filter(
                CVInferenceRecord.tenant_id == tenant,
                *operational_sql_criteria(CVInferenceRecord)).scalar() or 0
        finally:
            db.close()
        assert unfiltered == 1000 and filtered == 0

    def test_pipeline_written_rows_match_the_sql_filter_end_to_end(
        self, monkeypatch, onnx_provider, enable_demo_scoring,
    ):
        """The SQL filter keys on what the real pipeline writes — prove it with
        rows persisted by ``run_analysis`` itself, not hand-built fixtures."""
        from app.cv.evidence import integrity_verified, operational_sql_criteria
        from app.cv.mock_provider import MockCVProvider
        from app.cv.pipeline import run_analysis

        # P4.7.2: the fixture provider's two verified digests are approved pins here,
        # so the pipeline can seal its run.
        monkeypatch.setenv("CV_ONNX_CLASSIFIER_SHA256", "a" * 64)
        monkeypatch.setenv("CV_ONNX_DETECTOR_SHA256", "b" * 64)
        tenant = _uid("p471-e2e-tenant")
        db = SessionLocal()
        try:
            monkeypatch.setattr(CVRegistry, "get_provider", classmethod(lambda cls: onnx_provider))
            genuine = run_analysis(CVAnalysisRequest(image_data_b64=_b64_png(), tenant_id=tenant), db=db)
            monkeypatch.setattr(CVRegistry, "get_provider", classmethod(lambda cls: MockCVProvider()))
            simulated = run_analysis(CVAnalysisRequest(image_data_b64=_b64_png(), tenant_id=tenant), db=db)

            assert genuine.evidence_class == EVIDENCE_MODEL_INFERENCE
            assert simulated.evidence_class == EVIDENCE_SIMULATED
            stored = db.query(CVInferenceRecord).filter(CVInferenceRecord.tenant_id == tenant).all()
            assert {r.inference_id for r in stored} == {genuine.inference_id, simulated.inference_id}
            operational = (
                db.query(CVInferenceRecord)
                .filter(CVInferenceRecord.tenant_id == tenant, *operational_sql_criteria(CVInferenceRecord))
                .all()
            )
            assert [r.inference_id for r in operational] == [genuine.inference_id]
            assert [r.inference_id for r in integrity_verified(db, operational)] == [genuine.inference_id]
        finally:
            db.close()
