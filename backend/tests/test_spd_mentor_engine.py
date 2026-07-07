"""v1.4 — SPD Mentor Engine: corrective actions, anatomy coaching, confidence
coaching, training mode, education library, and competency support."""
from fastapi.testclient import TestClient

from app.db.session import SessionLocal
from app.models.baseline_library import BaselineLibraryEntry
from app.services.baseline_comparison_scoring_service import analyze_inspection
from app.services.education_library import get_article, list_articles
from app.services.spd_mentor_engine import (
    confidence_coaching,
    corrective_action_chain,
    education_card,
)
from app.main import app

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
            udi=f"sme-{itype}", instrument_category=itype, manufacturer_name="M",
            model_name="X", baseline_type="manufacturer", approval_status="approved",
        ))
        db.commit()
    finally:
        db.close()


def _analyze(itype, declared=None, training_mode=False):
    _baseline(itype)
    db = SessionLocal()
    try:
        return analyze_inspection(
            db, instrument_type=itype, tenant_id="default-tenant",
            has_image=True, image_sha256=SHA, declared_findings=declared,
            training_mode=training_mode,
        )
    finally:
        db.close()


class TestCorrectiveActionRecommendations:
    def test_blood_recommendation_generated(self):
        cd = _analyze("scissors", declared=["blood"])["clinical_decision"]
        actions = cd["spd_mentor"]["corrective_actions"]
        blood = next((a for a in actions if a["finding"] == "blood"), None)
        assert blood is not None
        assert blood["steps"] == corrective_action_chain("blood")
        assert "Supervisor verification." in blood["steps"]

    def test_rust_generates_repair_remove_recommendation(self):
        # "rust" is not a declarable category in the scoring engine (only its
        # sibling "corrosion" is) — assert the chain directly, as the education
        # card/library tests already do for other pure-function lookups.
        steps = corrective_action_chain("rust")
        assert "Remove from service." in steps
        assert "Evaluate for repair." in steps

    def test_corrosion_recommendation_generated(self):
        cd = _analyze("scissors", declared=["corrosion"])["clinical_decision"]
        actions = cd["spd_mentor"]["corrective_actions"]
        corrosion = next((a for a in actions if a["finding"] == "corrosion"), None)
        assert corrosion is not None
        assert "Remove from service." in corrosion["steps"]
        assert "Evaluate for repair." in corrosion["steps"]

    def test_crack_generates_remove_from_service_recommendation(self):
        cd = _analyze("forceps", declared=["crack"])["clinical_decision"]
        actions = cd["spd_mentor"]["corrective_actions"]
        crack = next((a for a in actions if a["finding"] == "crack"), None)
        assert crack is not None
        assert crack["steps"][0] == "Remove from service immediately."
        assert "Notify supervisor." in crack["steps"]


class TestAnatomyAwareCoaching:
    def test_kerrison_serrations_coaching(self):
        cd = _analyze("kerrison_rongeur")["clinical_decision"]
        coaching = cd["spd_mentor"]["anatomy_coaching"]
        assert any("Kerrison jaw serrations are high-retention anatomy zones." == c for c in coaching)

    def test_rigid_scope_oring_coaching(self):
        cd = _analyze("rigid_scope")["clinical_decision"]
        coaching = cd["spd_mentor"]["anatomy_coaching"]
        assert any("O-ring" in c for c in coaching)

    def test_drill_bit_flutes_coaching(self):
        cd = _analyze("drill_bit")["clinical_decision"]
        coaching = cd["spd_mentor"]["anatomy_coaching"]
        assert any("flutes" in c.lower() for c in coaching)

    def test_needle_holder_box_lock_coaching(self):
        cd = _analyze("needle_holder")["clinical_decision"]
        coaching = cd["spd_mentor"]["anatomy_coaching"]
        assert any("box lock" in c.lower() for c in coaching)


class TestConfidenceCoaching:
    def test_low_confidence_coaching_displayed(self):
        result = {
            "confidence": 0.5,
            "inspection_coverage": {"assessed": True, "overall_coverage": 40},
        }
        coaching = confidence_coaching(result)
        assert coaching is not None
        assert "incomplete" in coaching["message"].lower()
        assert "Request supervisor review." in coaching["suggestions"]

    def test_high_confidence_full_coverage_no_coaching(self):
        result = {
            "confidence": 0.95,
            "inspection_coverage": {"assessed": True, "overall_coverage": 100},
        }
        assert confidence_coaching(result) is None

    def test_coverage_not_assessed_triggers_coaching(self):
        result = {"confidence": 0.9, "inspection_coverage": {"assessed": False}}
        coaching = confidence_coaching(result)
        assert coaching is not None
        assert "Capture additional images." in coaching["suggestions"]


class TestTrainingMode:
    def test_training_mode_expands_explanations(self):
        cd_off = _analyze("scissors", declared=["blood"], training_mode=False)["clinical_decision"]
        cd_on = _analyze("scissors", declared=["blood"], training_mode=True)["clinical_decision"]

        assert "expanded_explanations" not in cd_off["spd_mentor"]
        assert cd_off["spd_mentor"]["training_mode"] is False

        mentor_on = cd_on["spd_mentor"]
        assert mentor_on["training_mode"] is True
        expanded = mentor_on["expanded_explanations"]
        assert expanded["every_finding"]
        assert expanded["anatomy_explained"]
        assert expanded["recommendation_explained"]["disposition"]
        assert any(t["term"] == "IFU" for t in expanded["terminology"])


