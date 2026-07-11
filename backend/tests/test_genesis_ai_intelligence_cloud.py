"""v5.3 — LumenAI Network: Project Genesis AI — Global Sterile Processing
Intelligence Cloud tests.

Covers: Instrument Registry, Anatomy Registry, Evidence linking,
Knowledge exchange, API, Research workflows, Governance, and Provenance.
"""
from __future__ import annotations

import time

from fastapi.testclient import TestClient

from app.db import models
from app.db.session import SessionLocal
from app.main import app
from app.models.instrument_registry import RegistryInstrument
from app.models.p24_standards import AdvisoryConsortiumMember
from app.services import horizon_evidence_service

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


def _seed_registry_instrument(db, *, manufacturer_name: str = "Acme") -> int:
    row = RegistryInstrument(manufacturer_name=manufacturer_name, model_name="Model-X", instrument_category="endoscope")
    db.add(row)
    db.commit()
    db.refresh(row)
    return row.id


def _seed_participant(db, tenant_id: str, *, research_opt_in: bool = False, observatory_opt_in: bool = False) -> None:
    db.add(AdvisoryConsortiumMember(
        tenant_id=tenant_id, organization_type="hospital", membership_status="active", membership_tier="contributor",
        research_opt_in=research_opt_in, observatory_opt_in=observatory_opt_in,
    ))
    db.commit()


# ── 1. Instrument Registry ────────────────────────────────────────────────────

def test_instrument_profile_set_and_get():
    tenant_id = uid("gai-t")
    db = SessionLocal()
    try:
        _seed_membership(db, tenant_id)
        instrument_id = _seed_registry_instrument(db)
    finally:
        db.close()

    r = client.patch(
        f"/api/genesis-ai/instruments/{instrument_id}/profile",
        json={
            "instrument_family": "kerrison_rongeur", "ifu_versions": ["v1.0", "v2.0"], "inspection_zones": ["tip", "box_lock"],
            "digital_twin_template_ref": "dtt-kerrison-1", "failure_modes": ["tip_wear"], "repair_guidance": "Replace tip at 0.5mm wear.",
            "knowledge_references": ["kb-101"],
        },
        headers=_headers(AUTH_ADMIN, tenant_id),
    )
    assert r.status_code == 200
    assert r.json()["instrument_family"] == "kerrison_rongeur"
    assert r.json()["ifu_versions"] == ["v1.0", "v2.0"]

    r2 = client.get(f"/api/genesis-ai/instruments/{instrument_id}/profile", headers=_headers(AUTH_ADMIN, tenant_id))
    assert r2.status_code == 200
    assert r2.json()["failure_modes"] == ["tip_wear"]

    r3 = client.get("/api/genesis-ai/instruments/families/kerrison_rongeur", headers=_headers(AUTH_ADMIN, tenant_id))
    assert r3.status_code == 200
    assert len(r3.json()["instruments"]) == 1


def test_unknown_instrument_profile_404s():
    tenant_id = uid("gai-t")
    db = SessionLocal()
    try:
        _seed_membership(db, tenant_id)
    finally:
        db.close()
    r = client.get("/api/genesis-ai/instruments/999999999/profile", headers=_headers(AUTH_ADMIN, tenant_id))
    assert r.status_code == 404


# ── 2. Anatomy Registry ───────────────────────────────────────────────────────

