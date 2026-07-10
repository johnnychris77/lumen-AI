"""LumenAI Inspect v2.4 — Clinical Memory & Predictive Intelligence
("Project Insight").

Covers: memory lookup, similarity search, recurrence detection, health
forecast, timeline generation, and recommendation enrichment.
"""
from __future__ import annotations

import json

from fastapi.testclient import TestClient

from app.db.session import SessionLocal
from app.main import app
from app.models.baseline_library import BaselineLibraryEntry
from app.models.knowledge import APPROVED, KnowledgeArticle
from app.services.clinical_memory_service import (
    build_memory_recommendation, build_memory_timeline, get_clinical_memory,
)
from app.services.instrument_health_forecast_service import forecast_instrument_health
from app.services.instrument_condition_service import instrument_condition_history
from app.services.predictive_risk_engine import estimate_predictive_risk
from app.services.recurrence_detection_service import detect_recurring_issues
from app.services.similar_instrument_search_service import find_similar_instruments

client = TestClient(app)
AUTH_ADMIN = {"Authorization": "Bearer dev-token"}


def _baseline(itype: str) -> None:
    db = SessionLocal()
    try:
        db.query(BaselineLibraryEntry).filter(BaselineLibraryEntry.instrument_category == itype).delete()
        db.add(BaselineLibraryEntry(
            udi=f"v24-{itype}", instrument_category=itype, manufacturer_name="M",
            model_name="X", baseline_type="manufacturer", approval_status="approved",
        ))
        db.commit()
    finally:
        db.close()


def _create_inspection(instrument_type: str, barcode: str, sha_suffix: str, finding_categories=None) -> dict:
    _baseline(instrument_type)
    r = client.post("/api/inspections", headers=AUTH_ADMIN, json={
        "instrument_type": instrument_type, "site_name": "Main OR", "has_image": True,
        "image_sha256": sha_suffix * 64, "file_name": "x.jpg",
        "instrument_barcode": barcode,
        "finding_categories": finding_categories or [],
        "image_view_tags": [{
            "instrument_family": instrument_type, "anatomy_zone": "box lock",
            "image_view": "box lock", "image_sha256": sha_suffix * 64,
        }],
    })
    assert r.status_code == 201, r.text
    return r.json()


class TestClinicalMemoryLookup:
    def test_no_history_returns_404(self):
        r = client.get("/api/clinical-memory?instrument_identity=barcode:no-such-instrument", headers=AUTH_ADMIN)
        assert r.status_code == 404

    def test_requires_authentication(self):
        r = client.get("/api/clinical-memory?instrument_identity=barcode:x")
        assert r.status_code in (401, 403)

    def test_real_instrument_returns_full_memory_context(self):
        for i in range(3):
            _create_inspection("scissors", "V24-BC-A", str(i), finding_categories=["blood"])

        r = client.get("/api/clinical-memory?instrument_identity=barcode:V24-BC-A", headers=AUTH_ADMIN)
        assert r.status_code == 200
        body = r.json()
        for key in (
            "condition_history", "recurring_issues", "predictive_risk", "health_forecast",
            "similar_instruments", "knowledge_articles", "timeline", "memory_recommendation",
        ):
            assert key in body
        assert body["human_review_required"] is True
        assert body["condition_history"]["inspection_count"] == 3

    def test_untracked_instrument_has_no_memory(self):
        insp = _create_inspection("forceps", "", "9")
        db = SessionLocal()
        try:
            from app.db import models
            row = db.query(models.Inspection).filter(models.Inspection.id == insp["id"]).first()
            identity = f"untracked:forceps:{row.id}"
        finally:
            db.close()
        r = client.get(f"/api/clinical-memory?instrument_identity={identity}", headers=AUTH_ADMIN)
        assert r.status_code == 404

    def test_ai_context_expansion_attaches_memory_on_second_inspection(self):
        _create_inspection("scissors", "V24-BC-CTX", "1", finding_categories=["blood"])
        second = _create_inspection("scissors", "V24-BC-CTX", "2", finding_categories=["blood"])
        assert second["analysis"].get("clinical_memory") is not None
        assert second["analysis"]["clinical_memory"]["condition_history"]["inspection_count"] == 1

    def test_learning_dashboard_reachable(self):
        r = client.get("/api/clinical-memory/learning-dashboard", headers=AUTH_ADMIN)
        assert r.status_code == 200
        body = r.json()
        for key in (
            "tracked_instrument_count", "recurring_findings", "repeated_contamination_zones",
            "most_improved_instruments", "most_problematic_instruments", "repeat_repair_candidates",
        ):
            assert key in body


