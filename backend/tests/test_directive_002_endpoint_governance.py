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
    # --- REVIEW_REQUIRED (real gaps, tracked for increment 3) ---
    ("POST", "/api/enterprise/baseline-aware-score"),
    ("POST", "/api/enterprise/baselines/{baseline_id}/review"),
    ("POST", "/api/enterprise/instruments/{instrument_id}/baseline"),
    ("POST", "/api/enterprise/intake/{finding_id}/baseline-comparison"),
    ("POST", "/api/enterprise/vendor-baseline-subscription/baselines"),
    ("POST", "/api/enterprise/vendor-baseline-subscription/baselines/upload-image"),
    ("POST", "/api/enterprise/vendor-baseline-subscription/baselines/{baseline_id}/approve"),
    ("POST", "/api/enterprise/vendor-baseline-subscription/match"),
    ("POST", "/api/enterprise/vendor-governance/events"),
    ("POST", "/api/enterprise/vendor-governance/events/{event_id}/create-capa"),
    ("POST", "/api/enterprise/vendor-governance/events/{event_id}/link-capa"),
}


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
