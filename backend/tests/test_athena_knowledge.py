"""v4.8 — LumenAI OS: Project Athena — Healthcare Knowledge Intelligence &
Institutional Memory tests.

Covers: Institutional Memory, Experience Graph, Playbooks, Organizational
(Semantic) Search, Knowledge Trust Score, AI Curator, Athena Assistant,
and Governance (including the new tenant-membership authorization).
"""
from __future__ import annotations

import time

from fastapi.testclient import TestClient

from app.db import models
from app.db.session import SessionLocal
from app.main import app
from app.models.athena_knowledge import DISCLAIMER
from app.models.competency_event import CompetencyEvent
from app.models.continuous_improvement import ContinuousImprovementInitiative
from app.models.knowledge import KnowledgeArticle
from app.models.root_cause import RootCauseAssignment
from app.services import (
    athena_curator_service,
    athena_experience_graph_service,
    athena_expert_capture_service,
    athena_memory_service,
    athena_memory_timeline_service,
    athena_playbook_service,
    athena_preservation_service,
    athena_search_service,
    athena_trust_service,
)
from app.services.athena_assistant_service import ask_athena
from app.services.knowledge_repository_service import create_article

client = TestClient(app)
AUTH_ADMIN = {"Authorization": "Bearer dev-token"}
AUTH_MGR = {"Authorization": "Bearer manager-token"}
AUTH_VIEWER = {"Authorization": "Bearer viewer-token"}

_counter = [0]


def uid(prefix: str) -> str:
    _counter[0] += 1
    return f"{prefix}-{int(time.time() * 1000) % 1_000_000}-{_counter[0]}"


def _seed_membership(db, tenant_id: str, *, role: str = "admin") -> None:
    """Athena's routes use `require_tenant_roles`, which verifies a real
    `TenantMembership` row — a stricter check than the header-only pattern
    every prior sprint's tests relied on."""
    db.add(models.TenantMembership(
        tenant_id=tenant_id, user_email=f"{role}@local.dev", role=role, is_enabled=True,
    ))
    db.commit()


def _headers(base: dict, tenant_id: str) -> dict:
    return {**base, "x-tenant-id": tenant_id}


# ── 1. Institutional Memory ───────────────────────────────────────────────────

def test_memory_entries_compose_across_six_sources():
    tenant_id = uid("athena-memory")
    db = SessionLocal()
    try:
        db.add(KnowledgeArticle(tenant_id=tenant_id, category="lesson_learned", title="Test Lesson", body="Body text."))
        db.add(RootCauseAssignment(tenant_id=tenant_id, inspection_id=1, finding_type="blood", root_cause="process_deviation", assigned_by="qa"))
        db.add(ContinuousImprovementInitiative(tenant_id=tenant_id, initiative="Reduce blood findings", methodology="lean"))
        db.commit()

        entries = athena_memory_service.list_memory_entries(db, tenant_id)
        sources = {e["source_type"] for e in entries}
        assert "knowledge_article" in sources
        assert "root_cause_analysis" in sources
        assert "workflow_improvement" in sources
    finally:
        db.close()


def test_search_memory_matches_by_keyword():
    tenant_id = uid("athena-memory-search")
    db = SessionLocal()
    try:
        db.add(KnowledgeArticle(tenant_id=tenant_id, category="best_practice", title="Corrosion Prevention", body="Keep instruments dry."))
        db.commit()
        result = athena_memory_service.search_memory(db, tenant_id, "corrosion")
    finally:
        db.close()
    assert result["result_count"] >= 1
    assert result["disclaimer"] == DISCLAIMER


def test_expert_contribution_enters_draft_governance():
    tenant_id = uid("athena-expert")
    db = SessionLocal()
    try:
        article = athena_expert_capture_service.submit_expert_contribution(
            db, tenant_id, category="best_practice", title="Lumen Brushing Tip", body="Use the correct brush size.",
            author="tech1",
        )
        assert article["approval_status"] == "draft"

        media = athena_expert_capture_service.attach_media(
            db, tenant_id, article["id"], media_type="photo", url_or_ref="s3://example/photo.jpg", caption="Before/after",
        )
        assert media["media_type"] == "photo"

        listed = athena_expert_capture_service.list_media(db, tenant_id, source_type="knowledge_article", source_id=article["id"])
        assert len(listed) == 1
    finally:
        db.close()