class TestRecurrenceDetection:
    def test_repeated_finding_type_generates_alert(self):
        for i in range(3):
            _create_inspection("scissors", "V24-BC-REC", str(i), finding_categories=["blood"])
        db = SessionLocal()
        try:
            condition = instrument_condition_history(db, "default-tenant", "barcode:V24-BC-REC")
            recurrence = detect_recurring_issues(db, "default-tenant", condition)
        finally:
            db.close()
        assert recurrence["has_recurring_issues"] is True
        blood_alerts = [a for a in recurrence["alerts"] if a.get("finding_type") == "blood"]
        assert blood_alerts and blood_alerts[0]["occurrences"] >= 2

    def test_single_finding_does_not_recur(self):
        _create_inspection("scissors", "V24-BC-SINGLE", "1", finding_categories=["blood"])
        db = SessionLocal()
        try:
            condition = instrument_condition_history(db, "default-tenant", "barcode:V24-BC-SINGLE")
            recurrence = detect_recurring_issues(db, "default-tenant", condition)
        finally:
            db.close()
        # A single inspection can log a finding, but with only one inspection
        # on record it can't have recurred yet.
        assert condition["inspection_count"] == 1
        assert recurrence["has_recurring_issues"] is False
        assert all(count < 2 for count in recurrence["finding_counts"].values())


class TestPredictiveRiskEngine:
    def test_no_repeats_is_low_risk(self):
        condition = {"condition_trend": "stable", "repair_count": 0}
        recurrence = {"finding_counts": {}, "override_count": 0}
        risk = estimate_predictive_risk(condition, recurrence)
        assert risk["overall_risk_level"] == "Low"
        assert risk["human_review_required"] is True

    def test_repeated_contamination_raises_likelihood(self):
        condition = {"condition_trend": "stable", "repair_count": 0}
        recurrence = {"finding_counts": {"blood": 6}, "override_count": 0}
        risk = estimate_predictive_risk(condition, recurrence)
        assert risk["repeat_contamination_likelihood"] in ("High", "Critical")

    def test_repeated_repairs_raise_removal_likelihood(self):
        condition = {"condition_trend": "declining", "repair_count": 3}
        recurrence = {"finding_counts": {}, "override_count": 0}
        risk = estimate_predictive_risk(condition, recurrence)
        assert risk["removal_from_service_likelihood"] == "Critical"
        assert risk["overall_risk_level"] == "Critical"


class TestInstrumentHealthForecast:
    def test_forecast_reflects_repair_trend_and_sample_size(self):
        for i in range(2):
            _create_inspection("scissors", "V24-BC-FORECAST", str(i), finding_categories=["blood"])
        db = SessionLocal()
        try:
            condition = instrument_condition_history(db, "default-tenant", "barcode:V24-BC-FORECAST")
            forecast = forecast_instrument_health(db, "default-tenant", "barcode:V24-BC-FORECAST", condition)
        finally:
            db.close()
        assert forecast["repair_trend"] == "none"
        assert forecast["sample_size"] == 2
        assert forecast["human_review_required"] is True

    def test_small_sample_confidence_interval_is_wide_or_null(self):
        _create_inspection("scissors", "V24-BC-SMALL", "1", finding_categories=["blood"])
        db = SessionLocal()
        try:
            condition = instrument_condition_history(db, "default-tenant", "barcode:V24-BC-SMALL")
            forecast = forecast_instrument_health(db, "default-tenant", "barcode:V24-BC-SMALL", condition)
        finally:
            db.close()
        ci = forecast["confidence_interval"]
        if ci is not None:
            assert (ci["high"] - ci["low"]) >= 20


