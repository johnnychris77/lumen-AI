"""P24: Global Healthcare Intelligence Ecosystem & Standards Leadership — test suite."""
from __future__ import annotations

import time

from fastapi.testclient import TestClient

from app.main import app

HEADERS = {"Authorization": "Bearer dev-token"}
NO_AUTH = {}
TS = str(int(time.time() * 1000))

client = TestClient(app, raise_server_exceptions=True)

_DISCLAIMER_MIN_LEN = 20

_CAUSATION_PHRASES = ["causes", "caused by", "proves", "confirms causation", "establishes causation"]


def _has_causation(text: str) -> bool:
    t = text.lower()
    return any(p in t for p in _CAUSATION_PHRASES)


def _flatten(obj) -> str:
    if isinstance(obj, dict):
        return " ".join(_flatten(v) for v in obj.values())
    if isinstance(obj, list):
        return " ".join(_flatten(v) for v in obj)
    return str(obj) if obj is not None else ""


# ---------------------------------------------------------------------------
# Phase 1: Quality Standards
# ---------------------------------------------------------------------------


class TestQualityStandards:
    def test_returns_200(self):
        r = client.get("/api/standards/quality-standards", headers=HEADERS)
        assert r.status_code == 200

    def test_requires_auth(self):
        r = client.get("/api/standards/quality-standards", headers=NO_AUTH)
        assert r.status_code in (401, 403)

    def test_returns_list(self):
        r = client.get("/api/standards/quality-standards", headers=HEADERS)
        assert r.status_code == 200
        assert isinstance(r.json().get("standards"), list)

    def test_has_published_standards(self):
        r = client.get("/api/standards/quality-standards", headers=HEADERS)
        assert r.status_code == 200
        standards = r.json()["standards"]
        assert len(standards) > 0

    def test_has_disclaimer(self):
        r = client.get("/api/standards/quality-standards", headers=HEADERS)
        body = r.json()
        assert "disclaimer" in body
        assert len(body["disclaimer"]) >= _DISCLAIMER_MIN_LEN

    def test_human_review_required(self):
        r = client.get("/api/standards/quality-standards", headers=HEADERS)
        assert r.json().get("human_review_required") is True

    def test_filter_by_standard_type(self):
        r = client.get(
            "/api/standards/quality-standards?standard_type=contamination_classification",
            headers=HEADERS,
        )
        assert r.status_code == 200

    def test_no_causation_language(self):
        r = client.get("/api/standards/quality-standards", headers=HEADERS)
        text = _flatten(r.json().get("standards", []))
        assert not _has_causation(text)

    def test_standard_has_version_and_title(self):
        r = client.get("/api/standards/quality-standards", headers=HEADERS)
        for s in r.json().get("standards", []):
            assert "version" in s
            assert "title" in s
            assert s["title"]

    def test_standard_types_covered(self):
        r = client.get("/api/standards/quality-standards", headers=HEADERS)
        types = {s.get("standard_type") for s in r.json().get("standards", [])}
        expected = {
            "contamination_classification",
            "instrument_defect",
            "baseline_variance",
            "inspection_scoring",
        }
        assert expected <= types


# ---------------------------------------------------------------------------
# Phase 2: Baseline Governance
# ---------------------------------------------------------------------------


