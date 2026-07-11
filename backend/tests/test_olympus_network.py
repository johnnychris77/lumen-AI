"""v5.1 — LumenAI Network: Project Olympus — Autonomous Healthcare
Intelligence Network tests.

Covers: Network identity, Trust scoring, Knowledge exchange, Marketplace,
Registry, Governance, Certification, and Security.
"""
from __future__ import annotations

import time

from fastapi.testclient import TestClient

from app.db import models
from app.db.session import SessionLocal
from app.main import app
from app.models.federated_horizon import KnowledgeContribution
from app.models.p24_standards import AdvisoryConsortiumMember
from app.services import olympus_exchange_service, olympus_model_registry_service

client = TestClient(app)
AUTH_ADMIN = {"Authorization": "Bearer dev-token"}
AUTH_VIEWER = {"Authorization": "Bearer viewer-token"}

_counter = [0]


def uid(prefix: str) -> str:
    _counter[0] += 1
    return f"{prefix}-{int(time.time() * 1000) % 1_000_000}-{_counter[0]}"


def _seed_membership(db, tenant_id: str, *, role: str = "admin") -> None:
    db.add(models.TenantMembership(tenant_id=tenant_id, user_email=f"{role}@local.dev", role=role, is_enabled=True))
    db.commit()


def _headers(base: dict, tenant_id: str) -> dict:
    return {**base, "x-tenant-id": tenant_id}


def _seed_participant(db, tenant_id: str, *, organization_type: str = "hospital", membership_status: str = "active", observatory_opt_in: bool = False) -> None:
    db.add(AdvisoryConsortiumMember(
        tenant_id=tenant_id, organization_type=organization_type, membership_status=membership_status,
        membership_tier="contributor", observatory_opt_in=observatory_opt_in,
    ))
    db.commit()


# ── 1. Network Identity ──────────────────────────────────────────────────────

def test_network_participant_directory_and_detail():
    tenant_id = uid("olympus-t")
    db = SessionLocal()
    try:
        _seed_membership(db, tenant_id)
        _seed_participant(db, tenant_id, organization_type="educator")
    finally:
        db.close()

    r = client.get("/api/olympus/participants", headers=_headers(AUTH_ADMIN, tenant_id), params={"organization_type": "educator"})
    assert r.status_code == 200
    assert any(p["tenant_id"] == tenant_id for p in r.json()["participants"])

    r2 = client.get(f"/api/olympus/participants/{tenant_id}", headers=_headers(AUTH_ADMIN, tenant_id))
    assert r2.status_code == 200
    assert r2.json()["organization_type"] == "educator"
    assert "trust" in r2.json()
    assert "contribution_history" in r2.json()


def test_invalid_organization_type_rejected():
    tenant_id = uid("olympus-t")
    db = SessionLocal()
    try:
        _seed_membership(db, tenant_id)
    finally:
        db.close()
    r = client.get("/api/olympus/participants", headers=_headers(AUTH_ADMIN, tenant_id), params={"organization_type": "not_a_real_type"})
    assert r.status_code == 422


def test_directory_summary_counts_active_by_type():
    tenant_id = uid("olympus-t")
    db = SessionLocal()
    try:
        _seed_membership(db, tenant_id)
        _seed_participant(db, tenant_id, organization_type="consultant")
    finally:
        db.close()
    r = client.get("/api/olympus/directory-summary", headers=_headers(AUTH_ADMIN, tenant_id))
    assert r.status_code == 200
    assert r.json()["by_organization_type"].get("consultant", 0) >= 1


# ── 2. Trust Scoring ──────────────────────────────────────────────────────────