def test_anatomy_profile_lifecycle():
    tenant_id = uid("gai-t")
    db = SessionLocal()
    try:
        _seed_membership(db, tenant_id)
    finally:
        db.close()

    r = client.post(
        "/api/genesis-ai/anatomy-profiles",
        json={"profile_type": "rigid_scopes", "name": "0-degree rigid laparoscope", "zones": ["lens", "shaft", "eyepiece"]},
        headers=_headers(AUTH_ADMIN, tenant_id),
    )
    assert r.status_code == 201
    profile_id = r.json()["id"]

    r2 = client.get(f"/api/genesis-ai/anatomy-profiles/{profile_id}", headers=_headers(AUTH_ADMIN, tenant_id))
    assert r2.status_code == 200
    assert r2.json()["zones"] == ["lens", "shaft", "eyepiece"]

    r3 = client.get("/api/genesis-ai/anatomy-profiles", params={"profile_type": "rigid_scopes"}, headers=_headers(AUTH_ADMIN, tenant_id))
    assert r3.status_code == 200
    assert len(r3.json()["profiles"]) >= 1

    r4 = client.get("/api/genesis-ai/anatomy-profiles/summary", headers=_headers(AUTH_ADMIN, tenant_id))
    assert r4.status_code == 200
    assert r4.json()["by_profile_type"]["rigid_scopes"] >= 1


def test_invalid_anatomy_profile_type_rejected():
    tenant_id = uid("gai-t")
    db = SessionLocal()
    try:
        _seed_membership(db, tenant_id)
    finally:
        db.close()
    r = client.post(
        "/api/genesis-ai/anatomy-profiles", json={"profile_type": "not_real", "name": "x"}, headers=_headers(AUTH_ADMIN, tenant_id),
    )
    assert r.status_code == 422


def test_anatomy_future_expansion_other_type_accepted():
    tenant_id = uid("gai-t")
    db = SessionLocal()
    try:
        _seed_membership(db, tenant_id)
    finally:
        db.close()
    r = client.post(
        "/api/genesis-ai/anatomy-profiles", json={"profile_type": "other", "name": "Novel bipolar sealer"},
        headers=_headers(AUTH_ADMIN, tenant_id),
    )
    assert r.status_code == 201


# ── 3. Evidence linking ───────────────────────────────────────────────────────

def test_evidence_cloud_summary_reflects_horizon_evidence():
    tenant_id = uid("gai-t")
    db = SessionLocal()
    try:
        _seed_membership(db, tenant_id)
        horizon_evidence_service.add_evidence(
            db, evidence_type="peer_reviewed", title="Sterile processing outcomes study", citation_text="Journal, 2026.",
        )
    finally:
        db.close()

    r = client.get("/api/genesis-ai/evidence-cloud/summary", headers=_headers(AUTH_ADMIN, tenant_id))
    assert r.status_code == 200
    assert r.json()["by_evidence_type"]["peer_reviewed"] >= 1


# ── 4. Knowledge / Clinical Intelligence Exchange ────────────────────────────

def test_research_dataset_package_flows_through_hix():
    tenant_id = uid("gai-t")
    db = SessionLocal()
    try:
        _seed_membership(db, tenant_id)
    finally:
        db.close()

    r = client.post(
        "/api/genesis-ai/intelligence-exchange/research-dataset-packages",
        json={
            "dataset_ref": 1, "title": "Multi-center corrosion cohort", "description": "De-identified benchmark dataset.",
            "no_phi_confirmed": True, "no_identifiable_customer_data_confirmed": True,
        },
        headers=_headers(AUTH_ADMIN, tenant_id),
    )
    assert r.status_code == 201
    assert r.json()["package_type"] == "research_dataset"
    assert r.json()["status"] == "pending_governance_review"

    r2 = client.get("/api/genesis-ai/intelligence-exchange/summary", headers=_headers(AUTH_ADMIN, tenant_id))
    assert r2.status_code == 200
    assert "research_dataset" in r2.json()["package_types"]


