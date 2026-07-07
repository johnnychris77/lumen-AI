"""v1.8 — Institutional Knowledge & Clinical Memory."""
from fastapi.testclient import TestClient

from app.db.session import SessionLocal
from app.main import app
from app.models.baseline_library import BaselineLibraryEntry
from app.models.knowledge import APPROVED, PENDING_REVIEW

client = TestClient(app)
AUTH_ADMIN = {"Authorization": "Bearer dev-token"}
AUTH_MGR = {"Authorization": "Bearer manager-token"}
AUTH_OPERATOR = {"Authorization": "Bearer operator-token"}
SHA = "a1b2c3d4" + "0" * 56
TENANT = "default-tenant"


def _baseline(itype: str) -> None:
    db = SessionLocal()
    try:
        db.query(BaselineLibraryEntry).filter(BaselineLibraryEntry.instrument_category == itype).delete()
        db.add(BaselineLibraryEntry(
            udi=f"ik-{itype}", instrument_category=itype, manufacturer_name="M",
            model_name="X", baseline_type="manufacturer", approval_status="approved",
        ))
        db.commit()
    finally:
        db.close()


def _create(itype, declared=None, headers=None):
    _baseline(itype)
    r = client.post("/api/inspections", json={
        "instrument_type": itype, "site_name": "Mercy",
        "has_image": True, "image_sha256": SHA, "file_name": "x.jpg",
        "finding_categories": declared or [],
    }, headers=headers or AUTH_OPERATOR)
    assert r.status_code == 201, r.text
    return r.json()["id"]


class TestKnowledgeArticleCreation:
    def test_create_article_starts_pending_review(self):
        r = client.post("/api/knowledge/articles", json={
            "category": "best_practice", "title": "Always brush serrations twice",
            "body": "Kerrison serrations trap blood; brush from both directions.",
            "applicable_instruments": ["kerrison_rongeur"], "applicable_findings": ["blood"],
        }, headers=AUTH_OPERATOR)
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["approval_status"] == PENDING_REVIEW
        assert body["version"] == 1
        assert body["author"]

    def test_invalid_category_rejected(self):
        r = client.post("/api/knowledge/articles", json={
            "category": "not_a_real_category", "title": "x", "body": "y",
        }, headers=AUTH_OPERATOR)
        assert r.status_code == 422

    def test_get_article_records_view(self):
        created = client.post("/api/knowledge/articles", json={
            "category": "faq", "title": "Why brush twice", "body": "Because residue hides in the groove.",
        }, headers=AUTH_OPERATOR).json()
        r = client.get(f"/api/knowledge/articles/{created['id']}", headers=AUTH_ADMIN)
        assert r.status_code == 200
        assert r.json()["view_count"] == 1
        r2 = client.get(f"/api/knowledge/articles/{created['id']}", headers=AUTH_ADMIN)
        assert r2.json()["view_count"] == 2

    def test_list_articles_by_category(self):
        client.post("/api/knowledge/articles", json={
            "category": "clinical_pearl", "title": "Pearl one", "body": "body",
        }, headers=AUTH_OPERATOR)
        r = client.get("/api/knowledge/articles?category=clinical_pearl", headers=AUTH_ADMIN)
        assert r.status_code == 200
        assert all(a["category"] == "clinical_pearl" for a in r.json()["articles"])


class TestKnowledgeVersioning:
    def test_editing_approved_article_bumps_version_and_reopens_review(self):
        created = client.post("/api/knowledge/articles", json={
            "category": "local_standard", "title": "Coverage rule", "body": "Capture all six zones.",
        }, headers=AUTH_OPERATOR).json()
        client.post(f"/api/knowledge/articles/{created['id']}/approve", headers=AUTH_MGR)

        r = client.patch(f"/api/knowledge/articles/{created['id']}", json={"body": "Capture all eight zones."}, headers=AUTH_OPERATOR)
        assert r.status_code == 200
        body = r.json()
        assert body["version"] == 2
        assert body["approval_status"] == PENDING_REVIEW

    def test_editing_with_no_actual_change_does_not_bump_version(self):
        created = client.post("/api/knowledge/articles", json={
            "category": "faq", "title": "Same title", "body": "Same body.",
        }, headers=AUTH_OPERATOR).json()
        r = client.patch(f"/api/knowledge/articles/{created['id']}", json={"title": "Same title"}, headers=AUTH_OPERATOR)
        assert r.json()["version"] == 1


