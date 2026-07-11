"""v5.2 — LumenAI Network: Project GuardianX — AI Assurance Framework
tests.

Covers: Model Governance, Audit Replay, Explainability, Evidence Ledger,
Trust Scoring, Governance Workflow, Version Traceability, and Reporting.
"""
from __future__ import annotations

import time

from fastapi.testclient import TestClient

from app.db import models
from app.db.session import SessionLocal
from app.main import app
from app.models.inspection import Inspection
from app.models.workflow_forge import WorkflowDefinition, WorkflowExecution
from app.services import olympus_model_registry_service

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


def _make_model(db) -> dict:
    return olympus_model_registry_service.register_model(
        db, model_type="vision", name=f"Model-{uid('m')}", version="1.0.0",
        clinical_scope="Test scope", registered_by="admin@local.dev",
    )


# ── 1. Model Governance ───────────────────────────────────────────────────────

def test_model_governance_ownership_and_lookup():
    tenant_id = uid("gx-t")
    db = SessionLocal()
    try:
        _seed_membership(db, tenant_id)
        model = _make_model(db)
    finally:
        db.close()

    r = client.patch(
        f"/api/guardianx/models/{model['id']}/ownership",
        json={"model_owner": "Dr. Lee", "clinical_owner": "Dr. Patel", "technical_owner": "J. Chen", "approval_committee": "AI Governance Committee"},
        headers=_headers(AUTH_ADMIN, tenant_id),
    )
    assert r.status_code == 200
    assert r.json()["model_owner"] == "Dr. Lee"

    r2 = client.get(f"/api/guardianx/models/{model['id']}/governance", headers=_headers(AUTH_ADMIN, tenant_id))
    assert r2.status_code == 200
    assert r2.json()["clinical_owner"] == "Dr. Patel"

    r3 = client.patch(
        f"/api/guardianx/models/{model['id']}/use-cases",
        json={"approved_use_cases": ["screening"], "out_of_scope_uses": ["diagnosis"]},
        headers=_headers(AUTH_ADMIN, tenant_id),
    )
    assert r3.status_code == 200
    assert r3.json()["approved_use_cases"] == ["screening"]
    assert r3.json()["out_of_scope_uses"] == ["diagnosis"]


def test_retire_model_sets_retirement_date():
    tenant_id = uid("gx-t")
    db = SessionLocal()
    try:
        _seed_membership(db, tenant_id)
        model = _make_model(db)
    finally:
        db.close()
    r = client.post(f"/api/guardianx/models/{model['id']}/retire", headers=_headers(AUTH_ADMIN, tenant_id))
    assert r.status_code == 200
    assert r.json()["retirement_date"] is not None


def test_unknown_model_governance_404s():
    tenant_id = uid("gx-t")
    db = SessionLocal()
    try:
        _seed_membership(db, tenant_id)
    finally:
        db.close()
    r = client.get("/api/guardianx/models/999999999/governance", headers=_headers(AUTH_ADMIN, tenant_id))
    assert r.status_code == 404


# ── 2. Governance Workflow ────────────────────────────────────────────────────

def test_governance_review_reuses_forge_approval_chain():
    tenant_id = uid("gx-t")
    db = SessionLocal()
    try:
        _seed_membership(db, tenant_id)
        model = _make_model(db)
    finally:
        db.close()

    r_start = client.post(f"/api/guardianx/models/{model['id']}/governance-review/start", headers=_headers(AUTH_ADMIN, tenant_id))
    assert r_start.status_code == 200
    assert r_start.json()["chain"]["steps"] == [
        "clinical_review_board", "ai_governance_committee", "quality_leadership", "security", "compliance",
    ]

    r_status = client.get(f"/api/guardianx/models/{model['id']}/governance-review", headers=_headers(AUTH_ADMIN, tenant_id))
    assert r_status.json()["governance_status"] == "in_progress"

    r_advance = client.post(
        f"/api/guardianx/models/{model['id']}/governance-review/advance",
        json={"decided_role": "clinical_review_board", "decision": "rejected", "notes": "Insufficient clinical evidence."},
        headers=_headers(AUTH_ADMIN, tenant_id),
    )
    assert r_advance.status_code == 200
    assert r_advance.json()["governance_status"] == "rejected"


# ── 3. AI Risk Registry (folded into Model Governance coverage) ─────────────

