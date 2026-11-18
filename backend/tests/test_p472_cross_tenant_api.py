"""P4.7.2 — authenticated cross-tenant API adversarial tests (tenant A vs tenant B).

This file is about API AUTHORIZATION, not provenance. A provenance row being
bound to a tenant says a sealed run cannot be re-attributed; it says nothing
about whether an authenticated member of tenant A can reach tenant B's data
through an HTTP route. That is tested here, end to end, through the real app:

* two tenants, each with a real membership-verified user and a signed JWT;
* each tenant holds its own sealed inference runs, created through the API;
* every request goes through ``TestClient`` — no handler is called directly.

Covered: unauthorized access, writes, inference results, evidence retrieval
and operational aggregation, on every enterprise CV route (the list is checked
against the mounted routes, so a new CV route without a row here fails) and on
the API routes of the six analytics services that consume CV records.

The 13 downstream cases that were strict ``xfail`` when this file was written
(finding P472-03: a route authenticated the caller for their own tenant and then
served the tenant named in the request) are ordinary tests now that the routes
are fixed. Every endpoint of those modules is covered in
``test_p472_03_tenant_authorization.py``.

Everything is synthetic: canned provider outputs, constant digests, a test key.
"""
from __future__ import annotations

import base64
import io
import json
import sys
import time
import types
import uuid
from dataclasses import dataclass, field

import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from PIL import Image

from app.cv import provenance
from app.cv.evidence import EVIDENCE_MODEL_INFERENCE
from app.cv.provenance import verify_record
from app.cv.registry import CVRegistry
from app.db import models
from app.db.session import SessionLocal
from app.main import app
from app.models.cv_inference import CVInferenceProvenance, CVInferenceRecord
from app.routers.auth_simple import _make_token

client = TestClient(app)

CV = "/api/enterprise/cv"
TEST_KEY = "test-only-provenance-key-not-a-secret-0123456789"
CLASSIFIER_DIGEST = "a" * 64
DETECTOR_DIGEST = "b" * 64
REFUSED = (401, 403)


# ── helpers ───────────────────────────────────────────────────────────────────

def _uid(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10]}"


def _b64_png() -> str:
    buf = io.BytesIO()
    Image.new("RGB", (64, 64), (200, 200, 200)).save(buf, "PNG")
    return base64.b64encode(buf.getvalue()).decode()


PNG = _b64_png()


def _bearer(user: str) -> dict:
    return {"Authorization": f"Bearer {_make_token(user)}"}


def _add_membership(tenant: str, user: str, *, enabled: bool = True) -> None:
    db = SessionLocal()
    try:
        db.add(models.TenantMembership(
            tenant_id=tenant, user_email=user, role="viewer", is_enabled=enabled))
        db.commit()
    finally:
        db.close()


@dataclass
class Party:
    """One tenant with one verified member."""
    tenant: str
    user: str
    headers: dict
    inference_ids: list[str] = field(default_factory=list)
    job_id: str = ""


def _party(label: str) -> Party:
    tenant = _uid(f"xt-{label}-tenant")
    user = f"{_uid(f'xt-{label}')}@example.com"
    _add_membership(tenant, user)
    return Party(tenant=tenant, user=user, headers=_bearer(user))