class TestEducationCards:
    def test_education_card_rendered_correctly(self):
        card = education_card("blood")
        assert card["finding"] == "blood"
        assert card["clinical_significance"]
        assert card["recommended_practice"]
        assert "AAMI ST79" in card["reference"]

    def test_clinical_decision_includes_education_cards(self):
        cd = _analyze("scissors", declared=["blood"])["clinical_decision"]
        cards = cd["spd_mentor"]["education_cards"]
        assert any(c["finding"] == "blood" for c in cards)


class TestEducationLibrary:
    def test_library_has_all_twelve_categories(self):
        articles = list_articles()
        assert len(articles) == 12

    def test_article_fields_present(self):
        article = get_article("rust")
        for field in (
            "definition", "clinical_importance", "typical_anatomy_locations",
            "inspection_tips", "cleaning_considerations", "corrective_actions", "reference",
        ):
            assert article[field], f"missing/empty {field}"

    def test_unknown_finding_type_returns_none(self):
        assert get_article("not_a_real_finding") is None


class TestMentorDisclaimer:
    def test_disclaimer_never_replaces_supervisor_judgment(self):
        cd = _analyze("scissors")["clinical_decision"]
        assert "does not replace" in cd["spd_mentor"]["disclaimer"].lower()


class TestSupervisorCoachingDashboard:
    def _create(self, itype):
        _baseline(itype)
        r = client.post("/api/inspections", json={
            "instrument_type": itype, "site_name": "Mercy",
            "has_image": True, "image_sha256": SHA, "file_name": "x.jpg",
        }, headers=AUTH_OPERATOR)
        assert r.status_code == 201, r.text
        return r.json()["id"]

    def test_coaching_queue_lists_inspection(self):
        iid = self._create("scissors")
        r = client.get("/api/mentor/coaching-queue", headers=AUTH_MGR)
        assert r.status_code == 200
        ids = [row["inspection_id"] for row in r.json()["queue"]]
        assert iid in ids

    def test_submit_coaching_review(self):
        iid = self._create("forceps")
        r = client.post(
            f"/api/inspections/{iid}/coaching-review",
            json={"approved": True, "educational_comment": "Good catch on the box lock."},
            headers=AUTH_MGR,
        )
        assert r.status_code == 201, r.text
        assert r.json()["educational_comment"] == "Good catch on the box lock."

    def test_operator_cannot_submit_coaching_review(self):
        iid = self._create("forceps")
        r = client.post(
            f"/api/inspections/{iid}/coaching-review",
            json={"approved": True}, headers=AUTH_OPERATOR,
        )
        assert r.status_code == 403

    def test_coaching_effectiveness_reflects_reviews(self):
        iid = self._create("needle_holder")
        client.post(
            f"/api/inspections/{iid}/coaching-review",
            json={"approved": True}, headers=AUTH_MGR,
        )
        r = client.get("/api/mentor/coaching-effectiveness", headers=AUTH_MGR)
        assert r.status_code == 200
        assert r.json()["total_reviews"] >= 1


class TestCompetencySupport:
    def _create_as_operator(self, itype):
        _baseline(itype)
        r = client.post("/api/inspections", json={
            "instrument_type": itype, "site_name": "Mercy",
            "has_image": True, "image_sha256": SHA, "file_name": "x.jpg",
        }, headers=AUTH_OPERATOR)
        assert r.status_code == 201, r.text
        return r.json()["id"]

    def test_competency_summary_updates_after_supervisor_review(self):
        iid = self._create_as_operator("scissors")

        before = client.get("/api/mentor/competency/operator@local.dev", headers=AUTH_MGR)
        assert before.status_code == 200
        before_reviewed = before.json()["findings_reviewed"]
        before_corrections = before.json()["supervisor_corrections"]

        r = client.post(
            f"/api/inspections/{iid}/supervisor-review",
            json={
                "agreement": "disagree",
                "rationale": "Debris still present in hinge.",
                "finding_type": "debris",
            },
            headers=AUTH_MGR,
        )
        assert r.status_code == 201, r.text

        after = client.get("/api/mentor/competency/operator@local.dev", headers=AUTH_MGR)
        assert after.status_code == 200
        assert after.json()["findings_reviewed"] == before_reviewed + 1
        assert after.json()["supervisor_corrections"] == before_corrections + 1

    def test_operator_can_view_own_summary_only(self):
        r = client.get("/api/mentor/competency/operator@local.dev", headers=AUTH_OPERATOR)
        assert r.status_code == 200
        r2 = client.get("/api/mentor/competency/spd_manager@local.dev", headers=AUTH_OPERATOR)
        assert r2.status_code == 403

    def test_education_completion_recorded(self):
        r = client.post("/api/mentor/education/blood/complete", headers=AUTH_OPERATOR)
        assert r.status_code == 201, r.text
        assert "blood" in r.json()["education_completed"]


class TestInspectionMentorEndpoint:
    def test_rederive_mentor_for_past_inspection(self):
        _baseline("scissors")
        r = client.post("/api/inspections", json={
            "instrument_type": "scissors", "site_name": "Mercy",
            "has_image": True, "image_sha256": SHA, "file_name": "x.jpg",
        }, headers=AUTH_OPERATOR)
        iid = r.json()["id"]

        r = client.get(f"/api/inspections/{iid}/mentor?training_mode=true", headers=AUTH_ADMIN)
        assert r.status_code == 200
        assert r.json()["training_mode"] is True
        assert "expanded_explanations" in r.json()