def test_risk_registry_record_and_summary():
    tenant_id = uid("gx-t")
    db = SessionLocal()
    try:
        _seed_membership(db, tenant_id)
        model = _make_model(db)
    finally:
        db.close()

    r = client.post(
        "/api/guardianx/risks",
        json={"model_id": model["id"], "risk_type": "bias", "description": "Underrepresented skin tones in training data.",
              "mitigation": "Supplement dataset.", "severity": "high"},
        headers=_headers(AUTH_ADMIN, tenant_id),
    )
    assert r.status_code == 201
    risk_id = r.json()["id"]

    r2 = client.get(f"/api/guardianx/models/{model['id']}/risks", headers=_headers(AUTH_ADMIN, tenant_id))
    assert r2.status_code == 200
    assert len(r2.json()["risks"]) == 1

    r3 = client.patch(f"/api/guardianx/risks/{risk_id}/status", json={"status": "mitigated"}, headers=_headers(AUTH_ADMIN, tenant_id))
    assert r3.status_code == 200
    assert r3.json()["status"] == "mitigated"

    r4 = client.get("/api/guardianx/risks/summary", headers=_headers(AUTH_ADMIN, tenant_id))
    assert r4.status_code == 200
    assert r4.json()["total_risks"] >= 1


def test_invalid_risk_type_rejected():
    tenant_id = uid("gx-t")
    db = SessionLocal()
    try:
        _seed_membership(db, tenant_id)
        model = _make_model(db)
    finally:
        db.close()
    r = client.post(
        "/api/guardianx/risks", json={"model_id": model["id"], "risk_type": "not_real", "description": "x"},
        headers=_headers(AUTH_ADMIN, tenant_id),
    )
    assert r.status_code == 422


# ── 4. Explainability ──────────────────────────────────────────────────────────

def test_explainability_record_lifecycle():
    tenant_id = uid("gx-t")
    db = SessionLocal()
    try:
        _seed_membership(db, tenant_id)
    finally:
        db.close()

    r = client.post(
        "/api/guardianx/explainability",
        json={
            "source_type": "capa_suggestion", "source_id": "42", "input_summary": "Recurring corrosion findings.",
            "evidence_used": ["inspection-101", "inspection-102"], "knowledge_sources": ["kb-article-7"],
            "clinical_rules_applied": ["rule-corrosion-threshold"], "confidence": 0.87,
            "alternative_explanations": ["Could be a lighting artifact."],
        },
        headers=_headers(AUTH_ADMIN, tenant_id),
    )
    assert r.status_code == 201
    record_id = r.json()["id"]
    assert r.json()["confidence"] == 0.87
    assert r.json()["human_overrides"] == []

    r2 = client.post(
        f"/api/guardianx/explainability/{record_id}/human-override",
        json={"override_note": "Supervisor disagreed with corrosion classification."},
        headers=_headers(AUTH_ADMIN, tenant_id),
    )
    assert r2.status_code == 200
    assert len(r2.json()["human_overrides"]) == 1

    r3 = client.get("/api/guardianx/explainability", params={"source_type": "capa_suggestion", "source_id": "42"}, headers=_headers(AUTH_ADMIN, tenant_id))
    assert r3.status_code == 200
    assert len(r3.json()["explanations"]) == 1


# ── 5. Evidence Ledger ────────────────────────────────────────────────────────

def test_evidence_ledger_is_signed_and_verifiable():
    tenant_id = uid("gx-t")
    db = SessionLocal()
    try:
        _seed_membership(db, tenant_id)
    finally:
        db.close()

    r = client.post(
        "/api/guardianx/evidence",
        json={
            "source_type": "capa_suggestion", "source_id": "77", "evidence": ["finding-1", "finding-2"],
            "knowledge_version": "kb-v3", "model_version": "1.0.0", "workflow_version": "2",
        },
        headers=_headers(AUTH_ADMIN, tenant_id),
    )
    assert r.status_code == 201
    entry_id = r.json()["id"]
    assert r.json()["digital_signature"] != ""

    r_verify = client.get(f"/api/guardianx/evidence/{entry_id}/verify", headers=_headers(AUTH_ADMIN, tenant_id))
    assert r_verify.status_code == 200
    assert r_verify.json()["verified"] is True

    r_list = client.get("/api/guardianx/evidence", params={"source_type": "capa_suggestion", "source_id": "77"}, headers=_headers(AUTH_ADMIN, tenant_id))
    assert r_list.status_code == 200
    assert len(r_list.json()["entries"]) == 1


def test_unknown_evidence_entry_404s():
    tenant_id = uid("gx-t")
    db = SessionLocal()
    try:
        _seed_membership(db, tenant_id)
    finally:
        db.close()
    r = client.get("/api/guardianx/evidence/999999999", headers=_headers(AUTH_ADMIN, tenant_id))
    assert r.status_code == 404


