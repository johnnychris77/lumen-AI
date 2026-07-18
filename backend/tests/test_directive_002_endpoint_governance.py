"""Pilot Zero Directive 002, increment 2 — endpoint governance regression tests.

These tests enforce the endpoint-security invariants established by the
generated inventory (`scripts/generate_endpoint_inventory.py`). They are the
CI-enforceable control that:

  1. every mounted endpoint is classifiable (no ``UNKNOWN``);
  2. no NEW unauthenticated write endpoint can be introduced — the set of
     unauthenticated writes must stay within the reviewed allowlist in
     ``docs/pilot-zero/directive-002/ENDPOINT_SECURITY_REVIEW.md``;
  3. the liveness/readiness probes behave as documented.

If you add an authenticated write, this test keeps passing. If you add an
*unauthenticated* write, this test fails until the endpoint is either secured
or explicitly reviewed and added to ``REVIEWED_UNAUTHENTICATED_WRITES`` with a
disposition recorded in the security-review doc.
"""
from __future__ import annotations

import os
import sys

import pytest
from fastapi.testclient import TestClient

# Make the committed generator importable (backend/ root is the test rootdir).
_BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BACKEND_ROOT not in sys.path:
    sys.path.insert(0, _BACKEND_ROOT)

from scripts.generate_endpoint_inventory import (  # noqa: E402
    collect,
    unauthenticated_writes,
)

from app.main import app  # noqa: E402

client = TestClient(app)

# Reviewed, dispositioned allowlist of unauthenticated write endpoints (method,
# path). Every entry is justified in ENDPOINT_SECURITY_REVIEW.md as either
# PUBLIC_BY_DESIGN (login / signed webhooks / self-service registration /
# token refresh / stateless compute) or REVIEW_REQUIRED (a real gap tracked
# for increment 3). New unauthenticated writes are NOT permitted here without
# a matching review entry.
REVIEWED_UNAUTHENTICATED_WRITES = {
    # --- PUBLIC_BY_DESIGN ---
    ("POST", "/api/admin/bootstrap"),
    ("POST", "/api/auth/login"),
    ("POST", "/api/baseline-ranking/audit-evidence"),
    ("POST", "/api/billing/upgrade"),
    ("POST", "/api/billing/webhook"),
    ("POST", "/api/capture/ingest"),
    ("POST", "/api/integrations/webhook/{system_name}"),
    ("POST", "/api/manufacturers/register"),
    ("POST", "/api/mobile/auth/token-refresh"),
    # The 11 REVIEW_REQUIRED enterprise/vendor-governance writes were SECURED in
    # increment 3 (require_enterprise_auth / already-guarded via
    # require_hospital_or_enterprise_admin) and removed from this allowlist. See
    # SECURED_WRITE_ENDPOINTS below and ENDPOINT_SECURITY_REVIEW.md.
}

# Endpoints secured in increment 3: they must now reject an unauthenticated
# request (401/403). These are asserted live in TestSecuredWritesRejectAnon.
# Only endpoints whose body passes FastAPI validation with the payload below
# are listed here — for handlers with a required pydantic body, an empty anon
# request returns 422 (validation) before the in-body auth guard runs, so their
# secured state is asserted by the allowlist test (they are no longer in the
# unauthenticated-writes set) rather than a direct 401 assertion.
SECURED_WRITE_ENDPOINTS = [
    ("post", "/api/enterprise/baseline-aware-score", {}),
    ("post", "/api/enterprise/intake/1/baseline-comparison", {}),
    ("post", "/api/enterprise/vendor-baseline-subscription/baselines", {}),
    ("post", "/api/enterprise/vendor-baseline-subscription/match", {}),
    ("post", "/api/enterprise/vendor-governance/events", {
        "vendor_name": "x", "event_type": "quality", "event_summary": "s",
        "risk_level": "low", "site": "s", "device_or_tray": "d", "owner": "o",
    }),
    ("post", "/api/enterprise/vendor-governance/events/evt-1/create-capa", None),
    ("post", "/api/enterprise/vendor-governance/events/evt-1/link-capa", {"capa_id": "c-1"}),
]


@pytest.fixture(scope="module")
def rows():
    return collect()


class TestEndpointClassification:
    def test_no_endpoint_is_unknown(self, rows):
        unknown = [r for r in rows if r["classification"] == "UNKNOWN"]
        assert unknown == [], f"{len(unknown)} endpoints are UNKNOWN: {unknown[:5]}"

    def test_inventory_is_non_trivial(self, rows):
        # Guard against the generator silently collecting nothing.
        assert len(rows) > 1000
        assert any(r["write"] for r in rows)


class TestNoNewUnauthenticatedWrites:
    def test_unauthenticated_writes_stay_within_reviewed_allowlist(self, rows):
        current = {(r["method"], r["path"]) for r in unauthenticated_writes(rows)}
        new_unreviewed = current - REVIEWED_UNAUTHENTICATED_WRITES
        assert new_unreviewed == set(), (
            "New unauthenticated write endpoint(s) introduced without security "
            f"review: {sorted(new_unreviewed)}. Secure the endpoint, or add it to "
            "REVIEWED_UNAUTHENTICATED_WRITES with a disposition in "
            "ENDPOINT_SECURITY_REVIEW.md."
        )

    def test_allowlist_has_no_stale_entries(self, rows):
        # Keep the allowlist honest: once an endpoint is secured it must be
        # removed from the allowlist so the set shrinks over time.
        current = {(r["method"], r["path"]) for r in unauthenticated_writes(rows)}
        stale = REVIEWED_UNAUTHENTICATED_WRITES - current
        assert stale == set(), f"Allowlist entries no longer unauthenticated (remove them): {sorted(stale)}"


class TestSecuredWritesRejectAnon:
    """Increment 3 — the 11 previously-unauthenticated enterprise/vendor writes
    now reject an anonymous request (no Authorization header) with 401/403."""

    @pytest.mark.parametrize("method,path,body", SECURED_WRITE_ENDPOINTS)
    def test_secured_write_requires_auth(self, method, path, body):
        fn = getattr(client, method)
        resp = fn(path, json=body) if body is not None else fn(path)
        assert resp.status_code in (401, 403), (
            f"{method.upper()} {path} must require auth, got {resp.status_code}: {resp.text[:200]}"
        )


class TestHealthProbes:
    def test_liveness_ok(self):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_readiness_reports_dependency_checks(self):
        resp = client.get("/ready")
        assert resp.status_code in (200, 503)
        body = resp.json()
        # Increment 2 adds a per-dependency `checks` block; database is the
        # hard readiness gate.
        assert "checks" in body
        assert "database" in body["checks"]