class TestBaselineGovernance:
    _PAYLOAD = {
        "governance_type": "version_change",
        "instrument_category": "flexible_scopes",
        "baseline_version_from": "1.0",
        "baseline_version_to": "1.1",
        "provenance_source": "network_contributed",
        "change_rationale": "Updated contamination threshold based on Q1 network data.",
        "contributing_facilities": 8,
    }

    def test_list_returns_200(self):
        r = client.get("/api/standards/baseline-governance", headers=HEADERS)
        assert r.status_code == 200

    def test_list_requires_auth(self):
        r = client.get("/api/standards/baseline-governance", headers=NO_AUTH)
        assert r.status_code in (401, 403)

    def test_list_has_disclaimer(self):
        r = client.get("/api/standards/baseline-governance", headers=HEADERS)
        assert "disclaimer" in r.json()

    def test_submit_returns_200(self):
        r = client.post("/api/standards/baseline-governance", json=self._PAYLOAD, headers=HEADERS)
        assert r.status_code == 200

    def test_submit_returns_record_id(self):
        r = client.post("/api/standards/baseline-governance", json=self._PAYLOAD, headers=HEADERS)
        assert r.status_code == 200
        assert "record_id" in r.json()

    def test_submit_starts_pending(self):
        r = client.post("/api/standards/baseline-governance", json=self._PAYLOAD, headers=HEADERS)
        assert r.json()["approval_status"] == "pending"

    def test_submit_invalid_governance_type(self):
        bad = {**self._PAYLOAD, "governance_type": "random_action"}
        r = client.post("/api/standards/baseline-governance", json=bad, headers=HEADERS)
        assert r.status_code == 422

    def test_submit_invalid_provenance(self):
        bad = {**self._PAYLOAD, "provenance_source": "magic_source"}
        r = client.post("/api/standards/baseline-governance", json=bad, headers=HEADERS)
        assert r.status_code == 422

    def test_submit_requires_auth(self):
        r = client.post("/api/standards/baseline-governance", json=self._PAYLOAD, headers=NO_AUTH)
        assert r.status_code in (401, 403)

    def test_approve_record(self):
        r = client.post("/api/standards/baseline-governance", json=self._PAYLOAD, headers=HEADERS)
        record_id = r.json()["record_id"]
        ra = client.post(f"/api/standards/baseline-governance/{record_id}/approve", headers=HEADERS)
        assert ra.status_code == 200
        assert ra.json()["approval_status"] == "approved"

    def test_approve_double_is_conflict(self):
        r = client.post("/api/standards/baseline-governance", json=self._PAYLOAD, headers=HEADERS)
        record_id = r.json()["record_id"]
        client.post(f"/api/standards/baseline-governance/{record_id}/approve", headers=HEADERS)
        r2 = client.post(f"/api/standards/baseline-governance/{record_id}/approve", headers=HEADERS)
        assert r2.status_code == 409

    def test_approve_unknown_is_404(self):
        r = client.post("/api/standards/baseline-governance/999999/approve", headers=HEADERS)
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# Phase 3: Benchmark Program
# ---------------------------------------------------------------------------


class TestBenchmarks:
    def test_returns_200(self):
        r = client.get("/api/standards/benchmarks", headers=HEADERS)
        assert r.status_code == 200

    def test_requires_auth(self):
        r = client.get("/api/standards/benchmarks", headers=NO_AUTH)
        assert r.status_code in (401, 403)

    def test_returns_list(self):
        r = client.get("/api/standards/benchmarks", headers=HEADERS)
        assert isinstance(r.json().get("reports"), list)

    def test_has_reports(self):
        r = client.get("/api/standards/benchmarks", headers=HEADERS)
        assert len(r.json()["reports"]) > 0

    def test_has_disclaimer(self):
        r = client.get("/api/standards/benchmarks", headers=HEADERS)
        assert "disclaimer" in r.json()
        for rpt in r.json()["reports"]:
            assert "disclaimer" in rpt

    def test_human_review_required(self):
        r = client.get("/api/standards/benchmarks", headers=HEADERS)
        assert r.json().get("human_review_required") is True

    def test_filter_by_type(self):
        r = client.get("/api/standards/benchmarks?report_type=annual", headers=HEADERS)
        assert r.status_code == 200

    def test_report_types_present(self):
        r = client.get("/api/standards/benchmarks", headers=HEADERS)
        types = {rpt.get("report_type") for rpt in r.json()["reports"]}
        expected = {"annual", "contamination", "reliability", "executive_scorecard"}
        assert expected <= types

    def test_no_causation_language(self):
        r = client.get("/api/standards/benchmarks", headers=HEADERS)
        text = _flatten(r.json().get("reports", []))
        assert not _has_causation(text)

    def test_benchmark_has_network_metrics(self):
        r = client.get("/api/standards/benchmarks", headers=HEADERS)
        for rpt in r.json()["reports"]:
            assert "facility_count" in rpt
            assert rpt["facility_count"] > 0