class TestGovernanceApprovalWorkflow:
    def test_approve_requires_leadership_role(self):
        created = client.post("/api/knowledge/articles", json={
            "category": "faq", "title": "q", "body": "a",
        }, headers=AUTH_OPERATOR).json()
        r = client.post(f"/api/knowledge/articles/{created['id']}/approve", headers=AUTH_OPERATOR)
        assert r.status_code == 403

    def test_approve_sets_reviewer_and_status(self):
        created = client.post("/api/knowledge/articles", json={
            "category": "faq", "title": "q2", "body": "a2",
        }, headers=AUTH_OPERATOR).json()
        r = client.post(f"/api/knowledge/articles/{created['id']}/approve", headers=AUTH_MGR)
        assert r.status_code == 200
        assert r.json()["approval_status"] == APPROVED
        assert r.json()["reviewer"]

    def test_archive_removes_from_default_list(self):
        created = client.post("/api/knowledge/articles", json={
            "category": "faq", "title": "outdated", "body": "old guidance",
        }, headers=AUTH_OPERATOR).json()
        client.post(f"/api/knowledge/articles/{created['id']}/approve", headers=AUTH_MGR)
        client.post(f"/api/knowledge/articles/{created['id']}/archive", headers=AUTH_MGR)

        r = client.get("/api/knowledge/articles", headers=AUTH_ADMIN)
        assert all(a["id"] != created["id"] for a in r.json()["articles"])

    def test_governance_summary(self):
        r = client.get("/api/knowledge/governance-summary", headers=AUTH_MGR)
        assert r.status_code == 200
        assert "by_approval_status" in r.json()


class TestSupervisorKnowledgeCapture:
    def test_teaching_point_saved_and_auto_approved(self):
        iid = _create("scissors", declared=["blood"])
        r = client.post(f"/api/inspections/{iid}/teaching-point", json={
            "explanation": "Blood pools in the pivot joint on this family.",
            "teaching_point": "Check the pivot joint under magnification.",
            "common_mistake": "Only checking the tip.",
            "prevention_tip": "Rotate the instrument during inspection.",
        }, headers=AUTH_MGR)
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["approval_status"] == APPROVED
        assert body["category"] == "teaching_point"
        assert body["source_inspection_id"] == iid

    def test_teaching_point_requires_leadership_role(self):
        iid = _create("scissors")
        r = client.post(f"/api/inspections/{iid}/teaching-point", json={
            "explanation": "x", "teaching_point": "y",
        }, headers=AUTH_OPERATOR)
        assert r.status_code == 403

    def test_teaching_point_updates_clinical_case_educational_notes(self):
        iid = _create("scissors", declared=["blood"])
        client.post(f"/api/inspections/{iid}/teaching-point", json={
            "explanation": "Explanation text.", "teaching_point": "Teaching headline.",
        }, headers=AUTH_MGR)
        r = client.get("/api/knowledge/cases", headers=AUTH_ADMIN)
        case = next((c for c in r.json()["cases"] if c["inspection_id"] == iid), None)
        assert case is not None
        assert "Teaching headline" in case["educational_notes"]


class TestClinicalCaseLibraryAndSimilarCases:
    def test_significant_inspection_auto_saves_case(self):
        iid = _create("scissors", declared=["blood"])
        r = client.get("/api/knowledge/cases", headers=AUTH_ADMIN)
        ids = [c["inspection_id"] for c in r.json()["cases"]]
        assert iid in ids

    def test_similar_case_finder_matches_same_family_and_finding(self):
        iid1 = _create("scissors", declared=["blood"])
        iid2 = _create("scissors", declared=["blood"])
        r = client.get(f"/api/inspections/{iid2}/similar-cases", headers=AUTH_ADMIN)
        assert r.status_code == 200
        body = r.json()
        similar_ids = [c["inspection_id"] for c in body["similar_cases"]]
        assert iid1 in similar_ids
        assert iid2 not in similar_ids

    def test_case_view_increments(self):
        iid = _create("scissors", declared=["blood"])
        cases = client.get("/api/knowledge/cases", headers=AUTH_ADMIN).json()["cases"]
        case = next(c for c in cases if c["inspection_id"] == iid)
        r = client.get(f"/api/knowledge/cases/{case['id']}", headers=AUTH_ADMIN)
        assert r.json()["view_count"] == 1


class TestSmartKnowledgeSearch:
    def test_search_by_finding(self):
        client.post("/api/knowledge/articles", json={
            "category": "clinical_pearl", "title": "Blood pearl", "body": "Blood hides in serrations.",
            "applicable_findings": ["blood"],
        }, headers=AUTH_OPERATOR)
        approved_id = client.get("/api/knowledge/articles?category=clinical_pearl", headers=AUTH_ADMIN).json()["articles"][0]["id"]
        client.post(f"/api/knowledge/articles/{approved_id}/approve", headers=AUTH_MGR)

        r = client.post("/api/knowledge/search", json={"query": "show all blood findings"}, headers=AUTH_OPERATOR)
        assert r.status_code == 200
        body = r.json()
        assert "blood" in body["matched_findings"]
        assert any(a["id"] == approved_id for a in body["articles"])

    def test_search_by_instrument_family(self):
        _create("scissors", declared=["blood"])
        r = client.post("/api/knowledge/search", json={"query": "show cases for kerrison"}, headers=AUTH_OPERATOR)
        assert r.status_code == 200
        assert "kerrison_rongeur" in r.json()["matched_instrument_families"]

    def test_search_logs_query_for_analytics(self):
        client.post("/api/knowledge/search", json={"query": "unique-query-marker-xyz"}, headers=AUTH_OPERATOR)
        r = client.get("/api/knowledge/analytics", headers=AUTH_MGR)
        queries = [q["query"] for q in r.json()["most_common_questions"]]
        assert "unique-query-marker-xyz" in queries