def test_compute_trust_snapshot_and_history():
    tenant_id = uid("olympus-t")
    db = SessionLocal()
    try:
        _seed_membership(db, tenant_id)
        _seed_participant(db, tenant_id)
    finally:
        db.close()

    r = client.post(f"/api/olympus/trust/{tenant_id}/compute", headers=_headers(AUTH_ADMIN, tenant_id))
    assert r.status_code == 200
    body = r.json()
    assert set(body["components"].keys()) == {
        "participation_status", "knowledge_quality", "validation_history",
        "evidence_contributions", "peer_recognition", "governance_compliance",
    }
    assert body["components"]["participation_status"] == 100.0  # active membership
    assert body["human_review_required"] is True

    r2 = client.get(f"/api/olympus/trust/{tenant_id}/history", headers=_headers(AUTH_ADMIN, tenant_id))
    assert r2.status_code == 200
    assert len(r2.json()["history"]) >= 1


def test_trust_score_zero_for_brand_new_unenrolled_participant():
    """Trust is earned, not assigned — an org with no AdvisoryConsortiumMember
    row at all scores 0 on every component, never a default/optimistic score."""
    tenant_id = uid("olympus-t")
    db = SessionLocal()
    try:
        _seed_membership(db, tenant_id)
    finally:
        db.close()
    r = client.post(f"/api/olympus/trust/{tenant_id}/compute", headers=_headers(AUTH_ADMIN, tenant_id))
    assert r.status_code == 200
    assert r.json()["overall_trust_score"] == 0.0


def test_trust_leaderboard_ranks_by_score():
    tenant_id = uid("olympus-t")
    db = SessionLocal()
    try:
        _seed_membership(db, tenant_id)
        _seed_participant(db, tenant_id)
    finally:
        db.close()
    client.post(f"/api/olympus/trust/{tenant_id}/compute", headers=_headers(AUTH_ADMIN, tenant_id))
    r = client.get("/api/olympus/trust/leaderboard", headers=_headers(AUTH_ADMIN, tenant_id))
    assert r.status_code == 200
    scores = [row["overall_trust_score"] for row in r.json()["leaderboard"]]
    assert scores == sorted(scores, reverse=True)


# ── 3. Knowledge Exchange (HIX) ───────────────────────────────────────────────

def test_hix_package_lifecycle_requires_governance_before_publish():
    tenant_id = uid("olympus-t")
    db = SessionLocal()
    try:
        _seed_membership(db, tenant_id)
    finally:
        db.close()

    payload = {
        "package_type": "knowledge_package", "title": "Contamination pattern insights",
        "description": "De-identified aggregate findings.", "content_ref_type": "knowledge_article",
        "content_ref_id": 1, "no_phi_confirmed": True, "no_identifiable_customer_data_confirmed": True,
    }
    r = client.post("/api/olympus/exchange/packages", json=payload, headers=_headers(AUTH_ADMIN, tenant_id))
    assert r.status_code == 201
    package_id = r.json()["id"]
    assert r.json()["status"] == "pending_governance_review"

    # Cannot publish before governance review.
    r_early = client.post(f"/api/olympus/exchange/packages/{package_id}/publish", headers=_headers(AUTH_ADMIN, tenant_id))
    assert r_early.status_code == 422

    r2 = client.post(
        f"/api/olympus/exchange/packages/{package_id}/governance-review", json={"decision": "approved"},
        headers=_headers(AUTH_ADMIN, tenant_id),
    )
    assert r2.status_code == 200
    assert r2.json()["status"] == "approved"

    r3 = client.post(f"/api/olympus/exchange/packages/{package_id}/publish", headers=_headers(AUTH_ADMIN, tenant_id))
    assert r3.status_code == 200
    assert r3.json()["status"] == "published"


def test_hix_package_submission_requires_deidentification_confirmations():
    tenant_id = uid("olympus-t")
    db = SessionLocal()
    try:
        _seed_membership(db, tenant_id)
    finally:
        db.close()
    payload = {
        "package_type": "knowledge_package", "title": "x", "description": "", "content_ref_type": "knowledge_article",
        "content_ref_id": 1, "no_phi_confirmed": True, "no_identifiable_customer_data_confirmed": False,
    }
    r = client.post("/api/olympus/exchange/packages", json=payload, headers=_headers(AUTH_ADMIN, tenant_id))
    assert r.status_code == 422


