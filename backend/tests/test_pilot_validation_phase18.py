"""Phase 18 — Real-world pilot validation & clinical performance study.

Covers ground-truth labeling from supervisor reviews, clinical metrics
(FP/FN/agreement), zone performance, the validation dashboard, the safety review
queue, and the validation report (dataset/model version).
"""
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.main import app
from app.db.session import SessionLocal
from app.db import models
from app.services.ml.ground_truth import (
    classify_ground_truth, FALSE_NEGATIVE, FALSE_POSITIVE, TRUE_POSITIVE,
)
from app.services.ml import pilot_validation as pv

client = TestClient(app)
AUTH = {"Authorization": "Bearer dev-token"}
AUTH_VIEWER = {"Authorization": "Bearer viewer-token"}


def _row(**kw):
    """A lightweight stand-in for a SupervisorReview row for pure-service tests."""
    base = dict(
        id=1, inspection_id=1, ground_truth="", agreement="agree", override_action="",
        finding_type="", ai_zone="", corrected_zone="", instrument_family="",
        ai_confidence=None, supervisor_finding_present=None,
    )
    base.update(kw)
    return SimpleNamespace(**base)


# ── Ground truth ──────────────────────────────────────────────────────────────

class TestGroundTruth:
    def test_labels(self):
        assert classify_ground_truth(True, True) == TRUE_POSITIVE
        assert classify_ground_truth(True, False) == FALSE_POSITIVE
        assert classify_ground_truth(False, True) == FALSE_NEGATIVE
        assert classify_ground_truth(None, True) == "inconclusive"

    def test_supervisor_review_creates_ground_truth_label(self):
        db = SessionLocal()
        try:
            insp = models.Inspection(
                tenant_id="default-tenant", file_name="f.jpg", instrument_type="rigid_scope",
                risk_score=30, score_status="scored", has_image=True, recommended_action="REPROCESS",
            )
            db.add(insp)
            db.commit()
            db.refresh(insp)
            iid = insp.id
        finally:
            db.close()
        r = client.post(f"/api/inspections/{iid}/supervisor-review", headers=AUTH, json={
            "agreement": "agree", "ai_finding_present": True, "supervisor_finding_present": True,
            "finding_type": "blood", "ai_zone": "o-ring area", "instrument_family": "rigid_scope",
            "ai_confidence": 0.9,
        })
        assert r.status_code == 201, r.text
        assert r.json()["ground_truth"] == TRUE_POSITIVE


# ── Metrics ───────────────────────────────────────────────────────────────────

class TestClinicalMetrics:
    def test_false_positive_and_negative_counts(self):
        rows = [
            _row(ground_truth=TRUE_POSITIVE),
            _row(ground_truth=FALSE_POSITIVE, agreement="disagree", override_action="reprocess"),
            _row(ground_truth=FALSE_NEGATIVE, agreement="disagree"),
        ]
        m = pv.clinical_metrics(rows)
        assert m["counts"][FALSE_POSITIVE] == 1
        assert m["counts"][FALSE_NEGATIVE] == 1
        # recall = TP/(TP+FN) = 1/2
        assert m["recall"] == 0.5

    def test_agreement_rate(self):
        rows = [_row(agreement="agree"), _row(agreement="agree"), _row(agreement="disagree")]
        m = pv.clinical_metrics(rows)
        assert m["supervisor_agreement_rate"] == round(2 / 3, 4)

    def test_blood_false_negative_rate(self):
        rows = [
            _row(finding_type="blood", supervisor_finding_present=True, ground_truth=FALSE_NEGATIVE),
            _row(finding_type="blood", supervisor_finding_present=True, ground_truth=TRUE_POSITIVE),
        ]
        sm = pv.safety_metrics(rows)
        assert sm["blood_false_negative_rate"] == 0.5

    def test_zone_performance_calculated(self):
        rows = [
            _row(corrected_zone="serrations", ground_truth=FALSE_NEGATIVE, ai_confidence=0.4),
            _row(corrected_zone="serrations", ground_truth=TRUE_POSITIVE, ai_confidence=0.8),
            _row(corrected_zone="hinge", ground_truth=TRUE_POSITIVE, override_action="reprocess"),
        ]
        zp = pv.zone_performance(rows)
        assert zp["by_zone"]["serrations"]["missed"] == 1
        assert zp["by_zone"]["serrations"]["n"] == 2
        assert any(z["zone"] == "serrations" for z in zp["most_common_missed_zones"])
        assert any(z["zone"] == "hinge" for z in zp["highest_override_zones"])


# ── Safety queue ──────────────────────────────────────────────────────────────

class TestSafetyQueue:
    def test_queue_includes_critical_missed_findings(self):
        rows = [
            _row(id=10, finding_type="tissue", supervisor_finding_present=True,
                 ground_truth=FALSE_NEGATIVE, ai_confidence=0.9, agreement="disagree"),
            _row(id=11, ground_truth=TRUE_POSITIVE, agreement="agree"),  # not queued
        ]
        q = pv.safety_review_queue(rows)
        assert len(q) == 1
        assert q[0]["review_id"] == 10
        assert "false_negative" in q[0]["reasons"]


# ── Dashboard + report API ────────────────────────────────────────────────────

class TestPilotValidationApi:
    def _seed(self, **kw):
        db = SessionLocal()
        try:
            insp = models.Inspection(
                tenant_id="default-tenant", file_name="f.jpg", instrument_type="rigid_scope",
                risk_score=30, score_status="scored", has_image=True, recommended_action="REPROCESS",
            )
            db.add(insp)
            db.commit()
            db.refresh(insp)
            iid = insp.id
        finally:
            db.close()
        payload = {"agreement": "agree", "ai_finding_present": True,
                   "supervisor_finding_present": True, "finding_type": "blood",
                   "instrument_family": "rigid_scope", "ai_confidence": 0.9}
        payload.update(kw)
        return client.post(f"/api/inspections/{iid}/supervisor-review", headers=AUTH, json=payload)

    def test_dashboard_returns_required_metrics(self):
        self._seed()
        d = client.get("/api/pilot-validation/dashboard", headers=AUTH)
        assert d.status_code == 200, d.text
        body = d.json()
        for key in (
            "total_inspections_reviewed", "ai_supervisor_agreement_rate",
            "false_positives", "false_negatives", "high_risk_findings_detected",
            "inconclusive_cases", "safety_metrics", "zone_performance",
            "instrument_family_performance",
        ):
            assert key in body

    def test_report_includes_dataset_and_model_version(self):
        self._seed()
        r = client.get(
            "/api/pilot-validation/report?dataset_version=ds-test-1&model_version=1.2&model_id=m-x",
            headers=AUTH,
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["dataset_version"] == "ds-test-1"
        assert body["model_version"] == "1.2"
        assert "results" in body and "go_no_go" in body

    def test_safety_queue_endpoint(self):
        self._seed(agreement="disagree", rationale="AI missed tissue in the lumen.",
                   ai_finding_present=False, supervisor_finding_present=True,
                   finding_type="tissue", ai_confidence=0.9)
        q = client.get("/api/pilot-validation/safety-queue", headers=AUTH)
        assert q.status_code == 200
        assert q.json()["count"] >= 1

    def test_viewer_cannot_access_safety_queue(self):
        assert client.get("/api/pilot-validation/safety-queue", headers=AUTH_VIEWER).status_code == 403