# ---------------------------------------------------------------------------
# Phase 4: International Expansion
# ---------------------------------------------------------------------------


class TestRegionalDeployments:
    def test_returns_200(self):
        r = client.get("/api/standards/regional-deployments", headers=HEADERS)
        assert r.status_code == 200

    def test_requires_auth(self):
        r = client.get("/api/standards/regional-deployments", headers=NO_AUTH)
        assert r.status_code in (401, 403)

    def test_returns_list(self):
        r = client.get("/api/standards/regional-deployments", headers=HEADERS)
        assert isinstance(r.json().get("deployments"), list)

    def test_covers_major_regions(self):
        r = client.get("/api/standards/regional-deployments", headers=HEADERS)
        regions = {d.get("region") for d in r.json()["deployments"]}
        expected = {"north_america", "europe", "apac", "australia"}
        assert expected <= regions

    def test_has_privacy_framework(self):
        r = client.get("/api/standards/regional-deployments", headers=HEADERS)
        for d in r.json()["deployments"]:
            assert "privacy_framework" in d
            assert d["privacy_framework"]

    def test_filter_by_region(self):
        r = client.get("/api/standards/regional-deployments?region=europe", headers=HEADERS)
        assert r.status_code == 200

    def test_has_disclaimer(self):
        r = client.get("/api/standards/regional-deployments", headers=HEADERS)
        assert "disclaimer" in r.json()

    def test_human_review_required(self):
        r = client.get("/api/standards/regional-deployments", headers=HEADERS)
        assert r.json().get("human_review_required") is True


# ---------------------------------------------------------------------------
# Phase 5: Intelligence APIs
# ---------------------------------------------------------------------------


class TestAPIPartners:
    _APPLY_PAYLOAD = {
        "partner_name": f"TestPartner-{TS}",
        "api_tier": "research",
        "requested_scopes": ["signals.read", "benchmarks.read"],
    }

    def test_list_returns_200(self):
        r = client.get("/api/standards/api-partners", headers=HEADERS)
        assert r.status_code == 200

    def test_list_requires_auth(self):
        r = client.get("/api/standards/api-partners", headers=NO_AUTH)
        assert r.status_code in (401, 403)

    def test_apply_returns_200(self):
        r = client.post("/api/standards/api-partners", json=self._APPLY_PAYLOAD, headers=HEADERS)
        assert r.status_code == 200

    def test_apply_returns_application_id(self):
        r = client.post("/api/standards/api-partners", json=self._APPLY_PAYLOAD, headers=HEADERS)
        assert "application_id" in r.json()

    def test_apply_starts_pending(self):
        r = client.post("/api/standards/api-partners", json=self._APPLY_PAYLOAD, headers=HEADERS)
        assert r.json()["application_status"] == "pending"

    def test_apply_invalid_tier(self):
        bad = {**self._APPLY_PAYLOAD, "api_tier": "vip"}
        r = client.post("/api/standards/api-partners", json=bad, headers=HEADERS)
        assert r.status_code == 422

    def test_apply_requires_auth(self):
        r = client.post("/api/standards/api-partners", json=self._APPLY_PAYLOAD, headers=NO_AUTH)
        assert r.status_code in (401, 403)

    def test_approve_application(self):
        r = client.post("/api/standards/api-partners", json=self._APPLY_PAYLOAD, headers=HEADERS)
        app_id = r.json()["application_id"]
        ra = client.post(f"/api/standards/api-partners/{app_id}/approve", headers=HEADERS)
        assert ra.status_code == 200
        assert ra.json()["application_status"] == "approved"

    def test_approve_returns_scopes(self):
        r = client.post("/api/standards/api-partners", json=self._APPLY_PAYLOAD, headers=HEADERS)
        app_id = r.json()["application_id"]
        ra = client.post(f"/api/standards/api-partners/{app_id}/approve", headers=HEADERS)
        assert ra.status_code == 200
        assert isinstance(ra.json().get("approved_scopes"), list)

    def test_approve_unknown_is_404(self):
        r = client.post("/api/standards/api-partners/999999/approve", headers=HEADERS)
        assert r.status_code == 404

    def test_approve_double_is_conflict(self):
        r = client.post("/api/standards/api-partners", json=self._APPLY_PAYLOAD, headers=HEADERS)
        app_id = r.json()["application_id"]
        client.post(f"/api/standards/api-partners/{app_id}/approve", headers=HEADERS)
        r2 = client.post(f"/api/standards/api-partners/{app_id}/approve", headers=HEADERS)
        assert r2.status_code == 409