def test_manufacturer_update_requires_review_before_publish():
    tenant_id = uid("gai-t")
    db = SessionLocal()
    try:
        _seed_membership(db, tenant_id)
    finally:
        db.close()

    r = client.post(
        "/api/genesis-ai/manufacturer-updates",
        json={"update_type": "ifu", "title": "IFU Rev C", "version": "3.0", "body": "Updated cleaning steps.", "instrument_category": "endoscope"},
        headers=_headers(AUTH_ADMIN, tenant_id),
    )
    assert r.status_code == 201
    update_id = r.json()["id"]
    assert r.json()["status"] == "pending_review"

    r2 = client.post(f"/api/genesis-ai/manufacturer-updates/{update_id}/review", json={"decision": "published"}, headers=_headers(AUTH_ADMIN, tenant_id))
    assert r2.status_code == 200
    assert r2.json()["status"] == "published"

    # Already-reviewed updates cannot be reviewed again.
    r3 = client.post(f"/api/genesis-ai/manufacturer-updates/{update_id}/review", json={"decision": "published"}, headers=_headers(AUTH_ADMIN, tenant_id))
    assert r3.status_code == 422


# ── 5. API (Instrument Intelligence API / Nexus v1 gateway) ──────────────────

def test_v1_instruments_anatomy_evidence_endpoints():
    tenant_id = uid("gai-t")
    db = SessionLocal()
    try:
        _seed_membership(db, tenant_id)
        instrument_id = _seed_registry_instrument(db)
    finally:
        db.close()

    db2 = SessionLocal()
    try:
        from app.services.genesis_ai_instrument_registry_service import set_instrument_profile

        set_instrument_profile(db2, instrument_id, instrument_family="scissors_family")
    finally:
        db2.close()

    r = client.get("/api/v1/instrument-registry", params={"instrument_family": "scissors_family"}, headers=_headers(AUTH_ADMIN, tenant_id))
    assert r.status_code == 200
    assert r.json()["api_version"] == "v1"
    assert len(r.json()["instruments"]) == 1

    r2 = client.get("/api/v1/anatomy", headers=_headers(AUTH_ADMIN, tenant_id))
    assert r2.status_code == 200
    assert r2.json()["api_version"] == "v1"

    r3 = client.get("/api/v1/evidence", headers=_headers(AUTH_ADMIN, tenant_id))
    assert r3.status_code == 200
    assert r3.json()["api_version"] == "v1"


def test_v1_gateway_requires_auth():
    r = client.get("/api/v1/instrument-registry")
    assert r.status_code == 401


# ── 6. Research workflows ─────────────────────────────────────────────────────

def test_research_hub_summary_and_opt_in():
    tenant_id = uid("gai-t")
    db = SessionLocal()
    try:
        _seed_membership(db, tenant_id)
        _seed_participant(db, tenant_id, research_opt_in=False)
    finally:
        db.close()

    r = client.patch(f"/api/genesis-ai/participants/{tenant_id}/research-opt-in", json={"research_opt_in": True}, headers=_headers(AUTH_ADMIN, tenant_id))
    assert r.status_code == 200
    assert r.json()["research_opt_in"] is True

    r2 = client.get("/api/genesis-ai/research-hub/summary", headers=_headers(AUTH_ADMIN, tenant_id))
    assert r2.status_code == 200
    assert r2.json()["opted_in_participant_count"] >= 1
    assert "research_studies" in r2.json()
    assert "proposed_studies" in r2.json()


def test_research_opt_in_unknown_participant_404s():
    tenant_id = uid("gai-t")
    db = SessionLocal()
    try:
        _seed_membership(db, tenant_id)
    finally:
        db.close()
    r = client.patch(f"/api/genesis-ai/participants/{uid('gai-unknown')}/research-opt-in", json={"research_opt_in": True}, headers=_headers(AUTH_ADMIN, tenant_id))
    assert r.status_code == 404


def test_learning_engine_summary_composes_horizon_and_phoenix():
    tenant_id = uid("gai-t")
    db = SessionLocal()
    try:
        _seed_membership(db, tenant_id)
    finally:
        db.close()
    r = client.get("/api/genesis-ai/learning-engine/summary", headers=_headers(AUTH_ADMIN, tenant_id))
    assert r.status_code == 200
    body = r.json()
    assert "improvement_hypotheses" in body
    assert "model_performance" in body
    assert "workflow_effectiveness" in body
    assert "knowledge_adoption" in body


