"""Regression tests for Codex-review findings on PR #70's pilot-validation
subsystem (app/services/pilot_validation_service.py, app/routes/
pilot_validation.py, app/agents/supervisor_agent.py):

1. The primary one-form supervisor-review UI never sent `finding_correct`,
   so every case created through it was inconclusive — the label is now
   inferred from `agreement` as a fallback.
2. A supervisor-confirmed miss (AI said nothing, supervisor disagrees) with
   no explicit corrected finding type no longer collapses to finding_type
   "none" / is_critical_finding=False — it's flagged as a critical,
   unspecified finding instead of disappearing from safety metrics.
3. `ai_confidence` is normalized from Inspection.confidence's 0-100 scale to
   the 0-1 scale pilot cases/calibration buckets use.
4. POST /api/pilot-validation/cases honors the request tenant header instead
   of always falling back to "default-tenant".
5. SupervisorAgent scopes its SupervisorReview/PilotValidationCase lookups by
   tenant_id so a foreign tenant's case can't leak into this inspection's
   CIOS/agent context.
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.db import models
from app.db.session import SessionLocal
from app.models.pilot_validation import PilotValidationCase

client = TestClient(app)
AUTH_ADMIN = {"Authorization": "Bearer dev-token"}
SHA = "beadfeed" + "0" * 56


def _make_inspection(instrument_type="rigid scope", detected_issue="unknown", risk_score=20, confidence=80.0) -> int:
    db = SessionLocal()
    try:
        insp = models.Inspection(
            tenant_id="default-tenant", file_name="f.jpg", instrument_type=instrument_type,
            detected_issue=detected_issue, risk_score=risk_score, confidence=confidence,
            score_status="scored", has_image=True, image_sha256=SHA,
            recommended_action="MONITOR",
        )
        db.add(insp)
        db.commit()
        db.refresh(insp)
        return insp.id
    finally:
        db.close()


def _latest_case(inspection_id: int) -> PilotValidationCase:
    db = SessionLocal()
    try:
        return (
            db.query(PilotValidationCase)
            .filter(PilotValidationCase.inspection_id == inspection_id)
            .order_by(PilotValidationCase.id.desc())
            .first()
        )
    finally:
        db.close()


class TestLabelInferredFromAgreement:
    def test_disagree_without_finding_correct_yields_conclusive_label(self):
        iid = _make_inspection(detected_issue="unknown")
        r = client.post(
            f"/api/inspections/{iid}/supervisor-review",
            headers=AUTH_ADMIN,
            json={"agreement": "disagree", "rationale": "Missed a finding under magnification."},
        )
        assert r.status_code == 201, r.text
        case = _latest_case(iid)
        assert case.ground_truth_label != "inconclusive"

    def test_agree_without_finding_correct_yields_conclusive_label(self):
        iid = _make_inspection(detected_issue="unknown")
        r = client.post(
            f"/api/inspections/{iid}/supervisor-review",
            headers=AUTH_ADMIN,
            json={"agreement": "agree"},
        )
        assert r.status_code == 201, r.text
        case = _latest_case(iid)
        assert case.ground_truth_label == "tn"  # AI said nothing, supervisor agrees

    def test_partially_agree_without_finding_correct_stays_inconclusive(self):
        iid = _make_inspection(detected_issue="unknown")
        r = client.post(
            f"/api/inspections/{iid}/supervisor-review",
            headers=AUTH_ADMIN,
            json={"agreement": "partially_agree", "rationale": "Partly right."},
        )
        assert r.status_code == 201, r.text
        case = _latest_case(iid)
        assert case.ground_truth_label == "inconclusive"


class TestCriticalMissPreservesFindingType:
    def test_unspecified_miss_flagged_critical_not_none(self):
        iid = _make_inspection(detected_issue="unknown")
        r = client.post(
            f"/api/inspections/{iid}/supervisor-review",
            headers=AUTH_ADMIN,
            json={
                "agreement": "disagree",
                "rationale": "Supervisor found blood the AI missed.",
                "finding_correct": False,
            },
        )
        assert r.status_code == 201, r.text
        case = _latest_case(iid)
        assert case.finding_type != "none"
        assert case.is_critical_finding is True
        assert case.ground_truth_label == "fn"

    def test_explicit_corrected_finding_type_is_used(self):
        iid = _make_inspection(detected_issue="unknown")
        r = client.post(
            f"/api/inspections/{iid}/supervisor-review",
            headers=AUTH_ADMIN,
            json={
                "agreement": "disagree",
                "rationale": "Supervisor found blood the AI missed.",
                "finding_correct": False,
                "corrected_finding_type": "blood",
            },
        )
        assert r.status_code == 201, r.text
        case = _latest_case(iid)
        assert case.finding_type == "blood"
        assert case.is_critical_finding is True


class TestConfidenceNormalized:
    def test_ai_confidence_normalized_to_0_1(self):
        iid = _make_inspection(detected_issue="blood", confidence=80.0)
        r = client.post(
            f"/api/inspections/{iid}/supervisor-review",
            headers=AUTH_ADMIN,
            json={"agreement": "agree"},
        )
        assert r.status_code == 201, r.text
        case = _latest_case(iid)
        assert case.ai_confidence == 0.8


class TestPilotCaseRouteHonorsTenant:
    def test_case_created_with_request_tenant(self):
        r = client.post(
            "/api/pilot-validation/cases",
            headers={**AUTH_ADMIN, "X-LumenAI-Tenant-Id": "tenant-b"},
            json={
                "instrument_family": "hemostat",
                "manufacturer": "Acme",
                "model": "AS-100",
                "anatomy_zone": "box locks",
                "baseline_source": "vendor_baseline",
                "has_baseline": True,
                "finding_type": "blood",
                "severity": "critical",
                "ai_prediction": True,
                "ai_confidence": 0.9,
                "ai_recommended_disposition": "reprocess",
                "supervisor_finding": True,
                "supervisor_zone_correction": "",
                "reviewer_name": "J. Rivera",
                "reviewer_rationale": "Confirmed residue.",
                "final_disposition": "reprocess",
            },
        )
        assert r.status_code == 201, r.text
        assert r.json()["tenant_id"] == "tenant-b"


class TestSupervisorAgentTenantScoping:
    def test_foreign_tenant_case_does_not_leak(self):
        from app.agents.supervisor_agent import SupervisorAgent

        db = SessionLocal()
        try:
            insp = models.Inspection(
                tenant_id="tenant-a", file_name="f.jpg", instrument_type="rigid scope",
                risk_score=20, score_status="scored", has_image=True, image_sha256=SHA,
                recommended_action="MONITOR",
            )
            db.add(insp)
            db.commit()
            db.refresh(insp)
            iid = insp.id

            # A foreign tenant's case happens to reference the same inspection_id.
            foreign_case = PilotValidationCase(
                tenant_id="tenant-b", inspection_id=iid,
                ground_truth_label="fp", is_critical_finding=True,
            )
            db.add(foreign_case)
            db.commit()
        finally:
            db.close()

        agent = SupervisorAgent()
        db = SessionLocal()
        try:
            ctx = agent.run(db, iid, "tenant-a")
        finally:
            db.close()

        assert ctx.review_exists is False
        assert ctx.training_label_created is False
        assert ctx.ground_truth_label is None