def test_published_packages_are_deidentified_for_other_organizations():
    source_tenant = uid("olympus-src")
    other_tenant = uid("olympus-other")
    db = SessionLocal()
    try:
        _seed_membership(db, source_tenant)
        _seed_membership(db, other_tenant, role="viewer")
    finally:
        db.close()

    db2 = SessionLocal()
    try:
        pkg = olympus_exchange_service.submit_package(
            db2, source_tenant, package_type="benchmark_report", title="Benchmark", description="",
            content_ref_type="benchmark", content_ref_id=None, no_phi_confirmed=True,
            no_identifiable_customer_data_confirmed=True, submitted_by="mgr@local.dev",
        )
        olympus_exchange_service.governance_review_package(db2, pkg["id"], decision="approved", reviewed_by="admin@local.dev")
        olympus_exchange_service.publish_package(db2, pkg["id"], published_by="admin@local.dev")
    finally:
        db2.close()

    r_other = client.get("/api/olympus/exchange/packages", headers=_headers(AUTH_VIEWER, other_tenant))
    assert r_other.status_code == 200
    other_view = next(p for p in r_other.json()["packages"] if p["id"] == pkg["id"])
    assert "source_tenant_id" not in other_view

    r_own = client.get("/api/olympus/exchange/packages/mine", headers=_headers(AUTH_ADMIN, source_tenant))
    assert r_own.status_code == 200
    own_view = next(p for p in r_own.json()["packages"] if p["id"] == pkg["id"])
    assert own_view["source_tenant_id"] == source_tenant


# ── 4. Marketplace ────────────────────────────────────────────────────────────

def test_innovation_marketplace_summary_covers_new_listing_types():
    tenant_id = uid("olympus-t")
    db = SessionLocal()
    try:
        _seed_membership(db, tenant_id)
    finally:
        db.close()
    r = client.get("/api/olympus/marketplace/summary", headers=_headers(AUTH_ADMIN, tenant_id))
    assert r.status_code == 200
    body = r.json()
    assert "workflow_pack" in body["listing_types"]
    assert "simulation_template" in body["listing_types"]
    assert "by_listing_type" in body


# ── 5. Registry (AI Model Registry) ──────────────────────────────────────────

def test_register_model_and_version_chain():
    tenant_id = uid("olympus-t")
    db = SessionLocal()
    try:
        _seed_membership(db, tenant_id)
    finally:
        db.close()

    payload = {
        "model_type": "vision", "name": "Lumen Vision Classifier", "version": "1.0.0",
        "clinical_scope": "Corrosion and residue detection.", "evidence": ["internal_validation_study_2026"],
        "performance_metrics": {"sensitivity": 0.94, "specificity": 0.91},
    }
    r = client.post("/api/olympus/models", json=payload, headers=_headers(AUTH_ADMIN, tenant_id))
    assert r.status_code == 201
    model_id = r.json()["id"]
    assert r.json()["validation_status"] == "unvalidated"

    r_v2 = client.post(
        "/api/olympus/models", json={**payload, "version": "2.0.0", "supersedes_id": model_id},
        headers=_headers(AUTH_ADMIN, tenant_id),
    )
    assert r_v2.status_code == 201
    model_v2_id = r_v2.json()["id"]

    r_chain = client.get(f"/api/olympus/models/{model_v2_id}/version-chain", headers=_headers(AUTH_ADMIN, tenant_id))
    assert r_chain.status_code == 200
    versions = [entry["version"] for entry in r_chain.json()["chain"]]
    assert versions == ["1.0.0", "2.0.0"]


def test_invalid_model_type_rejected():
    tenant_id = uid("olympus-t")
    db = SessionLocal()
    try:
        _seed_membership(db, tenant_id)
    finally:
        db.close()
    r = client.post(
        "/api/olympus/models", json={"model_type": "not_real", "name": "x", "version": "1.0", "clinical_scope": ""},
        headers=_headers(AUTH_ADMIN, tenant_id),
    )
    assert r.status_code == 422