def _analyze(party: Party) -> str:
    response = client.post(f"{CV}/analyze", json={"image_data_b64": PNG}, headers=party.headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["tenant_id"] == party.tenant and body["evidence_class"] == EVIDENCE_MODEL_INFERENCE
    party.inference_ids.append(body["inference_id"])
    return body["inference_id"]


def _tenant_state(tenant: str) -> dict:
    """Everything stored for a tenant's CV records — to prove a request changed nothing."""
    db = SessionLocal()
    try:
        records = db.query(CVInferenceRecord).filter(CVInferenceRecord.tenant_id == tenant).all()
        rows = db.query(CVInferenceProvenance).filter(CVInferenceProvenance.tenant_id == tenant).all()
        return {
            "records": sorted(
                (r.inference_id, r.status, r.finding_count, r.review_annotation or "",
                 r.review_annotator_id or "", r.result_json) for r in records),
            "provenance": sorted((p.inference_id, p.state, p.attestation) for p in rows),
            "trusted": sorted(r.inference_id for r in records if verify_record(db, r).trusted),
        }
    finally:
        db.close()


def _total_records() -> int:
    db = SessionLocal()
    try:
        return db.query(CVInferenceRecord).count()
    finally:
        db.close()


class _Session:
    def __init__(self, outputs):
        self.outputs = outputs

    def run(self, *_a, **_k):
        return self.outputs


# ── fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def _environment(monkeypatch, tmp_path):
    """A server that can run and seal inference: provenance key, approved pins,
    and a provider object with canned outputs (no runtime, no weights)."""
    import app.cv.onnx_provider as onnx_mod

    monkeypatch.setenv(provenance.KEY_ENV, TEST_KEY)
    monkeypatch.delenv(provenance.KEY_ID_ENV, raising=False)
    monkeypatch.setenv("CV_ONNX_CLASSIFIER_SHA256", CLASSIFIER_DIGEST)
    monkeypatch.setenv("CV_ONNX_DETECTOR_SHA256", DETECTOR_DIGEST)
    monkeypatch.delenv("LUMENAI_MODEL_SHA256", raising=False)

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

    from app.limiter import limiter
    if limiter is not None:
        try:
            limiter.reset()
        except Exception:  # noqa: BLE001 - the limiter backend may not support reset
            pass
    yield
    CVRegistry.reset()


@dataclass
class World:
    a: Party
    b: Party
    outsider: dict          # a valid signed JWT for a user with no membership anywhere
    disabled_b: dict        # a valid signed JWT whose membership of tenant B is disabled


@pytest.fixture
def world() -> World:
    """Tenant A (1 sealed run) and tenant B (3 sealed runs and one async job)."""
    a, b = _party("a"), _party("b")
    _analyze(a)
    for _ in range(3):
        _analyze(b)

    submitted = client.post(f"{CV}/analyze-async", json={"image_data_b64": PNG}, headers=b.headers)
    assert submitted.status_code == 202, submitted.text
    b.job_id = submitted.json()["inference_id"]
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        polled = client.get(f"{CV}/inference/{b.job_id}/status", headers=b.headers).json()
        if polled["status"] != "processing":
            break
        time.sleep(0.05)
    assert polled["status"] == "complete", polled
    b.inference_ids.append(polled["result"]["inference_id"])

    outsider_user = f"{_uid('xt-outsider')}@example.com"
    disabled_user = f"{_uid('xt-disabled')}@example.com"
    _add_membership(b.tenant, disabled_user, enabled=False)
    return World(a=a, b=b, outsider=_bearer(outsider_user), disabled_b=_bearer(disabled_user))


# ── the CV route table ────────────────────────────────────────────────────────

def _cv_calls(inference_id: str, job_id: str, *, claim: str | None = None) -> dict:
    """One well-formed request per enterprise CV route.

    ``claim`` is a tenant id the CLIENT asserts wherever the route would accept
    one (body and query). Bodies are schema-valid so that a refusal is an
    authorization decision, not a validation error."""
    tenant_body = {"tenant_id": claim} if claim else {}
    tenant_query = {"tenant_id": claim} if claim else {}
    image = {"image_data_b64": PNG, **tenant_body}
    return {
        ("POST", "/analyze"): {"json": image},
        ("POST", "/analyze-and-rank"): {"json": image},
        ("POST", "/analyze-async"): {"json": image},
        ("POST", "/baseline-compare"): {"json": {
            "inspection_image_url": "https://images.example.invalid/a.png",
            "baseline_image_url": "https://images.example.invalid/b.png", **tenant_body}},
        ("POST", "/analyze-video"): {"json": {
            "video_url": "https://images.example.invalid/v.mp4", **tenant_body}},
        ("POST", "/inference/{inference_id}/annotate"): {
            "path": f"/inference/{inference_id}/annotate",
            "json": {"annotator_id": "attacker", "notes": "cross-tenant write",
                     "confirmed_regions": [], **tenant_body},
            "params": tenant_query},
        ("GET", "/inference/{inference_id}"): {
            "path": f"/inference/{inference_id}", "params": tenant_query},
        ("GET", "/inference/{inference_id}/status"): {
            "path": f"/inference/{job_id}/status", "params": tenant_query},
        ("GET", "/history"): {"params": tenant_query},
        ("GET", "/review-queue"): {"params": tenant_query},
        ("GET", "/kpi-summary"): {"params": tenant_query},
        ("GET", "/provider/metrics"): {"params": tenant_query},
        ("GET", "/provider/info"): {"params": tenant_query},
    }


CV_ROUTES = sorted(_cv_calls("x", "y"))
WRITE_ROUTES = [route for route in CV_ROUTES if route[0] == "POST"]


def _send(route: tuple[str, str], calls: dict, headers: dict):
    """Send the request for ``route`` out of a ``_cv_calls`` table."""
    method, template = route
    call = calls[route]
    return client.request(
        method, CV + call.get("path", template), headers=headers,
        json=call.get("json"), params=call.get("params") or None)


def test_the_route_table_covers_every_mounted_cv_route():
    mounted = sorted(
        (method, route.path.removeprefix(CV))
        for route in app.routes
        if isinstance(route, APIRoute) and route.path.startswith(CV + "/")
        for method in route.methods - {"HEAD", "OPTIONS"}
    )
    assert mounted == CV_ROUTES


# ══ 1. Unauthorized access — no verified tenant, no data, no side effect ══════

def _unsigned_token(user: str) -> str:
    def part(obj: dict) -> str:
        return base64.urlsafe_b64encode(json.dumps(obj).encode()).rstrip(b"=").decode()
    return f"{part({'alg': 'none', 'typ': 'JWT'})}.{part({'sub': user, 'exp': 4102444800})}."


def _tampered_token(user: str) -> str:
    header, payload, signature = _make_token(user).split(".")
    return f"{header}.{payload}.{signature[:-4]}{'AAAA' if not signature.endswith('AAAA') else 'BBBB'}"


def _unverified_identities(world: World) -> dict[str, dict]:
    b = world.b
    return {
        "anonymous": {},
        "anonymous naming tenant B": {"X-Tenant-Id": b.tenant},
        "not a token": {"Authorization": "Bearer not-a-jwt"},
        "unsigned token for B's user": {"Authorization": f"Bearer {_unsigned_token(b.user)}"},
        "tampered signature for B's user": {"Authorization": f"Bearer {_tampered_token(b.user)}"},
        "basic auth": {"Authorization": "Basic YWRtaW46YWRtaW4="},
        "user with no membership": world.outsider,
        "user with no membership naming tenant B": {**world.outsider, "X-Tenant-Id": b.tenant},
        "disabled member of B": world.disabled_b,
        "disabled member of B naming tenant B": {**world.disabled_b, "X-Tenant-Id": b.tenant},
    }


IDENTITY_LABELS = sorted(_unverified_identities(World(Party("t", "u", {}), Party("t", "u", {}), {}, {})))


class TestUnverifiedCallersGetNothing:
    @pytest.mark.parametrize("route", CV_ROUTES, ids=lambda r: f"{r[0]} {r[1]}")
    @pytest.mark.parametrize("identity", IDENTITY_LABELS)
    def test_refused_without_data_or_side_effect(self, world, route, identity):
        b = world.b
        before, total_before = _tenant_state(b.tenant), _total_records()
        headers = _unverified_identities(world)[identity]

        response = _send(route, _cv_calls(b.inference_ids[0], b.job_id), headers)

        assert response.status_code in REFUSED, (identity, route, response.status_code, response.text)
        for secret in (*b.inference_ids, b.tenant, b.user):
            assert secret not in response.text
        assert _tenant_state(b.tenant) == before
        assert _total_records() == total_before


# ══ 2. A verified member of tenant A cannot become tenant B ═══════════════════

def _tenant_spoofing_headers(world: World) -> dict[str, dict]:
    a, b = world.a, world.b
    return {
        "X-Tenant-Id: B": {**a.headers, "X-Tenant-Id": b.tenant},
        "x-tenant-id: B (lower case)": {**a.headers, "x-tenant-id": b.tenant},
        "both tenant headers: B": {**a.headers, "X-Tenant-Id": b.tenant, "X-LumenAI-Tenant-Id": b.tenant},
        "X-Tenant-Id: A but X-LumenAI-Tenant-Id: B": {
            **a.headers, "X-Tenant-Id": a.tenant, "X-LumenAI-Tenant-Id": b.tenant},
    }


SPOOF_LABELS = sorted(_tenant_spoofing_headers(World(Party("t", "u", {}), Party("t", "u", {}), {}, {})))


class TestTenantHeaderCannotBeForged:
    @pytest.mark.parametrize("route", CV_ROUTES, ids=lambda r: f"{r[0]} {r[1]}")
    @pytest.mark.parametrize("spoof", SPOOF_LABELS)
    def test_naming_tenant_b_in_a_header_is_refused(self, world, route, spoof):
        b = world.b
        before, total_before = _tenant_state(b.tenant), _total_records()

        response = _send(
            route, _cv_calls(b.inference_ids[0], b.job_id, claim=b.tenant),
            _tenant_spoofing_headers(world)[spoof])

        assert response.status_code == 403, (spoof, route, response.status_code, response.text)
        for secret in b.inference_ids:
            assert secret not in response.text
        assert _tenant_state(b.tenant) == before
        assert _total_records() == total_before

    @pytest.mark.parametrize("route", CV_ROUTES, ids=lambda r: f"{r[0]} {r[1]}")
    def test_the_secondary_tenant_header_alone_does_not_switch_tenant(self, world, route):
        """``X-LumenAI-Tenant-Id`` with no ``X-Tenant-Id``: the request must be
        served as tenant A or refused — never as tenant B."""
        a, b = world.a, world.b
        before = _tenant_state(b.tenant)

        response = _send(
            route, _cv_calls(b.inference_ids[0], b.job_id),
            {**a.headers, "X-LumenAI-Tenant-Id": b.tenant})

        for secret in b.inference_ids:
            assert secret not in response.text.replace(f"/inference/{b.inference_ids[0]}", "")
        assert _tenant_state(b.tenant) == before
        if response.status_code == 200 and isinstance(response.json(), dict):
            assert response.json().get("tenant_id", a.tenant) == a.tenant

    def test_a_tenant_header_is_honoured_only_with_membership(self, world):
        """Positive control: the header DOES select the tenant for a user who is a
        verified member of it — so the refusals above are authorization, not a
        header that is simply ignored."""
        a, b = world.a, world.b
        _add_membership(b.tenant, a.user)        # A's user now legitimately belongs to both

        as_b = client.get(f"{CV}/history", headers={**a.headers, "X-Tenant-Id": b.tenant})
        as_a = client.get(f"{CV}/history", headers={**a.headers, "X-Tenant-Id": a.tenant})

        assert {row["inference_id"] for row in as_b.json()} == set(b.inference_ids)
        assert {row["inference_id"] for row in as_a.json()} == set(a.inference_ids)


# ══ 3. Inference results — object-level access ════════════════════════════════

class TestInferenceResultsAreNotReadableAcrossTenants:
    def test_owner_can_read_and_the_other_tenant_cannot(self, world):
        a, b = world.a, world.b
        for inference_id in b.inference_ids:
            assert client.get(f"{CV}/inference/{inference_id}", headers=b.headers).status_code == 200
            denied = client.get(f"{CV}/inference/{inference_id}", headers=a.headers)
            assert denied.status_code == 404
            assert b.tenant not in denied.text

    @pytest.mark.parametrize("claim_in", ["query", "none"])
    def test_another_tenants_record_is_indistinguishable_from_a_missing_one(self, world, claim_in):
        """No existence oracle: a real id owned by B and an id that does not exist
        produce the same status and the same body for a member of A."""
        a, b = world.a, world.b
        params = {"tenant_id": b.tenant} if claim_in == "query" else None

        real = client.get(f"{CV}/inference/{b.inference_ids[0]}", headers=a.headers, params=params)
        missing = client.get(f"{CV}/inference/{_uid('inf')}", headers=a.headers, params=params)

        assert real.status_code == missing.status_code == 404
        assert real.json() == missing.json()

    def test_async_job_status_is_only_visible_to_its_tenant(self, world):
        a, b = world.a, world.b
        own = client.get(f"{CV}/inference/{b.job_id}/status", headers=b.headers).json()
        assert own["status"] == "complete" and own["result"]["tenant_id"] == b.tenant

        other = client.get(f"{CV}/inference/{b.job_id}/status", headers=a.headers)
        unknown_id = _uid("inf")
        unknown = client.get(f"{CV}/inference/{unknown_id}/status", headers=a.headers)

        assert other.json() == {"inference_id": b.job_id, "status": "not_found"}
        assert unknown.json() == {"inference_id": unknown_id, "status": "not_found"}
        assert "result" not in other.json() and b.tenant not in other.text

    def test_the_async_result_does_not_expose_the_owning_tenant_key(self, world):
        own = client.get(f"{CV}/inference/{world.b.job_id}/status", headers=world.b.headers).json()
        assert "tenant_id" not in own          # the job store's ownership field is internal


# ══ 4. Writes ═════════════════════════════════════════════════════════════════

class TestWritesStayInTheCallersTenant:
    def test_annotating_another_tenants_inference_is_refused_and_changes_nothing(self, world):
        a, b = world.a, world.b
        target = b.inference_ids[0]
        before = _tenant_state(b.tenant)

        for params in (None, {"tenant_id": b.tenant}):
            response = client.post(
                f"{CV}/inference/{target}/annotate", headers=a.headers, params=params,
                json={"annotator_id": "attacker", "notes": "cross-tenant write",
                      "confirmed_regions": [], "tenant_id": b.tenant})
            assert response.status_code == 404

        assert _tenant_state(b.tenant) == before
        assert target in _tenant_state(b.tenant)["trusted"]      # B's evidence is intact

    def test_the_owner_can_still_annotate(self, world):
        b = world.b
        response = client.post(
            f"{CV}/inference/{b.inference_ids[0]}/annotate", headers=b.headers,
            json={"annotator_id": "reviewer-b", "notes": "synthetic"})
        assert response.status_code == 200, response.text

    @pytest.mark.parametrize("route", WRITE_ROUTES, ids=lambda r: f"{r[0]} {r[1]}")
    def test_a_tenant_named_in_the_body_never_receives_the_write(self, world, route):
        """A's member names tenant B in the request body and query (no header).
        Whatever the route answers, nothing may be created or changed in B, and
        anything created must belong to A."""
        a, b = world.a, world.b
        before_b, before_a = _tenant_state(b.tenant), _tenant_state(a.tenant)

        response = _send(route, _cv_calls(b.inference_ids[0], b.job_id, claim=b.tenant), a.headers)

        assert response.status_code != 500
        assert _tenant_state(b.tenant) == before_b
        if response.status_code == 200 and "tenant_id" in response.json():
            assert response.json()["tenant_id"] == a.tenant
        created = {row[0] for row in _tenant_state(a.tenant)["records"]} - {
            row[0] for row in before_a["records"]}
        db = SessionLocal()
        try:
            owners = {r.tenant_id for r in db.query(CVInferenceRecord).filter(
                CVInferenceRecord.inference_id.in_(created or {"-"}))}
        finally:
            db.close()
        assert owners <= {a.tenant}

    def test_an_async_job_submitted_while_naming_b_belongs_to_the_submitter(self, world):
        a, b = world.a, world.b
        submitted = client.post(
            f"{CV}/analyze-async", headers=a.headers,
            json={"image_data_b64": PNG, "tenant_id": b.tenant})
        assert submitted.status_code == 202
        job = submitted.json()["inference_id"]

        assert client.get(f"{CV}/inference/{job}/status", headers=b.headers).json()["status"] == "not_found"
        assert client.get(f"{CV}/inference/{job}/status", headers=a.headers).json()["status"] != "not_found"


# ══ 5. Evidence retrieval ═════════════════════════════════════════════════════

class TestEvidenceRetrievalIsTenantScoped:
    @pytest.mark.parametrize("endpoint", ["/history", "/review-queue"])
    @pytest.mark.parametrize("claim", [False, True], ids=["plain", "naming tenant B in the query"])
    def test_lists_contain_only_the_callers_records(self, world, endpoint, claim):
        a, b = world.a, world.b
        params = {"tenant_id": b.tenant, "limit": 200} if claim else {"limit": 200}

        as_a = client.get(CV + endpoint, headers=a.headers, params=params)
        as_b = client.get(CV + endpoint, headers=b.headers, params={"limit": 200})

        assert as_a.status_code == as_b.status_code == 200
        ids_a = {row["inference_id"] for row in as_a.json()}
        ids_b = {row["inference_id"] for row in as_b.json()}
        assert ids_a <= set(a.inference_ids) and ids_b <= set(b.inference_ids)
        assert not ids_a & set(b.inference_ids)
        for secret in (*b.inference_ids, b.tenant):
            assert secret not in as_a.text

    def test_history_returns_each_tenant_exactly_its_own_runs(self, world):
        a, b = world.a, world.b
        history = lambda party: {  # noqa: E731 - local shorthand
            row["inference_id"] for row in client.get(f"{CV}/history", headers=party.headers).json()}
        assert history(a) == set(a.inference_ids)
        assert history(b) == set(b.inference_ids)

    def test_provenance_detail_of_another_tenant_is_not_retrievable(self, world):
        """The integrity statement (artifact digests, issue time) is evidence too."""
        a, b = world.a, world.b
        own = client.get(f"{CV}/inference/{b.inference_ids[0]}", headers=b.headers).json()
        assert own["model_integrity"]["verified"] is True

        other = client.get(f"{CV}/inference/{b.inference_ids[0]}", headers=a.headers)
        assert other.status_code == 404 and "model_integrity" not in other.text


# ══ 6. Operational aggregation on the CV routes ═══════════════════════════════

def _stable(payload: dict) -> dict:
    return {k: v for k, v in payload.items() if "generated" not in k and "timestamp" not in k}


class TestOperationalAggregationIsTenantScoped:
    def test_each_tenant_counts_only_its_own_verified_runs(self, world):
        a, b = world.a, world.b
        kpi_a = client.get(f"{CV}/kpi-summary", headers=a.headers).json()
        kpi_b = client.get(f"{CV}/kpi-summary", headers=b.headers).json()
        assert (kpi_a["genuine_analyses"], kpi_a["total_analyses"]) == (1, 1)
        assert (kpi_b["genuine_analyses"], kpi_b["total_analyses"]) == (4, 4)
        assert kpi_a["evidence_basis"] == kpi_b["evidence_basis"] == "model_inference_only"

    @pytest.mark.parametrize("endpoint", ["/kpi-summary", "/provider/metrics"])
    def test_naming_tenant_b_in_the_query_still_returns_the_callers_aggregate(self, world, endpoint):
        a, b = world.a, world.b
        own = client.get(CV + endpoint, headers=a.headers).json()
        claimed = client.get(CV + endpoint, headers=a.headers, params={"tenant_id": b.tenant})
        assert claimed.status_code == 200
        assert _stable(claimed.json()) == _stable(own)
        assert b.tenant not in claimed.text

    @pytest.mark.parametrize("endpoint", ["/kpi-summary", "/provider/metrics", "/history", "/review-queue"])
    def test_activity_in_tenant_b_does_not_move_tenant_a(self, world, endpoint):
        """Differential: A's view is byte-for-byte the same before and after B
        runs more inference."""
        a, b = world.a, world.b
        before = client.get(CV + endpoint, headers=a.headers).json()

        for _ in range(2):
            _analyze(b)

        after = client.get(CV + endpoint, headers=a.headers).json()
        assert (_stable(after) if isinstance(after, dict) else after) == (
            _stable(before) if isinstance(before, dict) else before)

    def test_provider_metrics_count_only_the_callers_records(self, world):
        a, b = world.a, world.b
        metrics_a = client.get(f"{CV}/provider/metrics", headers=a.headers).json()
        metrics_b = client.get(f"{CV}/provider/metrics", headers=b.headers).json()
        assert sum(metrics_a["evidence_breakdown"].values()) == 1
        assert sum(metrics_b["evidence_breakdown"].values()) == 4


# ══ 7. Operational aggregation on the downstream analytics routes ═════════════
#
# The six analytics services read CV inference records. Their API routes are
# outside the CV router and resolve the tenant in two different ways.

# Tenant comes from the verified auth context.
CONTEXT_TENANT_ROUTES = [
    ("GET", "/api/digital-twin/state"),
    ("GET", "/api/digital-twin/dashboard"),
    ("GET", "/api/copilot/dashboard"),
    ("GET", "/api/copilot/sessions"),
]

# Routes that accept a ``tenant_id`` from the client. Before P472-03 they served
# whichever tenant it named; now it is only a claim that must match the caller's.
CLIENT_TENANT_ROUTES = [
    ("GET", "/api/regulatory/readiness"),
    ("GET", "/api/regulatory/readiness/findings"),
    ("GET", "/api/regulatory/dashboard"),
    ("GET", "/api/predictions/failures"),
    ("GET", "/api/predictions/contamination"),
    ("GET", "/api/predictions/dashboard"),
    ("GET", "/api/enterprise/benchmarks/hospitals"),
    ("GET", "/api/enterprise/benchmarks/rollup"),
    ("GET", "/api/enterprise/benchmarks/kpi-summary"),
    ("GET", "/api/enterprise/benchmarks/executive-dashboard"),
    ("GET", "/api/vendor-intelligence/vendors"),
]
ALL_DOWNSTREAM = CONTEXT_TENANT_ROUTES + CLIENT_TENANT_ROUTES


class TestDownstreamAggregateRoutes:
    @pytest.mark.parametrize("route", ALL_DOWNSTREAM, ids=lambda r: r[1])
    @pytest.mark.parametrize("identity", ["anonymous", "not a token", "user with no membership"])
    def test_unverified_callers_are_refused(self, world, route, identity):
        headers = _unverified_identities(world)[identity]
        response = client.request(
            route[0], route[1], headers=headers, params={"tenant_id": world.b.tenant})
        assert response.status_code in REFUSED, (route, identity, response.status_code)

    @pytest.mark.parametrize("route", ALL_DOWNSTREAM, ids=lambda r: r[1])
    def test_a_forged_tenant_header_is_refused(self, world, route):
        a, b = world.a, world.b
        response = client.request(
            route[0], route[1], headers={**a.headers, "X-Tenant-Id": b.tenant},
            params={"tenant_id": b.tenant})
        assert response.status_code == 403, (route, response.status_code)

    @pytest.mark.parametrize("route", ALL_DOWNSTREAM, ids=lambda r: r[1])
    def test_the_owner_can_read_its_own_aggregate(self, world, route):
        """Positive control for the refusals in this class."""
        b = world.b
        response = client.request(route[0], route[1], headers=b.headers, params={"tenant_id": b.tenant})
        assert response.status_code == 200, (route, response.status_code, response.text[:300])

    @pytest.mark.parametrize("route", CONTEXT_TENANT_ROUTES, ids=lambda r: r[1])
    def test_context_tenant_routes_ignore_a_tenant_named_in_the_query(self, world, route):
        a, b = world.a, world.b
        own = client.request(route[0], route[1], headers=a.headers)
        claimed = client.request(route[0], route[1], headers=a.headers, params={"tenant_id": b.tenant})
        assert own.status_code == claimed.status_code == 200
        assert b.tenant not in claimed.text
        for secret in b.inference_ids:
            assert secret not in claimed.text

    @pytest.mark.parametrize("route", CLIENT_TENANT_ROUTES, ids=[route[1] for route in CLIENT_TENANT_ROUTES])
    def test_a_member_of_a_cannot_request_tenant_b_by_query(self, world, route):
        """A verified member of tenant A, sending no tenant header, asks for
        ``tenant_id=<tenant B>``. Required: refused. (P472-03, fixed.)"""
        a, b = world.a, world.b
        response = client.request(route[0], route[1], headers=a.headers, params={"tenant_id": b.tenant})
        assert response.status_code in (*REFUSED, 404), (
            f"{route[1]} served tenant B's aggregate to a member of tenant A "
            f"(HTTP {response.status_code}): {response.text[:200]}")


# ── cross-tenant WRITES through the downstream routes ─────────────────────────

def _downstream_writes(tenant: str) -> dict[str, dict]:
    return {
        "/api/predictions/outcomes": {
            "tenant_id": tenant, "instrument_name": "synthetic-instrument",
            "prediction_date": "2026-11-01T00:00:00", "predicted_risk_category": "low",
            "actual_outcome": "no_event", "recorded_by": "cross-tenant-test"},
        "/api/regulatory/fda-submissions": {
            "tenant_id": tenant, "device_name": "synthetic-device",
            "manufacturer": "synthetic-manufacturer", "notes": "cross-tenant-test"},
    }


DOWNSTREAM_WRITE_PATHS = sorted(_downstream_writes("t"))


def _downstream_rows(tenant: str) -> dict[str, int]:
    from app.models.predictions import PredictionOutcome
    from app.models.regulatory import FDASubmissionTracker

    db = SessionLocal()
    try:
        return {
            "/api/predictions/outcomes": db.query(PredictionOutcome).filter(
                PredictionOutcome.tenant_id == tenant).count(),
            "/api/regulatory/fda-submissions": db.query(FDASubmissionTracker).filter(
                FDASubmissionTracker.tenant_id == tenant).count(),
        }
    finally:
        db.close()


class TestDownstreamWritesAcrossTenants:
    @pytest.mark.parametrize("path", DOWNSTREAM_WRITE_PATHS)
    @pytest.mark.parametrize("identity", ["anonymous", "not a token", "user with no membership"])
    def test_unverified_callers_cannot_write(self, world, path, identity):
        b = world.b
        before = _downstream_rows(b.tenant)
        response = client.post(
            path, json=_downstream_writes(b.tenant)[path], headers=_unverified_identities(world)[identity])
        assert response.status_code in REFUSED
        assert _downstream_rows(b.tenant) == before

    @pytest.mark.parametrize("path", DOWNSTREAM_WRITE_PATHS)
    def test_a_forged_tenant_header_cannot_write(self, world, path):
        a, b = world.a, world.b
        before = _downstream_rows(b.tenant)
        response = client.post(
            path, json=_downstream_writes(b.tenant)[path], headers={**a.headers, "X-Tenant-Id": b.tenant})
        assert response.status_code == 403
        assert _downstream_rows(b.tenant) == before

    @pytest.mark.parametrize("path", DOWNSTREAM_WRITE_PATHS)
    def test_the_owner_can_write_to_its_own_tenant(self, world, path):
        b = world.b
        before = _downstream_rows(b.tenant)[path]
        response = client.post(path, json=_downstream_writes(b.tenant)[path], headers=b.headers)
        assert response.status_code == 200, response.text
        assert _downstream_rows(b.tenant)[path] == before + 1

    @pytest.mark.parametrize("path", DOWNSTREAM_WRITE_PATHS)
    def test_a_member_of_a_cannot_write_into_tenant_b_by_naming_it_in_the_body(self, world, path):
        """A verified member of tenant A, sending no tenant header, posts a record
        whose body says ``tenant_id: <tenant B>``. Required: refused, nothing stored.
        (P472-03, fixed.)"""
        a, b = world.a, world.b
        before = _downstream_rows(b.tenant)[path]

        response = client.post(path, json=_downstream_writes(b.tenant)[path], headers=a.headers)

        stored = _downstream_rows(b.tenant)[path] - before
        assert response.status_code in REFUSED and stored == 0, (
            f"{path}: HTTP {response.status_code}; {stored} row(s) written into tenant B "
            "by a member of tenant A")