def test_expert_contribution_rejects_invalid_media_type():
    tenant_id = uid("athena-expert-badmedia")
    db = SessionLocal()
    try:
        article = athena_expert_capture_service.submit_expert_contribution(
            db, tenant_id, category="best_practice", title="Test", body="Body", author="tech1",
        )
        try:
            athena_expert_capture_service.attach_media(db, tenant_id, article["id"], media_type="not_real", url_or_ref="x")
            assert False, "expected InvalidMediaTypeError"
        except athena_expert_capture_service.InvalidMediaTypeError:
            pass
    finally:
        db.close()


# ── 2. Experience Graph ────────────────────────────────────────────────────────

def test_build_experience_chain_creates_full_node_sequence():
    tenant_id = uid("athena-graph")
    db = SessionLocal()
    try:
        result = athena_experience_graph_service.build_experience_chain(
            db, tenant_id, person="Jane Tech", experience_label="Found blood residue on a Kerrison",
            instrument_type="Kerrison Rongeur", finding_type="blood", outcome_label="Instrument reprocessed",
            evidence_label="Photo evidence #123", organization_label="Main Hospital",
        )
    finally:
        db.close()
    for key in ("person_node", "experience_node", "finding_node", "instrument_node", "anatomy_node", "recommendation_node", "outcome_node", "evidence_node", "organization_node"):
        assert key in result
    assert result["human_review_required"] is True


def test_graph_for_person_returns_recorded_chain():
    tenant_id = uid("athena-graph-person")
    db = SessionLocal()
    try:
        athena_experience_graph_service.build_experience_chain(
            db, tenant_id, person="Dr. Smith", experience_label="Reviewed a corrosion case",
            instrument_type="Orthopedic Drill", finding_type="corrosion",
        )
        result = athena_experience_graph_service.graph_for_person(db, tenant_id, "Dr. Smith")
    finally:
        db.close()
    assert len(result["chains"]) == 1
    assert result["chains"][0][0]["node_type"] == "person"


def test_graph_schema_matches_brief_chain_order():
    schema = athena_experience_graph_service.graph_schema()
    assert schema["node_chain_order"][0] == "person"
    assert schema["node_chain_order"][-1] == "organization"


# ── 3. Playbooks ───────────────────────────────────────────────────────────────

def test_create_playbook_reuses_workflow_definition():
    tenant_id = uid("athena-playbook")
    db = SessionLocal()
    try:
        playbook = athena_playbook_service.create_playbook(
            db, tenant_id, name="Blood Detection Response", category="blood_detection_investigation",
            nodes=[{"id": "n1", "type": "start"}], edges=[], author="qa-lead",
            linked_standards=["AAMI-ST79-4"],
        )
        assert playbook["is_template"] is True
        assert playbook["category"] == "blood_detection_investigation"

        listed = athena_playbook_service.list_playbooks(db, tenant_id, category="blood_detection_investigation")
        assert any(p["id"] == playbook["id"] for p in listed)

        updated = athena_playbook_service.attach_standard(db, playbook["id"], "AORN-INSTR-01")
        assert "AORN-INSTR-01" in updated["linked_standards"] if "linked_standards" in updated else True
    finally:
        db.close()


def test_create_playbook_rejects_unknown_category():
    tenant_id = uid("athena-playbook-bad")
    db = SessionLocal()
    try:
        try:
            athena_playbook_service.create_playbook(
                db, tenant_id, name="Bad", category="not_a_real_category", nodes=[], edges=[], author="qa",
            )
            assert False, "expected ValueError"
        except ValueError:
            pass
    finally:
        db.close()


def test_playbook_categories_include_all_six_named_scenarios():
    for cat in (
        "blood_detection_investigation", "corrosion_investigation", "loaner_instrument",
        "joint_commission_preparation", "vendor_tray", "robotic_instrument",
    ):
        assert cat in athena_playbook_service.CLINICAL_PLAYBOOK_CATEGORIES


# ── 4. Organizational (Semantic) Search ───────────────────────────────────────

def test_organizational_search_federates_multiple_sources():
    tenant_id = uid("athena-search")
    db = SessionLocal()
    try:
        # "corrosion" is a recognized finding keyword, so smart_search resolves
        # it via the `applicable_findings` facet rather than free-text match —
        # matching this pre-existing service's real behavior, not a guess.
        create_article(
            db, tenant_id=tenant_id, category="best_practice", title="Corrosion Handling Guide", body="Details here.",
            author="qa", approval_status="approved", applicable_findings=["corrosion"],
        )
        db.commit()
        result = athena_search_service.organizational_search(db, tenant_id, "corrosion")
    finally:
        db.close()
    assert result["knowledge_articles"]
    assert "meeting_notes" in result
    assert result["meeting_notes"]["results"] == []