# ── 6. Audit Replay ────────────────────────────────────────────────────────────

def test_replay_inspection():
    tenant_id = uid("gx-t")
    db = SessionLocal()
    try:
        _seed_membership(db, tenant_id)
        inspection = Inspection(file_name="scope-01.png")
        db.add(inspection)
        db.commit()
        db.refresh(inspection)
        inspection_id = inspection.id
    finally:
        db.close()

    r = client.get(f"/api/guardianx/audit-replay/inspections/{inspection_id}", headers=_headers(AUTH_ADMIN, tenant_id))
    assert r.status_code == 200
    assert r.json()["inspection_id"] == inspection_id
    assert "audit_chain" in r.json()


def test_replay_workflow_execution_includes_model_version():
    tenant_id = uid("gx-t")
    db = SessionLocal()
    try:
        _seed_membership(db, tenant_id)
        workflow = WorkflowDefinition(workflow_ref=uid("wf"), name="Test Workflow")
        db.add(workflow)
        db.commit()
        db.refresh(workflow)

        execution = WorkflowExecution(workflow_id=workflow.id)
        db.add(execution)
        db.commit()
        db.refresh(execution)
        execution_id = execution.id
        workflow_version = workflow.version
    finally:
        db.close()

    r = client.get(f"/api/guardianx/audit-replay/workflow-executions/{execution_id}", headers=_headers(AUTH_ADMIN, tenant_id))
    assert r.status_code == 200
    assert r.json()["model_version"]["version"] == workflow_version
    assert "timeline" in r.json()


def test_replay_recommendation_composes_evidence_and_explanations():
    tenant_id = uid("gx-t")
    db = SessionLocal()
    try:
        _seed_membership(db, tenant_id)
    finally:
        db.close()

    client.post(
        "/api/guardianx/evidence",
        json={"source_type": "rca_suggestion", "source_id": "500", "evidence": ["e1"]},
        headers=_headers(AUTH_ADMIN, tenant_id),
    )
    client.post(
        "/api/guardianx/explainability",
        json={"source_type": "rca_suggestion", "source_id": "500", "input_summary": "RCA reasoning"},
        headers=_headers(AUTH_ADMIN, tenant_id),
    )

    r = client.get(
        "/api/guardianx/audit-replay/recommendations", params={"source_type": "rca_suggestion", "source_id": "500"},
        headers=_headers(AUTH_ADMIN, tenant_id),
    )
    assert r.status_code == 200
    assert len(r.json()["evidence_ledger"]) == 1
    assert len(r.json()["explanations"]) == 1


def test_replay_unknown_inspection_404s():
    tenant_id = uid("gx-t")
    db = SessionLocal()
    try:
        _seed_membership(db, tenant_id)
    finally:
        db.close()
    r = client.get("/api/guardianx/audit-replay/inspections/999999999", headers=_headers(AUTH_ADMIN, tenant_id))
    assert r.status_code == 404


# ── 7. Trust Scoring ───────────────────────────────────────────────────────────

def test_model_trust_score_components():
    tenant_id = uid("gx-t")
    db = SessionLocal()
    try:
        _seed_membership(db, tenant_id)
        model = _make_model(db)
    finally:
        db.close()

    r = client.post(f"/api/guardianx/trust/models/{model['id']}/compute", headers=_headers(AUTH_ADMIN, tenant_id))
    assert r.status_code == 200
    body = r.json()
    assert set(body["components"].keys()) == {"validated", "certified", "governance_approved", "risk_posture"}
    assert body["components"]["validated"] == 0.0  # unvalidated by default
    assert body["human_review_required"] is True


def test_knowledge_workflow_digital_twin_trust_reuse_phoenix():
    tenant_id = uid("gx-t")
    db = SessionLocal()
    try:
        _seed_membership(db, tenant_id)
    finally:
        db.close()

    for endpoint in ("knowledge", "workflow", "digital-twin"):
        r = client.post(f"/api/guardianx/trust/{endpoint}/compute", headers=_headers(AUTH_ADMIN, tenant_id))
        assert r.status_code == 200
        assert "components" in r.json()


def test_platform_trust_score_and_history():
    tenant_id = uid("gx-t")
    db = SessionLocal()
    try:
        _seed_membership(db, tenant_id)
    finally:
        db.close()

    r = client.post("/api/guardianx/trust/platform/compute", headers=_headers(AUTH_ADMIN, tenant_id))
    assert r.status_code == 200
    assert r.json()["scope"] == "platform"

    r2 = client.get("/api/guardianx/trust/history", params={"scope": "platform", "scope_ref_id": tenant_id}, headers=_headers(AUTH_ADMIN, tenant_id))
    assert r2.status_code == 200
    assert len(r2.json()["history"]) >= 1