# ---------------------------------------------------------------------------
# Phase 6: Advisory Consortium
# ---------------------------------------------------------------------------


class TestConsortium:
    _ENROLL = {
        "organization_type": "hospital",
        "region": "north_america",
        "membership_tier": "observer",
    }

    def test_list_returns_200(self):
        r = client.get("/api/standards/consortium", headers=HEADERS)
        assert r.status_code == 200

    def test_list_requires_auth(self):
        r = client.get("/api/standards/consortium", headers=NO_AUTH)
        assert r.status_code in (401, 403)

    def test_list_has_members(self):
        r = client.get("/api/standards/consortium", headers=HEADERS)
        assert len(r.json().get("members", [])) > 0

    def test_list_filter_by_tier(self):
        r = client.get("/api/standards/consortium?tier=steering", headers=HEADERS)
        assert r.status_code == 200

    def test_list_has_disclaimer(self):
        r = client.get("/api/standards/consortium", headers=HEADERS)
        assert "disclaimer" in r.json()

    def test_enroll_or_conflict(self):
        r = client.post("/api/standards/consortium/enroll", json=self._ENROLL, headers=HEADERS)
        # 200 first time, 409 if already enrolled
        assert r.status_code in (200, 409)

    def test_enroll_starts_observer_tier(self):
        r = client.post("/api/standards/consortium/enroll", json=self._ENROLL, headers=HEADERS)
        if r.status_code == 200:
            assert r.json()["membership_tier"] == "observer"
            assert r.json()["membership_status"] == "pending"

    def test_enroll_invalid_org_type(self):
        bad = {**self._ENROLL, "organization_type": "alien"}
        r = client.post("/api/standards/consortium/enroll", json=bad, headers=HEADERS)
        assert r.status_code in (409, 422)  # 409 if already enrolled; 422 if validated first

    def test_enroll_requires_auth(self):
        r = client.post("/api/standards/consortium/enroll", json=self._ENROLL, headers=NO_AUTH)
        assert r.status_code in (401, 403)


class TestPublications:
    def test_list_returns_200(self):
        r = client.get("/api/standards/publications", headers=HEADERS)
        assert r.status_code == 200

    def test_list_requires_auth(self):
        r = client.get("/api/standards/publications", headers=NO_AUTH)
        assert r.status_code in (401, 403)

    def test_returns_list(self):
        r = client.get("/api/standards/publications", headers=HEADERS)
        assert isinstance(r.json().get("publications"), list)

    def test_has_publications(self):
        r = client.get("/api/standards/publications", headers=HEADERS)
        assert len(r.json()["publications"]) > 0

    def test_has_disclaimer(self):
        r = client.get("/api/standards/publications", headers=HEADERS)
        for pub in r.json()["publications"]:
            assert "disclaimer" in pub

    def test_filter_by_type(self):
        r = client.get("/api/standards/publications?publication_type=standard", headers=HEADERS)
        assert r.status_code == 200

    def test_review_publication(self):
        r = client.get("/api/standards/publications", headers=HEADERS)
        pubs = r.json()["publications"]
        # Find a non-published pub (consortium_review or draft)
        candidate = next(
            (p for p in pubs if p.get("status") not in ("published",)),
            None,
        )
        if candidate is None:
            return  # all already published — skip
        ra = client.post(
            "/api/standards/publications/review",
            json={"publication_id": candidate["id"], "decision": "approve"},
            headers=HEADERS,
        )
        assert ra.status_code == 200
        assert ra.json()["outcome"] == "published"

    def test_review_invalid_decision(self):
        r = client.get("/api/standards/publications", headers=HEADERS)
        pubs = r.json()["publications"]
        if not pubs:
            return
        ra = client.post(
            "/api/standards/publications/review",
            json={"publication_id": pubs[0]["id"], "decision": "maybe"},
            headers=HEADERS,
        )
        assert ra.status_code == 422

    def test_review_unknown_is_404(self):
        r = client.post(
            "/api/standards/publications/review",
            json={"publication_id": 999999, "decision": "approve"},
            headers=HEADERS,
        )
        assert r.status_code == 404

    def test_review_requires_auth(self):
        r = client.post(
            "/api/standards/publications/review",
            json={"publication_id": 1, "decision": "approve"},
            headers=NO_AUTH,
        )
        assert r.status_code in (401, 403)


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------