class TestAIKnowledgeAssistant:
    def test_assistant_retrieves_approved_guidance(self):
        created = client.post("/api/knowledge/articles", json={
            "category": "clinical_pearl", "title": "Corrosion pearl",
            "body": "Corrosion on the O-ring indicates repeated steam cycles beyond spec.",
            "applicable_findings": ["corrosion"],
        }, headers=AUTH_OPERATOR).json()
        client.post(f"/api/knowledge/articles/{created['id']}/approve", headers=AUTH_MGR)

        r = client.post("/api/knowledge/assistant", json={"question": "why does corrosion matter here"}, headers=AUTH_OPERATOR)
        assert r.status_code == 200
        body = r.json()
        assert any(f"#{created['id']}" in s for s in body["sources"])
        assert "corrosion" in body["answer"].lower()

    def test_assistant_ignores_unapproved_guidance(self):
        created = client.post("/api/knowledge/articles", json={
            "category": "clinical_pearl", "title": "Unapproved pearl",
            "body": "Some unreviewed claim about wear.",
            "applicable_findings": ["wear"],
        }, headers=AUTH_OPERATOR).json()
        r = client.post("/api/knowledge/assistant", json={"question": "tell me about wear"}, headers=AUTH_OPERATOR)
        assert not any(f"#{created['id']}" in s for s in r.json()["sources"])

    def test_assistant_answers_high_risk_anatomy_question(self):
        r = client.post("/api/knowledge/assistant", json={
            "question": "why is this anatomy high risk", "instrument_type": "kerrison_rongeur",
        }, headers=AUTH_OPERATOR)
        assert r.status_code == 200
        assert "kerrison_rongeur" in r.json()["matched_instrument_families"]

    def test_assistant_handles_no_match_honestly(self):
        r = client.post("/api/knowledge/assistant", json={"question": "asdkjaskldj nonsense query"}, headers=AUTH_OPERATOR)
        assert r.status_code == 200
        assert "No matching" in r.json()["answer"]


class TestOrganizationStandards:
    def test_create_and_list_standard(self):
        r = client.post("/api/knowledge/standards", json={
            "standard_type": "coverage_requirement", "title": "Full six-zone coverage",
            "description": "All inspections must capture six zones before scoring.",
        }, headers=AUTH_MGR)
        assert r.status_code == 201
        r2 = client.get("/api/knowledge/standards", headers=AUTH_ADMIN)
        assert any(s["title"] == "Full six-zone coverage" for s in r2.json()["standards"])

    def test_create_standard_requires_leadership(self):
        r = client.post("/api/knowledge/standards", json={
            "standard_type": "coverage_requirement", "title": "x", "description": "y",
        }, headers=AUTH_OPERATOR)
        assert r.status_code == 403

    def test_deactivate_standard(self):
        created = client.post("/api/knowledge/standards", json={
            "standard_type": "photography_standard", "title": "Deactivate me", "description": "d",
        }, headers=AUTH_MGR).json()
        client.post(f"/api/knowledge/standards/{created['id']}/deactivate", headers=AUTH_MGR)
        r = client.get("/api/knowledge/standards", headers=AUTH_ADMIN)
        assert all(s["id"] != created["id"] for s in r.json()["standards"])


class TestCompetencyKnowledgeLibrary:
    def test_competency_topic_merges_education_and_institutional(self):
        created = client.post("/api/knowledge/articles", json={
            "category": "competency_guidance", "title": "Rust guidance", "body": "Check under magnification.",
            "applicable_findings": ["rust"],
        }, headers=AUTH_OPERATOR).json()
        client.post(f"/api/knowledge/articles/{created['id']}/approve", headers=AUTH_MGR)

        r = client.get("/api/knowledge/competency-topics/rust", headers=AUTH_ADMIN)
        assert r.status_code == 200
        body = r.json()
        assert body["finding_type"] == "rust"
        assert any(a["id"] == created["id"] for a in body["institutional_knowledge"])

    def test_unknown_finding_type_404s(self):
        r = client.get("/api/knowledge/competency-topics/not-a-real-finding", headers=AUTH_ADMIN)
        assert r.status_code == 404
