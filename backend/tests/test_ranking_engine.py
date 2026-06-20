"""Tests for the Inspection Ranking Engine (unit + API integration)."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.schemas.ranking import RankingRequest
from app.services.ranking_engine import (
    CATEGORY_DEDUCTIONS,
    _category_deduction,
    _confidence_penalty,
    _identifier_bonus,
    _risk_level,
    _severity_multiplier,
    _resolve_weights,
    _resolve_multipliers,
    score_inspection,
    score_composite,
)
from app.schemas.ranking import CompositeRankingRequest, CompositeFindingInput

client = TestClient(app)
AUTH = {"Authorization": "Bearer dev-token", "X-LumenAI-Role": "operator"}
ADMIN_AUTH = {"Authorization": "Bearer dev-token", "X-LumenAI-Role": "hospital_admin"}


# ── Unit tests: scoring helpers ───────────────────────────────────────────────

class TestCategoryDeduction:
    def test_blood_has_highest_deduction(self):
        weights = _resolve_weights(None)
        assert _category_deduction("blood / retained blood residue", weights) == CATEGORY_DEDUCTIONS["blood / retained blood residue"]

    def test_bone_deduction(self):
        weights = _resolve_weights(None)
        assert _category_deduction("bone / bone fragment", weights) >= 25

    def test_unknown_category_falls_back_to_other(self):
        weights = _resolve_weights(None)
        assert _category_deduction("unrecognized finding xyz", weights) == CATEGORY_DEDUCTIONS["other"]

    def test_partial_match_corrosion(self):
        weights = _resolve_weights(None)
        assert _category_deduction("corrosion / surface rust", weights) == CATEGORY_DEDUCTIONS["corrosion / surface rust"]

    def test_profile_override_changes_weight(self):
        profile = {"category_weights": {"blood / retained blood residue": 5}}
        weights = _resolve_weights(profile)
        assert _category_deduction("blood / retained blood residue", weights) == 5


class TestSeverityMultiplier:
    def test_critical_is_highest(self):
        m = _resolve_multipliers(None)
        assert _severity_multiplier("critical", m) > _severity_multiplier("high", m)

    def test_low_is_below_one(self):
        m = _resolve_multipliers(None)
        assert _severity_multiplier("low", m) < 1.0

    def test_unknown_severity_returns_one(self):
        m = _resolve_multipliers(None)
        assert _severity_multiplier("extreme", m) == 1.0

    def test_profile_override_multiplier(self):
        profile = {"severity_multipliers": {"critical": 2.0}}
        m = _resolve_multipliers(profile)
        assert _severity_multiplier("critical", m) == 2.0


class TestConfidencePenalty:
    def test_high_confidence_no_penalty(self):
        assert _confidence_penalty(0.95) == 0

    def test_medium_confidence_penalty(self):
        assert _confidence_penalty(0.70) == 5

    def test_low_confidence_max_penalty(self):
        assert _confidence_penalty(0.30) == 15


class TestIdentifierBonus:
    def test_all_identifiers_capped_at_five(self):
        bonus, matched = _identifier_bonus("BC123", "QR456", "KD789")
        assert bonus == 5
        assert len(matched) == 3

    def test_no_identifiers_no_bonus(self):
        bonus, matched = _identifier_bonus("", "", "")
        assert bonus == 0
        assert matched == {}

    def test_one_identifier(self):
        bonus, matched = _identifier_bonus("BC123", "", "")
        assert bonus == 2
        assert "barcode" in matched


class TestRiskLevel:
    def test_score_90_is_low(self):
        assert _risk_level(90) == "Low"

    def test_score_70_is_medium(self):
        assert _risk_level(70) == "Medium"

    def test_score_50_is_high(self):
        assert _risk_level(50) == "High"

    def test_score_30_is_critical(self):
        assert _risk_level(30) == "Critical"

    def test_score_0_is_critical(self):
        assert _risk_level(0) == "Critical"


# ── Integration: score_inspection function ────────────────────────────────────

class TestScoreInspection:
    def _req(self, **kwargs) -> RankingRequest:
        defaults = dict(
            finding_category="blood / retained blood residue",
            severity="critical",
            confidence_score=0.90,
        )
        defaults.update(kwargs)
        return RankingRequest(**defaults)

    def test_returns_ranking_result(self):
        result = score_inspection(self._req())
        assert 0 <= result.inspection_score <= 100

    def test_critical_blood_scores_low(self):
        result = score_inspection(self._req(severity="critical"))
        assert result.inspection_score < 60
        assert result.risk_level in {"High", "Critical"}

    def test_low_severity_debris_scores_higher_than_critical_blood(self):
        low = score_inspection(self._req(finding_category="debris / retained debris", severity="low"))
        high = score_inspection(self._req(finding_category="blood / retained blood residue", severity="critical"))
        assert low.inspection_score > high.inspection_score

    def test_approved_baseline_gives_bonus(self):
        with_baseline = score_inspection(self._req(
            baseline_status="approved_baseline_found",
            instrument_match_status="matched",
        ))
        without_baseline = score_inspection(self._req(
            baseline_status="baseline_not_available",
            instrument_match_status="unknown",
        ))
        assert with_baseline.inspection_score >= without_baseline.inspection_score

    def test_identifier_present_increases_score(self):
        with_id = score_inspection(self._req(barcode_value="BC123"))
        without_id = score_inspection(self._req(barcode_value=""))
        assert with_id.inspection_score >= without_id.inspection_score

    def test_findings_list_populated(self):
        result = score_inspection(self._req())
        assert len(result.findings) == 1
        finding = result.findings[0]
        assert finding.category == "blood / retained blood residue"
        assert finding.score_deduction > 0

    def test_audit_evidence_contains_required_keys(self):
        result = score_inspection(self._req())
        audit = result.audit_evidence
        assert audit.ranking_mode
        assert isinstance(audit.baseline_review_required, bool)
        assert "final_score" in audit.scoring_breakdown
        assert "base_score" in audit.scoring_breakdown

    def test_recommended_action_is_not_empty(self):
        result = score_inspection(self._req())
        assert len(result.recommended_action) > 0

    def test_score_bounded_0_to_100(self):
        for severity in ["low", "medium", "high", "critical"]:
            result = score_inspection(self._req(severity=severity, confidence_score=0.1))
            assert 0 <= result.inspection_score <= 100

    def test_baseline_match_pct_zero_without_baseline(self):
        result = score_inspection(self._req(baseline_status="baseline_not_available"))
        assert result.baseline_match_pct == 0.0

    def test_baseline_match_pct_positive_with_approved_baseline(self):
        result = score_inspection(self._req(
            baseline_status="approved_baseline_found",
            instrument_match_status="matched",
            confidence_score=0.9,
        ))
        assert result.baseline_match_pct > 0

    def test_profile_weights_applied(self):
        # With blood deduction reduced to 5, score should be much higher than default
        profile = {"category_weights": {"blood / retained blood residue": 5}}
        result_custom = score_inspection(self._req(), profile=profile)
        result_default = score_inspection(self._req())
        assert result_custom.inspection_score > result_default.inspection_score

    def test_history_elevation_flag_false_without_db(self):
        result = score_inspection(self._req(instrument_id=1))
        assert result.history_elevation_applied is False  # no db passed


# ── Composite scoring ─────────────────────────────────────────────────────────

class TestCompositeScoring:
    def _req(self, findings: list[dict] | None = None) -> CompositeRankingRequest:
        if findings is None:
            findings = [
                {"finding_category": "blood / retained blood residue", "severity": "critical", "confidence_score": 0.9},
                {"finding_category": "crack / hairline fracture", "severity": "critical", "confidence_score": 0.85},
            ]
        return CompositeRankingRequest(
            instrument_name="Test Instrument",
            findings=[CompositeFindingInput(**f) for f in findings],
        )

    def test_composite_score_bounded(self):
        result = score_composite(self._req())
        assert 0 <= result.composite_score <= 100

    def test_two_critical_findings_trigger_escalation(self):
        result = score_composite(self._req())
        assert result.compound_escalation_applied is True
        assert result.composite_score <= 39
        assert result.risk_level == "Critical"

    def test_one_critical_finding_no_escalation(self):
        result = score_composite(self._req(findings=[
            {"finding_category": "blood / retained blood residue", "severity": "critical", "confidence_score": 0.9},
            {"finding_category": "discoloration", "severity": "low", "confidence_score": 0.95},
        ]))
        assert result.compound_escalation_applied is False

    def test_finding_results_count_matches_input(self):
        result = score_composite(self._req())
        assert len(result.finding_results) == 2

    def test_composite_recommended_action_includes_compound(self):
        result = score_composite(self._req())
        assert "COMPOUND RISK" in result.recommended_action

    def test_critical_findings_count(self):
        result = score_composite(self._req())
        assert result.critical_findings == 2

    def test_single_finding_no_escalation(self):
        result = score_composite(self._req(findings=[
            {"finding_category": "debris / retained debris", "severity": "low", "confidence_score": 0.9}
        ]))
        assert result.compound_escalation_applied is False
        assert result.composite_score > 60


# ── API endpoint tests ────────────────────────────────────────────────────────

class TestRankingAPI:
    def _payload(self, **kwargs) -> dict:
        defaults = dict(
            finding_category="blood / retained blood residue",
            severity="critical",
            confidence_score=0.85,
        )
        defaults.update(kwargs)
        return defaults

    def test_post_score_returns_200(self):
        res = client.post("/api/enterprise/ranking/score", json=self._payload(), headers=AUTH)
        assert res.status_code == 200

    def test_post_score_returns_inspection_score(self):
        res = client.post("/api/enterprise/ranking/score", json=self._payload(), headers=AUTH)
        data = res.json()
        assert "inspection_score" in data
        assert 0 <= data["inspection_score"] <= 100

    def test_post_score_returns_risk_level(self):
        res = client.post("/api/enterprise/ranking/score", json=self._payload(), headers=AUTH)
        data = res.json()
        assert data["risk_level"] in {"Low", "Medium", "High", "Critical"}

    def test_post_score_returns_audit_evidence(self):
        res = client.post("/api/enterprise/ranking/score", json=self._payload(), headers=AUTH)
        data = res.json()
        assert "audit_evidence" in data
        assert "ranking_mode" in data["audit_evidence"]

    def test_post_score_returns_recommended_action(self):
        res = client.post("/api/enterprise/ranking/score", json=self._payload(), headers=AUTH)
        data = res.json()
        assert "recommended_action" in data
        assert len(data["recommended_action"]) > 0

    def test_post_score_returns_capa_auto_triggered_field(self):
        res = client.post("/api/enterprise/ranking/score", json=self._payload(), headers=AUTH)
        data = res.json()
        assert "capa_auto_triggered" in data

    def test_post_score_invalid_confidence_returns_422(self):
        res = client.post(
            "/api/enterprise/ranking/score",
            json=self._payload(confidence_score=1.5),
            headers=AUTH,
        )
        assert res.status_code == 422

    def test_post_score_missing_finding_category_returns_422(self):
        payload = self._payload()
        del payload["finding_category"]
        res = client.post("/api/enterprise/ranking/score", json=payload, headers=AUTH)
        assert res.status_code == 422

    def test_composite_score_returns_200(self):
        res = client.post(
            "/api/enterprise/ranking/composite-score",
            json={
                "instrument_name": "Frazier Suction",
                "findings": [
                    {"finding_category": "blood / retained blood residue", "severity": "critical", "confidence_score": 0.9},
                    {"finding_category": "crack / hairline fracture", "severity": "critical", "confidence_score": 0.85},
                ],
            },
            headers=AUTH,
        )
        assert res.status_code == 200

    def test_composite_score_compound_escalation(self):
        res = client.post(
            "/api/enterprise/ranking/composite-score",
            json={
                "instrument_name": "Test",
                "findings": [
                    {"finding_category": "blood / retained blood residue", "severity": "critical", "confidence_score": 0.9},
                    {"finding_category": "tissue / retained tissue", "severity": "critical", "confidence_score": 0.88},
                ],
            },
            headers=AUTH,
        )
        data = res.json()
        assert data["compound_escalation_applied"] is True
        assert data["composite_score"] <= 39

    def test_kpi_summary_returns_200(self):
        res = client.get("/api/enterprise/ranking/kpi-summary", headers=AUTH)
        assert res.status_code == 200

    def test_kpi_summary_shape(self):
        res = client.get("/api/enterprise/ranking/kpi-summary", headers=AUTH)
        data = res.json()
        assert "total_ranked" in data
        assert "avg_inspection_score" in data
        assert "blood_count" in data
        assert "baseline_mismatch_rate_pct" in data
        assert "barcode_match_rate_pct" in data
        assert "qr_match_rate_pct" in data

    def test_history_nonexistent_finding_returns_404(self):
        res = client.get("/api/enterprise/ranking/history/999999", headers=AUTH)
        assert res.status_code == 404

    def test_pdf_report_nonexistent_finding_returns_404(self):
        res = client.get("/api/enterprise/ranking/score/999999/report.pdf", headers=AUTH)
        assert res.status_code == 404

    def test_insulation_damage_critical_scores_low(self):
        res = client.post(
            "/api/enterprise/ranking/score",
            json=self._payload(finding_category="insulation damage", severity="critical"),
            headers=AUTH,
        )
        data = res.json()
        assert data["inspection_score"] < 70

    def test_low_severity_other_scores_high(self):
        res = client.post(
            "/api/enterprise/ranking/score",
            json=self._payload(
                finding_category="discoloration",
                severity="low",
                confidence_score=0.95,
                baseline_status="approved_baseline_found",
                instrument_match_status="matched",
                barcode_value="BC123",
            ),
            headers=AUTH,
        )
        data = res.json()
        assert data["inspection_score"] >= 80
        assert data["risk_level"] == "Low"


class TestScoringProfiles:
    def test_create_profile_returns_200(self):
        res = client.post(
            "/api/enterprise/ranking/profiles",
            params={"tenant_id": "test-tenant"},
            json={
                "profile_name": "Trauma Center Profile",
                "category_weights": {"blood / retained blood residue": 40},
                "compound_escalation_threshold": 1,
                "created_by": "test-admin",
            },
            headers=ADMIN_AUTH,
        )
        assert res.status_code == 200

    def test_create_profile_returns_id(self):
        res = client.post(
            "/api/enterprise/ranking/profiles",
            params={"tenant_id": "test-tenant-2"},
            json={"profile_name": "ASC Profile"},
            headers=ADMIN_AUTH,
        )
        data = res.json()
        assert "id" in data
        assert data["profile_name"] == "ASC Profile"

    def test_get_active_profile_no_profile_returns_null(self):
        res = client.get(
            "/api/enterprise/ranking/profiles/nonexistent-tenant",
            headers=ADMIN_AUTH,
        )
        assert res.status_code == 200
        assert res.json() is None

    def test_get_active_profile_after_create(self):
        client.post(
            "/api/enterprise/ranking/profiles",
            params={"tenant_id": "profile-test-tenant"},
            json={"profile_name": "My Profile", "compound_escalation_threshold": 3},
            headers=ADMIN_AUTH,
        )
        res = client.get(
            "/api/enterprise/ranking/profiles/profile-test-tenant",
            headers=ADMIN_AUTH,
        )
        data = res.json()
        assert data is not None
        assert data["profile_name"] == "My Profile"
        assert data["compound_escalation_threshold"] == 3