class TestDashboard:
    _KPI_KEYS = [
        "published_standards",
        "active_regions",
        "total_network_participants",
        "consortium_members",
        "published_papers",
    ]

    def test_returns_200(self):
        r = client.get("/api/standards/dashboard", headers=HEADERS)
        assert r.status_code == 200

    def test_has_all_kpis(self):
        r = client.get("/api/standards/dashboard", headers=HEADERS)
        body = r.json()
        for key in self._KPI_KEYS:
            assert key in body, f"Missing KPI: {key}"

    def test_has_disclaimer(self):
        r = client.get("/api/standards/dashboard", headers=HEADERS)
        assert "disclaimer" in r.json()

    def test_human_review_required(self):
        r = client.get("/api/standards/dashboard", headers=HEADERS)
        assert r.json().get("human_review_required") is True

    def test_requires_auth(self):
        r = client.get("/api/standards/dashboard", headers=NO_AUTH)
        assert r.status_code in (401, 403)


# ---------------------------------------------------------------------------
# Public ecosystem overview
# ---------------------------------------------------------------------------


class TestEcosystemOverview:
    def test_returns_200_no_auth(self):
        r = client.get("/api/standards/ecosystem-overview")
        assert r.status_code == 200

    def test_has_participant_count(self):
        r = client.get("/api/standards/ecosystem-overview")
        body = r.json()
        assert "total_network_participants" in body
        assert isinstance(body["total_network_participants"], int)

    def test_has_active_regions(self):
        r = client.get("/api/standards/ecosystem-overview")
        body = r.json()
        assert "active_regions" in body
        assert isinstance(body["active_regions"], int)

    def test_has_disclaimer(self):
        r = client.get("/api/standards/ecosystem-overview")
        assert "disclaimer" in r.json()


# ---------------------------------------------------------------------------
# Governance / No Causation
# ---------------------------------------------------------------------------


class TestGovernance:
    def test_no_causation_in_standards(self):
        r = client.get("/api/standards/quality-standards", headers=HEADERS)
        text = _flatten(r.json().get("standards", []))
        assert not _has_causation(text)

    def test_no_causation_in_benchmarks(self):
        r = client.get("/api/standards/benchmarks", headers=HEADERS)
        text = _flatten(r.json().get("reports", []))
        assert not _has_causation(text)

    def test_disclaimer_present_on_all_endpoints(self):
        endpoints = [
            "/api/standards/quality-standards",
            "/api/standards/baseline-governance",
            "/api/standards/benchmarks",
            "/api/standards/regional-deployments",
            "/api/standards/api-partners",
            "/api/standards/consortium",
            "/api/standards/publications",
            "/api/standards/dashboard",
        ]
        for ep in endpoints:
            r = client.get(ep, headers=HEADERS)
            assert r.status_code == 200, f"{ep} returned {r.status_code}"
            assert "disclaimer" in r.json(), f"No disclaimer in {ep}"
            assert len(r.json()["disclaimer"]) >= _DISCLAIMER_MIN_LEN

    def test_human_review_required_on_all_endpoints(self):
        endpoints = [
            "/api/standards/quality-standards",
            "/api/standards/benchmarks",
            "/api/standards/regional-deployments",
            "/api/standards/consortium",
            "/api/standards/publications",
            "/api/standards/dashboard",
        ]
        for ep in endpoints:
            r = client.get(ep, headers=HEADERS)
            assert r.status_code == 200
            assert r.json().get("human_review_required") is True, f"{ep} missing human_review_required"