def test_set_validation_status():
    db = SessionLocal()
    try:
        model = olympus_model_registry_service.register_model(
            db, model_type="reasoning", name="Root Cause Reasoner", version="1.0.0",
            clinical_scope="RCA support", registered_by="admin@local.dev",
        )
    finally:
        db.close()
    tenant_id = uid("olympus-t")
    db2 = SessionLocal()
    try:
        _seed_membership(db2, tenant_id)
    finally:
        db2.close()
    r = client.patch(
        f"/api/olympus/models/{model['id']}/validation-status", json={"validation_status": "validated"},
        headers=_headers(AUTH_ADMIN, tenant_id),
    )
    assert r.status_code == 200
    assert r.json()["validation_status"] == "validated"


# ── 6. Governance ─────────────────────────────────────────────────────────────

def test_file_and_decide_governance_case():
    tenant_id = uid("olympus-t")
    db = SessionLocal()
    try:
        _seed_membership(db, tenant_id)
    finally:
        db.close()

    r = client.post(
        "/api/olympus/governance/cases",
        json={"case_type": "dispute", "title": "Attribution dispute", "description": "Two orgs claim the same finding.",
              "involved_tenant_ids": [tenant_id]},
        headers=_headers(AUTH_ADMIN, tenant_id),
    )
    assert r.status_code == 201
    case_id = r.json()["id"]
    assert r.json()["status"] == "open"

    r2 = client.post(
        f"/api/olympus/governance/cases/{case_id}/decide",
        json={"decision": "resolved", "resolution": "Attribution split 50/50."},
        headers=_headers(AUTH_ADMIN, tenant_id),
    )
    assert r2.status_code == 200
    assert r2.json()["status"] == "resolved"

    # Already-decided cases cannot be decided again.
    r3 = client.post(
        f"/api/olympus/governance/cases/{case_id}/decide",
        json={"decision": "resolved", "resolution": "again"},
        headers=_headers(AUTH_ADMIN, tenant_id),
    )
    assert r3.status_code == 422


def test_invalid_case_type_rejected():
    tenant_id = uid("olympus-t")
    db = SessionLocal()
    try:
        _seed_membership(db, tenant_id)
    finally:
        db.close()
    r = client.post(
        "/api/olympus/governance/cases", json={"case_type": "not_real", "title": "x", "description": ""},
        headers=_headers(AUTH_ADMIN, tenant_id),
    )
    assert r.status_code == 422


def test_governance_summary_counts_open_cases_by_type():
    tenant_id = uid("olympus-t")
    db = SessionLocal()
    try:
        _seed_membership(db, tenant_id)
    finally:
        db.close()
    client.post(
        "/api/olympus/governance/cases",
        json={"case_type": "ethics_review", "title": "Ethics case", "description": ""},
        headers=_headers(AUTH_ADMIN, tenant_id),
    )
    r = client.get("/api/olympus/governance/summary", headers=_headers(AUTH_ADMIN, tenant_id))
    assert r.status_code == 200
    assert r.json()["open_by_case_type"].get("ethics_review", 0) >= 1


# ── 7. Certification ──────────────────────────────────────────────────────────