# ── 7. Governance ──────────────────────────────────────────────────────────────

def test_viewer_cannot_submit_manufacturer_update():
    tenant_id = uid("gai-t")
    db = SessionLocal()
    try:
        _seed_membership(db, tenant_id, role="viewer")
    finally:
        db.close()
    r = client.post(
        "/api/genesis-ai/manufacturer-updates", json={"update_type": "ifu", "title": "x"}, headers=_headers(AUTH_VIEWER, tenant_id),
    )
    assert r.status_code == 403


def test_invalid_manufacturer_update_type_rejected():
    tenant_id = uid("gai-t")
    db = SessionLocal()
    try:
        _seed_membership(db, tenant_id)
    finally:
        db.close()
    r = client.post(
        "/api/genesis-ai/manufacturer-updates", json={"update_type": "not_real", "title": "x"}, headers=_headers(AUTH_ADMIN, tenant_id),
    )
    assert r.status_code == 422


def test_genesis_ai_routes_require_tenant_membership():
    tenant_id = uid("gai-nomember")
    r = client.get("/api/genesis-ai/summary", headers=_headers(AUTH_ADMIN, tenant_id))
    assert r.status_code in (401, 403)


# ── 8. Provenance ──────────────────────────────────────────────────────────────

def test_manufacturer_update_version_chain_provenance():
    tenant_id = uid("gai-t")
    db = SessionLocal()
    try:
        _seed_membership(db, tenant_id)
    finally:
        db.close()

    r_v1 = client.post(
        "/api/genesis-ai/manufacturer-updates", json={"update_type": "design_revision", "title": "Handle redesign", "version": "1.0"},
        headers=_headers(AUTH_ADMIN, tenant_id),
    )
    v1_id = r_v1.json()["id"]

    r_v2 = client.post(
        "/api/genesis-ai/manufacturer-updates",
        json={"update_type": "design_revision", "title": "Handle redesign", "version": "2.0", "supersedes_id": v1_id},
        headers=_headers(AUTH_ADMIN, tenant_id),
    )
    v2_id = r_v2.json()["id"]

    r_chain = client.get(f"/api/genesis-ai/manufacturer-updates/{v2_id}/version-chain", headers=_headers(AUTH_ADMIN, tenant_id))
    assert r_chain.status_code == 200
    versions = [entry["version"] for entry in r_chain.json()["chain"]]
    assert versions == ["1.0", "2.0"]


def test_standards_observatory_internal_policies_isolated_per_tenant():
    tenant_a = uid("gai-a")
    tenant_b = uid("gai-b")
    db = SessionLocal()
    try:
        _seed_membership(db, tenant_a)
        _seed_membership(db, tenant_b)
    finally:
        db.close()

    r_a = client.get("/api/genesis-ai/standards-observatory/summary", headers=_headers(AUTH_ADMIN, tenant_a))
    assert r_a.status_code == 200
    assert "internal_policy_changes" in r_a.json()

    r_b = client.get("/api/genesis-ai/standards-observatory/summary", headers=_headers(AUTH_ADMIN, tenant_b))
    assert r_b.status_code == 200
    # Each tenant's own (empty) policy list -- never another tenant's.
    assert r_b.json()["internal_policy_changes"] == []


def test_intelligence_cloud_umbrella_summary():
    tenant_id = uid("gai-t")
    db = SessionLocal()
    try:
        _seed_membership(db, tenant_id)
    finally:
        db.close()
    r = client.get("/api/genesis-ai/summary", headers=_headers(AUTH_ADMIN, tenant_id))
    assert r.status_code == 200
    body = r.json()
    assert "instrument_registry" in body
    assert "anatomy_registry" in body
    assert "evidence_cloud" in body
    assert "intelligence_exchange" in body
    assert "standards_observatory" in body