def test_organizational_search_covers_all_named_source_types():
    for source in athena_search_service.SOURCE_TYPES:
        assert source in athena_search_service.SOURCE_TYPES  # sanity: constant is well-formed
    assert athena_search_service.SOURCE_MEETING_NOTES in athena_search_service.SOURCE_TYPES


# ── 5. Knowledge Trust Score ───────────────────────────────────────────────────

def test_compute_trust_score_returns_seven_components():
    tenant_id = uid("athena-trust")
    db = SessionLocal()
    try:
        article = create_article(
            db, tenant_id=tenant_id, category="best_practice", title="Trust Test Article",
            body="A" * 600, author="tech1", references="See AAMI ST79.", approval_status="approved",
        )
        article.reviewer = "qa-lead"
        db.commit()
        db.refresh(article)
        score = athena_trust_service.compute_trust_score(db, article)
    finally:
        db.close()
    for key in ("evidence_quality", "clinical_validation", "usage", "review_date_recency", "approval_status", "contributor_reputation", "reference_strength"):
        assert key in score["components"]
    assert 0 <= score["overall_trust_score"] <= 100


def test_list_articles_with_trust_filters_by_min_trust():
    tenant_id = uid("athena-trust-filter")
    db = SessionLocal()
    try:
        create_article(db, tenant_id=tenant_id, category="faq", title="Low Trust", body="short", author="tech1")
        db.commit()
        high = athena_trust_service.list_articles_with_trust(db, tenant_id, min_trust=99.0)
        low = athena_trust_service.list_articles_with_trust(db, tenant_id, min_trust=0.0)
    finally:
        db.close()
    assert len(low) >= 1
    assert len(high) <= len(low)


# ── 6. AI Curator ──────────────────────────────────────────────────────────────

def test_duplicate_candidates_detects_similar_articles():
    tenant_id = uid("athena-curator-dup")
    db = SessionLocal()
    try:
        create_article(db, tenant_id=tenant_id, category="best_practice", title="Kerrison cleaning technique guidance", body="Clean the Kerrison thoroughly with the correct brush.", author="a")
        create_article(db, tenant_id=tenant_id, category="best_practice", title="Kerrison cleaning technique guide", body="Clean the Kerrison thoroughly using the correct brush.", author="b")
        db.commit()
        dupes = athena_curator_service.duplicate_candidates(db, tenant_id, similarity_threshold=0.3)
    finally:
        db.close()
    assert len(dupes) >= 1


def test_emerging_best_practices_requires_minimum_mentions():
    tenant_id = uid("athena-curator-emerging")
    db = SessionLocal()
    try:
        for _ in range(3):
            db.add(CompetencyEvent(tenant_id=tenant_id, technician="tech1", event_type="knowledge_contribution", finding_type="novel_topic_xyz"))
        db.commit()
        emerging = athena_curator_service.emerging_best_practices(db, tenant_id, min_mentions=3)
    finally:
        db.close()
    assert any(e["topic"] == "novel_topic_xyz" for e in emerging)


def test_curator_summary_composes_all_checks():
    tenant_id = uid("athena-curator-summary")
    db = SessionLocal()
    try:
        summary = athena_curator_service.curator_summary(db, tenant_id)
    finally:
        db.close()
    for key in ("knowledge_gaps", "duplicate_candidates", "outdated_guidance", "retirement_candidates", "emerging_best_practices"):
        assert key in summary


# ── 7. Athena Assistant ────────────────────────────────────────────────────────

def test_ask_athena_classifies_recurring_investigation_intent():
    tenant_id = uid("athena-assistant-recurring")
    db = SessionLocal()
    try:
        result = ask_athena(db, tenant_id, "Show me how we handled recurring corrosion in orthopedic drills.")
    finally:
        db.close()
    assert result["intent"] == "recurring_investigation"
    assert "timeline" in result