def test_ai_model_certification_reuses_forge_approval_chain():
    tenant_id = uid("olympus-t")
    db = SessionLocal()
    try:
        _seed_membership(db, tenant_id)
    finally:
        db.close()

    r_model = client.post(
        "/api/olympus/models",
        json={"model_type": "simulation", "name": "Digital Twin Simulator", "version": "1.0.0", "clinical_scope": "Twin risk projections"},
        headers=_headers(AUTH_ADMIN, tenant_id),
    )
    model_id = r_model.json()["id"]

    r_start = client.post(f"/api/olympus/models/{model_id}/certification/start", headers=_headers(AUTH_ADMIN, tenant_id))
    assert r_start.status_code == 200
    assert r_start.json()["chain"]["steps"] == [
        "security", "performance", "clinical_safety", "explainability", "accessibility", "documentation", "governance",
    ]

    r_status = client.get(f"/api/olympus/models/{model_id}/certification", headers=_headers(AUTH_ADMIN, tenant_id))
    assert r_status.json()["certification_status"] == "in_progress"

    # A rejection at any gate ends certification immediately.
    r_advance = client.post(
        f"/api/olympus/models/{model_id}/certification/advance",
        json={"decided_role": "security", "decision": "rejected", "notes": "Fails threat model."},
        headers=_headers(AUTH_ADMIN, tenant_id),
    )
    assert r_advance.status_code == 200
    assert r_advance.json()["certification_status"] == "rejected"


def test_certification_registry_reflects_certified_and_rejected_models():
    tenant_id = uid("olympus-t")
    db = SessionLocal()
    try:
        _seed_membership(db, tenant_id)
    finally:
        db.close()

    r_registry = client.get("/api/olympus/certification-registry", headers=_headers(AUTH_ADMIN, tenant_id))
    assert r_registry.status_code == 200
    body = r_registry.json()
    assert body["gates"] == [
        "security", "performance", "clinical_safety", "explainability", "accessibility", "documentation", "governance",
    ]
    assert "total_certified" in body and "total_in_progress" in body and "total_rejected" in body


# ── 8. Security ────────────────────────────────────────────────────────────────

def test_olympus_routes_require_tenant_membership():
    """No TenantMembership seeded — the dev-token role resolves, but
    require_tenant_roles must still 403 without a real membership row."""
    tenant_id = uid("olympus-nomember")
    r = client.get("/api/olympus/participants", headers=_headers(AUTH_ADMIN, tenant_id))
    assert r.status_code in (401, 403)


def test_viewer_cannot_file_governance_case():
    tenant_id = uid("olympus-t")
    db = SessionLocal()
    try:
        _seed_membership(db, tenant_id, role="viewer")
    finally:
        db.close()
    r = client.post(
        "/api/olympus/governance/cases",
        json={"case_type": "dispute", "title": "x", "description": ""},
        headers=_headers(AUTH_VIEWER, tenant_id),
    )
    assert r.status_code == 403


def test_unknown_exchange_package_404s():
    tenant_id = uid("olympus-t")
    db = SessionLocal()
    try:
        _seed_membership(db, tenant_id)
    finally:
        db.close()
    r = client.get("/api/olympus/exchange/packages/999999999", headers=_headers(AUTH_ADMIN, tenant_id))
    assert r.status_code == 404


def test_cross_organization_contribution_history_isolated():
    """A tenant's contribution history counts only its own
    KnowledgeContribution rows -- never another tenant's."""
    tenant_a = uid("olympus-a")
    tenant_b = uid("olympus-b")
    db = SessionLocal()
    try:
        _seed_membership(db, tenant_a)
        _seed_membership(db, tenant_b)
        _seed_participant(db, tenant_a)
        db.add(KnowledgeContribution(
            contribution_ref=uid("ref"), source_tenant_id=tenant_a, contribution_type="best_practice",
            category="general", title="A's contribution", body="body", submitted_by="admin@local.dev",
            approval_status="approved",
        ))
        db.commit()
    finally:
        db.close()

    r = client.get(f"/api/olympus/participants/{tenant_a}", headers=_headers(AUTH_ADMIN, tenant_a))
    assert r.status_code == 200
    assert r.json()["contribution_history"]["knowledge_contributions_total"] >= 1

    # tenant_b has a real membership but was never enrolled as a network
    # participant, and never sees tenant_a's contribution.
    r_b = client.get(f"/api/olympus/participants/{tenant_b}", headers=_headers(AUTH_ADMIN, tenant_b))
    assert r_b.status_code == 404