class TestSimilarInstrumentSearch:
    def test_finds_other_instrument_sharing_type_and_finding(self):
        for i in range(2):
            _create_inspection("scissors", "V24-BC-SIM-1", str(i), finding_categories=["blood"])
        _create_inspection("scissors", "V24-BC-SIM-2", "5", finding_categories=["blood"])

        # A generous limit — other tests in this module create their own
        # scissors/blood instruments in the same shared tenant, and this
        # assertion only cares that SIM-2 is *found*, not that it's top-ranked.
        db = SessionLocal()
        try:
            results = find_similar_instruments(db, "default-tenant", instrument_identity="barcode:V24-BC-SIM-1", limit=50)
        finally:
            db.close()
        assert any(r["instrument_identity"] == "barcode:V24-BC-SIM-2" for r in results)
        match = next(r for r in results if r["instrument_identity"] == "barcode:V24-BC-SIM-2")
        assert match["similarity_score"] > 0
        assert "blood" in match["shared_finding_types"]

    def test_untracked_instruments_excluded(self):
        db = SessionLocal()
        try:
            results = find_similar_instruments(db, "default-tenant", instrument_identity="barcode:V24-BC-SIM-1", limit=50)
        finally:
            db.close()
        assert all(not r["instrument_identity"].startswith("untracked:") for r in results)

    def test_no_history_returns_empty_list(self):
        db = SessionLocal()
        try:
            results = find_similar_instruments(db, "default-tenant", instrument_identity="barcode:no-such-thing")
        finally:
            db.close()
        assert results == []


class TestMemoryTimeline:
    def test_timeline_alternates_inspection_finding_repair_note(self):
        condition = {
            "history": [
                {
                    "inspection_id": 1, "date": "2026-01-01T00:00:00", "disposition": "REPROCESS",
                    "cleaning_findings": ["blood"], "damage_findings": [], "repair_flag": False,
                    "supervisor_comments": ["looked fine overall"],
                },
                {
                    "inspection_id": 2, "date": "2026-02-01T00:00:00", "disposition": "REMOVE FROM SERVICE",
                    "cleaning_findings": [], "damage_findings": ["crack"], "repair_flag": True,
                    "supervisor_comments": [],
                },
            ],
        }
        timeline = build_memory_timeline(condition)
        types = [e["type"] for e in timeline]
        assert types == ["inspection", "finding", "supervisor_note", "inspection", "finding", "repair", "current"]

    def test_empty_history_still_has_current_marker(self):
        timeline = build_memory_timeline({"history": []})
        assert timeline == [{"type": "current", "date": None}]


class TestMemoryDrivenRecommendation:
    def test_recommendation_names_recurring_finding_and_zone(self):
        for i in range(3):
            _create_inspection("scissors", "V24-BC-RECO", str(i), finding_categories=["blood"])
        db = SessionLocal()
        try:
            memory = get_clinical_memory(db, "default-tenant", "barcode:V24-BC-RECO")
        finally:
            db.close()
        rec = memory["memory_recommendation"]
        assert rec is not None
        assert rec["finding_type"] == "blood"
        assert rec["occurrences"] >= 3
        assert "blood" in rec["message"].lower()
        assert "recommend" in rec["message"].lower()
        assert rec["human_review_required"] is True

    def test_no_recurrence_means_no_recommendation(self):
        db = SessionLocal()
        try:
            condition = {"history": [{"inspection_id": 1}], "inspection_count": 1}
            recurrence = {"has_recurring_issues": False, "finding_counts": {}}
            rec = build_memory_recommendation(db, "default-tenant", condition, recurrence)
        finally:
            db.close()
        assert rec is None


class TestKnowledgeArticleEnrichment:
    def test_applicable_article_surfaced_in_memory(self):
        db = SessionLocal()
        try:
            db.add(KnowledgeArticle(
                tenant_id="default-tenant", category="teaching_point", title="Box lock blood residue",
                body="Check the box lock carefully.", approval_status=APPROVED,
                applicable_instruments=json.dumps(["scissors"]),
            ))
            db.commit()
        finally:
            db.close()

        for i in range(2):
            _create_inspection("scissors", "V24-BC-KA", str(i), finding_categories=["blood"])

        r = client.get("/api/clinical-memory?instrument_identity=barcode:V24-BC-KA", headers=AUTH_ADMIN)
        assert r.status_code == 200
        titles = [a["title"] for a in r.json()["knowledge_articles"]]
        assert "Box lock blood residue" in titles
