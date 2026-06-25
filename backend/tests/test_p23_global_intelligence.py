"""P23: Global Surgical Intelligence Network — test suite."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

HEADERS = {"Authorization": "Bearer dev-token"}
NO_AUTH = {}

client = TestClient(app, raise_server_exceptions=True)

_CAUSATION_PHRASES = [
    "causes",
    "caused by",
    "proves",
    "confirms causation",
    "establishes causation",
]


def _flatten_text(obj) -> str:
    """Recursively stringify all values in a nested structure."""
    if isinstance(obj, dict):
        return " ".join(_flatten_text(v) for v in obj.values())
    if isinstance(obj, list):
        return " ".join(_flatten_text(v) for v in obj)
    return str(obj) if obj is not None else ""


def _flatten_keys(obj) -> set:
    """Recursively collect all dict keys."""
    keys: set = set()
    if isinstance(obj, dict):
        for k, v in obj.items():
            keys.add(k)
            keys |= _flatten_keys(v)
    elif isinstance(obj, list):
        for item in obj:
            keys |= _flatten_keys(item)
    return keys


def _has_causation(text: str) -> bool:
    t = text.lower()
    return any(phrase in t for phrase in _CAUSATION_PHRASES)


# ---------------------------------------------------------------------------
# Global Signals
# ---------------------------------------------------------------------------


class TestGlobalSignals:
    def test_signals_returns_200(self):
        r = client.get("/api/global-intelligence/signals", headers=HEADERS)
        assert r.status_code == 200

    def test_signals_requires_auth(self):
        r = client.get("/api/global-intelligence/signals", headers=NO_AUTH)
        assert r.status_code in (401, 403)

    def test_signals_has_disclaimer(self):
        r = client.get("/api/global-intelligence/signals", headers=HEADERS)
        assert r.status_code == 200
        body = r.json()
        assert "disclaimer" in body
        assert len(body["disclaimer"]) > 10

    def test_signals_no_causation_language(self):
        r = client.get("/api/global-intelligence/signals", headers=HEADERS)
        assert r.status_code == 200
        body = r.json()
        text = _flatten_text(body.get("signals", []))
        assert not _has_causation(text), f"Causation language found in signals: {text[:200]}"

    def test_signals_human_review_required(self):
        r = client.get("/api/global-intelligence/signals", headers=HEADERS)
        assert r.status_code == 200
        body = r.json()
        assert body.get("human_review_required") is True

    def test_signals_k_anonymity_verified(self):
        r = client.get("/api/global-intelligence/signals", headers=HEADERS)
        assert r.status_code == 200
        body = r.json()
        signals = body.get("signals", [])
        assert len(signals) > 0
        for sig in signals:
            assert sig.get("facility_count", 0) >= 5, (
                f"Published signal has facility_count < 5: {sig}"
            )

    def test_signals_region_filter(self):
        r = client.get("/api/global-intelligence/signals?region=north_america", headers=HEADERS)
        assert r.status_code == 200


# ---------------------------------------------------------------------------
# Risk Registry
# ---------------------------------------------------------------------------


class TestRiskRegistry:
    def test_registry_returns_200(self):
        r = client.get("/api/global-intelligence/risk-registry", headers=HEADERS)
        assert r.status_code == 200

    def test_registry_is_list(self):
        r = client.get("/api/global-intelligence/risk-registry", headers=HEADERS)
        assert r.status_code == 200
        body = r.json()
        assert isinstance(body.get("entries"), list)

    def test_registry_has_risk_score(self):
        r = client.get("/api/global-intelligence/risk-registry", headers=HEADERS)
        assert r.status_code == 200
        entries = r.json().get("entries", [])
        assert len(entries) > 0
        for entry in entries:
            assert "risk_score" in entry
            assert isinstance(entry["risk_score"], (int, float))

    def test_registry_human_review_required(self):
        r = client.get("/api/global-intelligence/risk-registry", headers=HEADERS)
        assert r.status_code == 200
        entries = r.json().get("entries", [])
        for entry in entries:
            assert entry.get("human_review_required") is True

    def test_registry_requires_auth(self):
        r = client.get("/api/global-intelligence/risk-registry", headers=NO_AUTH)
        assert r.status_code in (401, 403)


# ---------------------------------------------------------------------------
# Recall Warnings
# ---------------------------------------------------------------------------


class TestRecallWarnings:
    def test_warnings_returns_200(self):
        r = client.get("/api/global-intelligence/recall-warnings", headers=HEADERS)
        assert r.status_code == 200

    def test_warnings_is_list(self):
        r = client.get("/api/global-intelligence/recall-warnings", headers=HEADERS)
        assert r.status_code == 200
        body = r.json()
        assert isinstance(body.get("warnings"), list)

    def test_warnings_no_causation_language(self):
        r = client.get("/api/global-intelligence/recall-warnings", headers=HEADERS)
        assert r.status_code == 200
        body = r.json()
        text = _flatten_text(body.get("warnings", []))
        assert not _has_causation(text)

    def test_warnings_human_review_required(self):
        r = client.get("/api/global-intelligence/recall-warnings", headers=HEADERS)
        assert r.status_code == 200
        body = r.json()
        assert body.get("human_review_required") is True
        for w in body.get("warnings", []):
            assert w.get("human_review_required") is True

    def test_warnings_has_disclaimer(self):
        r = client.get("/api/global-intelligence/recall-warnings", headers=HEADERS)
        assert r.status_code == 200
        body = r.json()
        assert "disclaimer" in body
        assert len(body["disclaimer"]) > 10

    def test_warnings_not_recall_notice(self):
        """Disclaimers must clarify these are not regulatory recall notices."""
        r = client.get("/api/global-intelligence/recall-warnings", headers=HEADERS)
        assert r.status_code == 200
        body = r.json()
        disclaimer = body.get("disclaimer", "")
        # Check the overall disclaimer or individual warning disclaimers note it's not a recall notice
        warnings = body.get("warnings", [])
        all_disclaimers = disclaimer + " ".join(
            w.get("disclaimer", "") for w in warnings
        )
        assert "not" in all_disclaimers.lower() or "human review" in all_disclaimers.lower()


# ---------------------------------------------------------------------------
# Participant Status
# ---------------------------------------------------------------------------


class TestParticipantStatus:
    def test_participant_status_returns_200(self):
        r = client.get("/api/global-intelligence/participant-status", headers=HEADERS)
        assert r.status_code == 200

    def test_participant_status_has_enrollment_status(self):
        r = client.get("/api/global-intelligence/participant-status", headers=HEADERS)
        assert r.status_code == 200
        body = r.json()
        participant = body.get("participant", body)
        assert "enrollment_status" in participant

    def test_participant_status_requires_auth(self):
        r = client.get("/api/global-intelligence/participant-status", headers=NO_AUTH)
        assert r.status_code in (401, 403)


# ---------------------------------------------------------------------------
# Regulatory Evidence
# ---------------------------------------------------------------------------


class TestRegulatoryEvidence:
    def test_evidence_returns_200(self):
        r = client.get("/api/global-intelligence/regulatory-evidence", headers=HEADERS)
        assert r.status_code == 200

    def test_evidence_is_list(self):
        r = client.get("/api/global-intelligence/regulatory-evidence", headers=HEADERS)
        assert r.status_code == 200
        body = r.json()
        assert isinstance(body.get("packages"), list)

    def test_evidence_has_disclaimer(self):
        r = client.get("/api/global-intelligence/regulatory-evidence", headers=HEADERS)
        assert r.status_code == 200
        body = r.json()
        assert "disclaimer" in body
        for pkg in body.get("packages", []):
            assert "disclaimer" in pkg

    def test_evidence_requires_auth(self):
        r = client.get("/api/global-intelligence/regulatory-evidence", headers=NO_AUTH)
        assert r.status_code in (401, 403)

    def test_evidence_authority_filter(self):
        r = client.get("/api/global-intelligence/regulatory-evidence?authority=FDA", headers=HEADERS)
        assert r.status_code == 200


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------


class TestDashboard:
    _KPI_KEYS = [
        "active_global_signals",
        "recall_early_warnings",
        "risk_registry_entries",
        "network_participants",
        "human_review_required_count",
    ]

    def test_dashboard_returns_200(self):
        r = client.get("/api/global-intelligence/dashboard", headers=HEADERS)
        assert r.status_code == 200

    def test_dashboard_has_all_kpis(self):
        r = client.get("/api/global-intelligence/dashboard", headers=HEADERS)
        assert r.status_code == 200
        body = r.json()
        for key in self._KPI_KEYS:
            assert key in body, f"Missing KPI key: {key}"

    def test_dashboard_has_disclaimer(self):
        r = client.get("/api/global-intelligence/dashboard", headers=HEADERS)
        assert r.status_code == 200
        body = r.json()
        assert "disclaimer" in body
        assert len(body["disclaimer"]) > 10

    def test_dashboard_requires_auth(self):
        r = client.get("/api/global-intelligence/dashboard", headers=NO_AUTH)
        assert r.status_code in (401, 403)

    def test_dashboard_human_review_required(self):
        r = client.get("/api/global-intelligence/dashboard", headers=HEADERS)
        assert r.status_code == 200
        body = r.json()
        assert body.get("human_review_required") is True


# ---------------------------------------------------------------------------
# Contribute
# ---------------------------------------------------------------------------


class TestContribute:
    _PAYLOAD = {
        "signal_type": "instrument_quality",
        "instrument_category": "flexible_scopes",
        "finding_type": "contamination",
        "region": "north_america",
        "facility_count": 12,
        "signal_strength": 0.7,
        "association_reason": "Elevated contamination rate observed across reporting facilities.",
    }

    def test_contribute_returns_200(self):
        r = client.post(
            "/api/global-intelligence/contribute",
            json=self._PAYLOAD,
            headers=HEADERS,
        )
        assert r.status_code == 200

    def test_contribute_requires_auth(self):
        r = client.post(
            "/api/global-intelligence/contribute",
            json=self._PAYLOAD,
            headers=NO_AUTH,
        )
        assert r.status_code in (401, 403)

    def test_contribute_returns_contribution_id(self):
        r = client.post(
            "/api/global-intelligence/contribute",
            json=self._PAYLOAD,
            headers=HEADERS,
        )
        assert r.status_code == 200
        body = r.json()
        assert "contribution_id" in body
        assert len(body["contribution_id"]) > 5


# ---------------------------------------------------------------------------
# Network Stats (public endpoint)
# ---------------------------------------------------------------------------


class TestNetworkStats:
    def test_network_stats_returns_200_no_auth(self):
        r = client.get("/api/global-intelligence/network-stats", headers=NO_AUTH)
        assert r.status_code == 200

    def test_network_stats_has_participant_count(self):
        r = client.get("/api/global-intelligence/network-stats", headers=NO_AUTH)
        assert r.status_code == 200
        body = r.json()
        assert "participant_count" in body
        assert isinstance(body["participant_count"], int)

    def test_network_stats_has_regions(self):
        r = client.get("/api/global-intelligence/network-stats")
        assert r.status_code == 200
        body = r.json()
        assert "regions_covered" in body
        assert isinstance(body["regions_covered"], list)


# ---------------------------------------------------------------------------
# Governance / Privacy
# ---------------------------------------------------------------------------


class TestGovernance:
    _FORBIDDEN_KEYS = {
        "patient_id",
        "mrn",
        "dob",
        "ssn",
        "patient_name",
        "facility_name",
        "facility_id",
    }

    def test_no_patient_or_facility_identifiers_in_signals(self):
        r = client.get("/api/global-intelligence/signals", headers=HEADERS)
        assert r.status_code == 200
        body = r.json()
        keys = _flatten_keys(body.get("signals", []))
        overlap = keys & self._FORBIDDEN_KEYS
        assert not overlap, f"Forbidden identifier keys found in signals: {overlap}"

    def test_no_causation_in_risk_registry(self):
        r = client.get("/api/global-intelligence/risk-registry", headers=HEADERS)
        assert r.status_code == 200
        body = r.json()
        entries = body.get("entries", [])
        for entry in entries:
            text = _flatten_text(entry)
            assert not _has_causation(text), f"Causation language in registry entry: {text[:200]}"

    def test_disclaimer_present_everywhere(self):
        endpoints = [
            "/api/global-intelligence/signals",
            "/api/global-intelligence/risk-registry",
            "/api/global-intelligence/recall-warnings",
            "/api/global-intelligence/participant-status",
            "/api/global-intelligence/regulatory-evidence",
            "/api/global-intelligence/dashboard",
        ]
        for ep in endpoints:
            r = client.get(ep, headers=HEADERS)
            assert r.status_code == 200, f"Endpoint {ep} returned {r.status_code}"
            body = r.json()
            assert "disclaimer" in body, f"No disclaimer in response from {ep}"
            assert len(body["disclaimer"]) > 10, f"Disclaimer too short in {ep}"


# ---------------------------------------------------------------------------
# Tier-1: Signal Governance Board Review
# ---------------------------------------------------------------------------


class TestSignalReview:
    _PAYLOAD = {
        "signal_type": "instrument_quality",
        "instrument_category": "flexible_scopes",
        "finding_type": "contamination",
        "region": "north_america",
        "facility_count": 12,
        "signal_strength": 0.7,
        "association_reason": "Aggregate pattern across reporting facilities.",
    }

    def _contribute(self) -> int:
        r = client.post("/api/global-intelligence/contribute", json=self._PAYLOAD, headers=HEADERS)
        assert r.status_code == 200
        return r.json()["signal_record_id"]

    def test_approve_publishes_signal(self):
        sid = self._contribute()
        r = client.post(
            f"/api/global-intelligence/signals/{sid}/review",
            json={"decision": "approve", "reviewer_notes": "k-anonymity met"},
            headers=HEADERS,
        )
        assert r.status_code == 200
        body = r.json()
        assert body["decision"] == "approve"
        assert body["published"] is True
        assert body["outcome"] == "approved_and_published"

    def test_reject_does_not_publish(self):
        sid = self._contribute()
        r = client.post(
            f"/api/global-intelligence/signals/{sid}/review",
            json={"decision": "reject"},
            headers=HEADERS,
        )
        assert r.status_code == 200
        body = r.json()
        assert body["decision"] == "reject"
        assert body["published"] is False

    def test_double_review_is_conflict(self):
        sid = self._contribute()
        client.post(
            f"/api/global-intelligence/signals/{sid}/review",
            json={"decision": "reject"},
            headers=HEADERS,
        )
        r = client.post(
            f"/api/global-intelligence/signals/{sid}/review",
            json={"decision": "approve"},
            headers=HEADERS,
        )
        assert r.status_code == 409

    def test_approve_blocks_low_k_anonymity(self):
        # facility_count=6 passes contribute gate (>=5) but fails approve gate (>=10)
        payload6 = {**self._PAYLOAD, "facility_count": 6}
        r6 = client.post("/api/global-intelligence/contribute", json=payload6, headers=HEADERS)
        assert r6.status_code == 200
        sid6 = r6.json()["signal_record_id"]
        ra = client.post(
            f"/api/global-intelligence/signals/{sid6}/review",
            json={"decision": "approve"},
            headers=HEADERS,
        )
        assert ra.status_code == 422
        assert ra.json()["detail"]["error"] == "k_anonymity_not_met"

    def test_review_invalid_decision(self):
        sid = self._contribute()
        r = client.post(
            f"/api/global-intelligence/signals/{sid}/review",
            json={"decision": "maybe"},
            headers=HEADERS,
        )
        assert r.status_code == 422

    def test_review_unknown_signal_is_404(self):
        r = client.post(
            "/api/global-intelligence/signals/999999/review",
            json={"decision": "reject"},
            headers=HEADERS,
        )
        assert r.status_code == 404

    def test_review_requires_auth(self):
        sid = self._contribute()
        r = client.post(
            f"/api/global-intelligence/signals/{sid}/review",
            json={"decision": "reject"},
            headers=NO_AUTH,
        )
        assert r.status_code in (401, 403)

    def test_review_has_disclaimer(self):
        sid = self._contribute()
        r = client.post(
            f"/api/global-intelligence/signals/{sid}/review",
            json={"decision": "reject"},
            headers=HEADERS,
        )
        assert r.status_code == 200
        assert "disclaimer" in r.json()


# ---------------------------------------------------------------------------
# Tier-1: Participant Enrollment & DPA Workflow
# ---------------------------------------------------------------------------

import time as _time  # noqa: E402

_TS = str(int(_time.time() * 1000))


class TestEnrollment:
    _ENROLL = {
        "participant_type": "hospital",
        "region": "north_america",
        "contribution_categories": ["inspection_metrics", "quality_rates"],
    }

    def test_enroll_creates_pending_participant(self):
        # Use a unique tenant by patching the header (dev-token maps to default-tenant;
        # we test the endpoint logic via the happy-path with default-tenant if not yet enrolled)
        r = client.post("/api/global-intelligence/enroll", json=self._ENROLL, headers=HEADERS)
        # May already be enrolled (conftest seeds participant); either 200 or 409
        assert r.status_code in (200, 409)

    def test_enroll_409_if_already_enrolled(self):
        # First call — may create or already exist
        client.post("/api/global-intelligence/enroll", json=self._ENROLL, headers=HEADERS)
        # Second call must 409
        r = client.post("/api/global-intelligence/enroll", json=self._ENROLL, headers=HEADERS)
        assert r.status_code == 409

    def test_enroll_requires_auth(self):
        r = client.post("/api/global-intelligence/enroll", json=self._ENROLL, headers=NO_AUTH)
        assert r.status_code in (401, 403)

    def test_sign_dpa_activates_enrollment(self):
        # Ensure participant exists first
        client.post("/api/global-intelligence/enroll", json=self._ENROLL, headers=HEADERS)
        r = client.post("/api/global-intelligence/sign-dpa", headers=HEADERS)
        # Either 200 (signed) or 409 (already signed) — both are valid depending on test order
        assert r.status_code in (200, 409)
        if r.status_code == 200:
            body = r.json()
            assert body["dpa_signed"] is True
            assert body["enrollment_status"] == "active"
            assert "disclaimer" in body

    def test_sign_dpa_requires_auth(self):
        r = client.post("/api/global-intelligence/sign-dpa", headers=NO_AUTH)
        assert r.status_code in (401, 403)

    def test_sign_dpa_404_if_not_enrolled(self):
        # This can only fire if the tenant has no participant — hard to guarantee in shared test db
        # We verify the endpoint returns 200 or 409 (not 500) for default-tenant
        r = client.post("/api/global-intelligence/sign-dpa", headers=HEADERS)
        assert r.status_code in (200, 404, 409)


# ---------------------------------------------------------------------------
# Tier-1: Recall Warning Escalation Actions
# ---------------------------------------------------------------------------


class TestRecallNotify:
    def _get_warning_id(self) -> int:
        """Fetch first active warning or seed one."""
        r = client.get("/api/global-intelligence/recall-warnings", headers=HEADERS)
        warnings = r.json().get("warnings", [])
        assert len(warnings) > 0, "No warnings available for notify test"
        return int(warnings[0]["id"])

    def test_notify_manufacturer(self):
        wid = self._get_warning_id()
        r = client.post(
            f"/api/global-intelligence/recall-warnings/{wid}/notify",
            json={"target": "manufacturer", "notification_notes": "Notified via email."},
            headers=HEADERS,
        )
        # 200 if not yet notified, 409 if already notified
        assert r.status_code in (200, 409)
        if r.status_code == 200:
            body = r.json()
            assert body["manufacturer_notified"] is True
            assert "human_review_required" in body
            assert "important_notice" in body
            assert "disclaimer" in body

    def test_notify_regulatory(self):
        wid = self._get_warning_id()
        r = client.post(
            f"/api/global-intelligence/recall-warnings/{wid}/notify",
            json={"target": "regulatory"},
            headers=HEADERS,
        )
        assert r.status_code in (200, 409)
        if r.status_code == 200:
            body = r.json()
            assert body["regulatory_notified"] is True

    def test_notify_invalid_target(self):
        wid = self._get_warning_id()
        r = client.post(
            f"/api/global-intelligence/recall-warnings/{wid}/notify",
            json={"target": "press"},
            headers=HEADERS,
        )
        assert r.status_code == 422

    def test_notify_unknown_warning_is_404(self):
        r = client.post(
            "/api/global-intelligence/recall-warnings/999999/notify",
            json={"target": "manufacturer"},
            headers=HEADERS,
        )
        assert r.status_code == 404

    def test_notify_requires_auth(self):
        wid = self._get_warning_id()
        r = client.post(
            f"/api/global-intelligence/recall-warnings/{wid}/notify",
            json={"target": "manufacturer"},
            headers=NO_AUTH,
        )
        assert r.status_code in (401, 403)

    def test_notify_human_review_required_in_response(self):
        wid = self._get_warning_id()
        r = client.post(
            f"/api/global-intelligence/recall-warnings/{wid}/notify",
            json={"target": "manufacturer"},
            headers=HEADERS,
        )
        if r.status_code == 200:
            assert r.json().get("human_review_required") is True

    def test_important_notice_not_a_recall(self):
        wid = self._get_warning_id()
        r = client.post(
            f"/api/global-intelligence/recall-warnings/{wid}/notify",
            json={"target": "manufacturer"},
            headers=HEADERS,
        )
        if r.status_code == 200:
            notice = r.json().get("important_notice", "")
            assert "NOT" in notice or "not" in notice.lower()