# ── 8. Version Traceability (Model Registry reuse) & Reporting ──────────────

def test_version_history_visible_via_assurance_center():
    tenant_id = uid("gx-t")
    db = SessionLocal()
    try:
        _seed_membership(db, tenant_id)
        model_v1 = _make_model(db)
    finally:
        db.close()

    r_v2 = client.post(
        "/api/olympus/models",
        json={"model_type": "vision", "name": model_v1["name"], "version": "2.0.0", "clinical_scope": "x", "supersedes_id": model_v1["id"]},
        headers=_headers(AUTH_ADMIN, tenant_id),
    )
    assert r_v2.status_code == 201
    model_v2_id = r_v2.json()["id"]

    r = client.get(f"/api/guardianx/assurance-center/models/{model_v2_id}", headers=_headers(AUTH_ADMIN, tenant_id))
    assert r.status_code == 200
    versions = [entry["version"] for entry in r.json()["version_history"]]
    assert versions == ["1.0.0", "2.0.0"]


def test_reports_executive_and_governance():
    tenant_id = uid("gx-t")
    db = SessionLocal()
    try:
        _seed_membership(db, tenant_id)
        _make_model(db)
    finally:
        db.close()

    r = client.get("/api/guardianx/reports/executive", headers=_headers(AUTH_ADMIN, tenant_id))
    assert r.status_code == 200
    assert "risk_registry" in r.json()
    assert "platform_trust_score" in r.json()

    r2 = client.get("/api/guardianx/reports/governance", headers=_headers(AUTH_ADMIN, tenant_id))
    assert r2.status_code == 200
    assert r2.json()["gates"] == [
        "clinical_review_board", "ai_governance_committee", "quality_leadership", "security", "compliance",
    ]


def test_reports_model_validation():
    tenant_id = uid("gx-t")
    db = SessionLocal()
    try:
        _seed_membership(db, tenant_id)
        model = _make_model(db)
    finally:
        db.close()

    r = client.get(f"/api/guardianx/reports/model-validation/{model['id']}", headers=_headers(AUTH_ADMIN, tenant_id))
    assert r.status_code == 200
    assert r.json()["model"]["id"] == model["id"]
    assert "trust_score" in r.json()


def test_compliance_mapping_and_traceability_matrix():
    tenant_id = uid("gx-t")
    db = SessionLocal()
    try:
        _seed_membership(db, tenant_id)
    finally:
        db.close()

    r = client.post(
        "/api/guardianx/compliance-mappings",
        json={"capability_name": "Digital Twin Health Scoring", "requirement_type": "internal_sop", "requirement_reference": "SOP-114"},
        headers=_headers(AUTH_ADMIN, tenant_id),
    )
    assert r.status_code == 201
    assert r.json()["verified_against_catalogue"] is False  # internal_sop has no catalogue to verify against

    r2 = client.get("/api/guardianx/compliance-mappings/traceability-matrix", headers=_headers(AUTH_ADMIN, tenant_id))
    assert r2.status_code == 200
    assert "Digital Twin Health Scoring" in r2.json()["by_capability"]


def test_invalid_requirement_type_rejected():
    tenant_id = uid("gx-t")
    db = SessionLocal()
    try:
        _seed_membership(db, tenant_id)
    finally:
        db.close()
    r = client.post(
        "/api/guardianx/compliance-mappings",
        json={"capability_name": "x", "requirement_type": "not_real", "requirement_reference": "y"},
        headers=_headers(AUTH_ADMIN, tenant_id),
    )
    assert r.status_code == 422


# ── Security ───────────────────────────────────────────────────────────────────

def test_guardianx_routes_require_tenant_membership():
    tenant_id = uid("gx-nomember")
    r = client.get("/api/guardianx/models/governance", headers=_headers(AUTH_ADMIN, tenant_id))
    assert r.status_code in (401, 403)


def test_viewer_cannot_start_governance_review():
    tenant_id = uid("gx-t")
    db = SessionLocal()
    try:
        _seed_membership(db, tenant_id, role="viewer")
        model = _make_model(db)
    finally:
        db.close()
    r = client.post(f"/api/guardianx/models/{model['id']}/governance-review/start", headers=_headers(AUTH_VIEWER, tenant_id))
    assert r.status_code == 403