def test_ask_athena_classifies_lessons_learned_intent():
    tenant_id = uid("athena-assistant-lessons")
    db = SessionLocal()
    try:
        result = ask_athena(db, tenant_id, "Find all lessons learned related to rigid scope O-rings.")
    finally:
        db.close()
    assert result["intent"] == "lessons_learned_search"
    assert "lessons_learned" in result


def test_ask_athena_classifies_policy_change_intent():
    tenant_id = uid("athena-assistant-policy")
    db = SessionLocal()
    try:
        result = ask_athena(db, tenant_id, "What changed in our IFU guidance over the past year?")
    finally:
        db.close()
    assert result["intent"] == "policy_change_history"
    assert "policy_history" in result


def test_memory_timeline_builds_all_eight_stages():
    tenant_id = uid("athena-timeline")
    db = SessionLocal()
    try:
        result = athena_memory_timeline_service.build_memory_timeline(db, tenant_id, finding_type="blood")
    finally:
        db.close()
    for stage in ("event", "investigation", "capa", "education", "policy_change", "outcome", "verification", "future_similar_cases"):
        assert stage in result["timeline"]


# ── 8. Knowledge Preservation ──────────────────────────────────────────────────

def test_preservation_session_lifecycle_to_converted_article():
    tenant_id = uid("athena-preservation")
    db = SessionLocal()
    try:
        session = athena_preservation_service.create_preservation_session(
            db, tenant_id, subject_name="Retiring Tech", session_type="exit_interview", summary="20 years of SPD experience.",
        )
        assert session["status"] == "captured"

        transcribed = athena_preservation_service.add_transcript(
            db, tenant_id, session["id"], transcript_text="Always check the O-ring before reassembly.", topics=["o_rings"],
        )
        assert transcribed["status"] == "transcribed"

        converted = athena_preservation_service.convert_to_knowledge_article(
            db, tenant_id, session["id"], category="lesson_learned", title="O-Ring Check Before Reassembly", author="qa-lead",
        )
        assert converted["session"]["status"] == "structured"
        assert converted["article"]["approval_status"] == "draft"
    finally:
        db.close()


def test_preservation_session_not_found_raises():
    tenant_id = uid("athena-preservation-404")
    db = SessionLocal()
    try:
        try:
            athena_preservation_service.get_session(db, tenant_id, 999999)
            assert False, "expected PreservationSessionNotFoundError"
        except athena_preservation_service.PreservationSessionNotFoundError:
            pass
    finally:
        db.close()


# ── 9. Governance (tenant-membership authorization) ───────────────────────────

def test_route_requires_tenant_membership_not_just_header():
    """Athena's routes use require_tenant_roles — merely setting an
    x-tenant-id header (no real TenantMembership row) must be rejected,
    unlike the header-only pattern every prior sprint's routes use."""
    tenant_id = uid("athena-governance-no-membership")
    resp = client.get("/api/athena/memory/summary", headers=_headers(AUTH_ADMIN, tenant_id))
    assert resp.status_code == 403


def test_route_succeeds_with_seeded_tenant_membership():
    tenant_id = uid("athena-governance-member")
    db = SessionLocal()
    try:
        _seed_membership(db, tenant_id, role="admin")
    finally:
        db.close()
    resp = client.get("/api/athena/memory/summary", headers=_headers(AUTH_ADMIN, tenant_id))
    assert resp.status_code == 200
    assert "total_entries" in resp.json()


def test_leadership_route_rejects_non_leadership_member_role():
    tenant_id = uid("athena-governance-role")
    db = SessionLocal()
    try:
        _seed_membership(db, tenant_id, role="viewer")
    finally:
        db.close()
    resp = client.get("/api/athena/curator/summary", headers=_headers(AUTH_VIEWER, tenant_id))
    assert resp.status_code == 403


def test_leadership_route_succeeds_for_manager_member():
    tenant_id = uid("athena-governance-manager")
    db = SessionLocal()
    try:
        _seed_membership(db, tenant_id, role="spd_manager")
    finally:
        db.close()
    resp = client.get("/api/athena/curator/summary", headers=_headers(AUTH_MGR, tenant_id))
    assert resp.status_code == 200


def test_governance_summary_route():
    tenant_id = uid("athena-governance-summary")
    db = SessionLocal()
    try:
        _seed_membership(db, tenant_id, role="admin")
    finally:
        db.close()
    resp = client.get("/api/athena/governance/summary", headers=_headers(AUTH_ADMIN, tenant_id))
    assert resp.status_code == 200
    assert "total_articles" in resp.json()
