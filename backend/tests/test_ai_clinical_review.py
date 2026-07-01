"""AI Clinical Review, Evidence Strength, Baseline Difference, Supervisor Notes."""
from fastapi.testclient import TestClient

from app.main import app
from app.db.session import SessionLocal
from app.models.baseline_library import BaselineLibraryEntry
from app.services.baseline_comparison_scoring_service import analyze_inspection

client = TestClient(app)
AUTH_ADMIN = {"Authorization": "Bearer dev-token"}
AUTH_MGR = {"Authorization": "Bearer manager-token"}
AUTH_OPERATOR = {"Authorization": "Bearer operator-token"}
SHA = "a1b2c3d4" + "0" * 56


def _baseline(itype: str) -> None:
    db = SessionLocal()
    try:
        db.query(BaselineLibraryEntry).filter(
            BaselineLibraryEntry.instrument_category == itype
        ).delete()
        db.add(BaselineLibraryEntry(
            udi=f"acr-{itype}", instrument_category=itype, manufacturer_name="M",
            model_name="X", baseline_type="manufacturer", approval_status="approved",
        ))
        db.commit()
    finally:
        db.close()


def _analyze(itype, declared=None):
    _baseline(itype)
    db = SessionLocal()
    try:
        return analyze_inspection(
            db, instrument_type=itype, tenant_id="default-tenant",
            has_image=True, image_sha256=SHA, declared_findings=declared,
        )
    finally:
        db.close()


class TestAIClinicalReview:
    def test_pass_reasoning_and_interpretation(self):
        cd = _analyze("retractor")["clinical_decision"]
        review = cd["ai_clinical_review"]
        assert review["outcome"] in (
            "PASS", "MONITOR", "SUPERVISOR REVIEW", "REPROCESS", "REMOVE FROM SERVICE"
        )
        # Reasoning is grounded (baseline line) and interpretation is non-generic.
        assert any("matched at" in ln for ln in review["reasoning"])
        assert review["interpretation"]

    def test_reprocess_outcome_on_blood(self):
        cd = _analyze("scissors", declared=["blood"])["clinical_decision"]
        assert cd["ai_clinical_review"]["outcome"] in ("REPROCESS", "REMOVE FROM SERVICE")
        assert cd["recommendation"]["action_text"]

    def test_five_action_texts(self):
        from app.services.baseline_comparison_scoring_service import _ACTION_TEXT
        assert set(_ACTION_TEXT) == {
            "PASS", "MONITOR", "SUPERVISOR REVIEW", "REPROCESS", "REMOVE FROM SERVICE"
        }


class TestEvidenceStrength:
    def test_strong_when_match_and_confidence_high(self):
        from app.services.baseline_comparison_scoring_service import evidence_strength
        es = evidence_strength({"baseline_match_score": 0.95, "confidence": 0.90})
        assert es["level"] == "Strong"
        assert es["stars"] == 5

    def test_moderate_band(self):
        from app.services.baseline_comparison_scoring_service import evidence_strength
        es = evidence_strength({"baseline_match_score": 0.80, "confidence": 0.60})
        assert es["level"] == "Moderate"

    def test_limited_when_baseline_missing(self):
        from app.services.baseline_comparison_scoring_service import evidence_strength
        es = evidence_strength({"baseline_match_score": None, "confidence": None})
        assert es["level"] == "Limited"
        assert es["stars"] == 1

    def test_evidence_strength_in_clinical_decision(self):
        cd = _analyze("scissors")["clinical_decision"]
        assert cd["evidence_strength"]["level"] in ("Strong", "Moderate", "Limited")


class TestBaselineDifference:
    def test_difference_section_present(self):
        cd = _analyze("forceps")["clinical_decision"]
        bd = cd["baseline_difference"]
        assert bd["baseline_match_pct"] is not None
        assert bd["differences"]
        assert "future" in bd["localization_note"].lower()

    def test_no_fabricated_localization(self):
        cd = _analyze("forceps")["clinical_decision"]
        # No bounding-box / heatmap fabrication — only plain observations.
        assert bd_ok(cd["baseline_difference"]["differences"])


def bd_ok(diffs):
    joined = " ".join(diffs).lower()
    return "bounding box" not in joined and "heatmap" not in joined


class TestAuditTrail:
    def test_audit_has_model_and_baseline_version(self):
        cd = _analyze("scissors")["clinical_decision"]
        audit = cd["audit"]
        assert audit["model_version"]
        assert "baseline_version" in audit
        assert "dataset_version" in audit
        assert "evidence_strength" in audit
        assert "supervisor_agreement" in audit


class TestSupervisorReviewAPI:
    def _create(self, itype):
        _baseline(itype)
        r = client.post("/api/inspections", json={
            "instrument_type": itype, "site_name": "Mercy",
            "has_image": True, "image_sha256": SHA, "file_name": "x.jpg",
        }, headers=AUTH_OPERATOR)
        assert r.status_code == 201, r.text
        return r.json()["id"]

    def test_operator_cannot_submit(self):
        iid = self._create("scissors")
        r = client.post(f"/api/inspections/{iid}/supervisor-review",
                        json={"agreement": "agree"}, headers=AUTH_OPERATOR)
        assert r.status_code == 403

    def test_manager_can_agree(self):
        iid = self._create("scissors")
        r = client.post(f"/api/inspections/{iid}/supervisor-review",
                        json={"agreement": "agree"}, headers=AUTH_MGR)
        assert r.status_code == 201, r.text
        assert r.json()["agreement"] == "agree"

    def test_disagree_requires_comment(self):
        iid = self._create("scissors")
        r = client.post(f"/api/inspections/{iid}/supervisor-review",
                        json={"agreement": "disagree", "rationale": ""}, headers=AUTH_MGR)
        assert r.status_code == 422

    def test_disagree_with_comment_ok(self):
        iid = self._create("scissors")
        r = client.post(f"/api/inspections/{iid}/supervisor-review",
                        json={"agreement": "disagree", "rationale": "Debris still present in hinge."},
                        headers=AUTH_MGR)
        assert r.status_code == 201

    def test_override_requires_comment(self):
        iid = self._create("scissors")
        r = client.post(f"/api/inspections/{iid}/supervisor-review",
                        json={"agreement": "agree", "override_action": "reprocess"},
                        headers=AUTH_MGR)
        assert r.status_code == 422

    def test_invalid_agreement_rejected(self):
        iid = self._create("scissors")
        r = client.post(f"/api/inspections/{iid}/supervisor-review",
                        json={"agreement": "maybe"}, headers=AUTH_MGR)
        assert r.status_code == 422

    def test_performance_summary_counts_reviews(self):
        iid = self._create("forceps")
        client.post(f"/api/inspections/{iid}/supervisor-review",
                    json={"agreement": "agree"}, headers=AUTH_MGR)
        r = client.get("/api/model-performance/ai-summary", headers=AUTH_MGR)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["supervisor_reviews"] >= 1
        assert body["supervisor_agreement_rate"] is not None
        # No fabricated production ground-truth.
        assert body["false_positive_count"] is None

    def test_performance_summary_operator_blocked(self):
        r = client.get("/api/model-performance/ai-summary", headers=AUTH_OPERATOR)
        assert r.status_code == 403
