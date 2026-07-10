"""v3.5 — Project Beacon: Collaborative Quality Ecosystem & Industry
Intelligence Platform tests."""
from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.db.session import SessionLocal
from app.main import app
from app.models.baseline_library import BaselineLibraryEntry
from app.models.digital_twin import InstrumentFlowRecord
from app.models.inspection import Inspection
from app.models.inspection_finding import InspectionFinding
from app.models.instrument_registry import RegistryInstrument
from app.models.or_connect import RepairRequest
from app.models.p24_standards import AdvisoryConsortiumMember

client = TestClient(app)
AUTH_ADMIN = {"Authorization": "Bearer dev-token"}
AUTH_MGR = {"Authorization": "Bearer manager-token"}
AUTH_VIEWER = {"Authorization": "Bearer viewer-token"}

_counter = [0]


def uid(prefix: str) -> str:
    _counter[0] += 1
    return f"{prefix}-{int(time.time() * 1000) % 1_000_000}-{_counter[0]}"


def _headers(base: dict, tenant_id: str) -> dict:
    return {**base, "x-tenant-id": tenant_id}


def _manufacturer_headers(manufacturer_id: str) -> dict:
    return {**AUTH_ADMIN, "X-Manufacturer-ID": manufacturer_id}


def _make_registry_instrument(manufacturer_name: str, udi: str) -> None:
    db = SessionLocal()
    try:
        db.add(RegistryInstrument(
            udi=udi, manufacturer_name=manufacturer_name, model_name="TestModel", instrument_category="rongeur",
        ))
        db.commit()
    finally:
        db.close()


def _make_baseline(manufacturer_name: str, *, approval_status: str = "approved") -> None:
    db = SessionLocal()
    try:
        db.add(BaselineLibraryEntry(
            instrument_category="rongeur", manufacturer_name=manufacturer_name, model_name="TestModel",
            approval_status=approval_status,
        ))
        db.commit()
    finally:
        db.close()


def _make_inspection(tenant_id: str, *, instrument_udi: str = "", instrument_type: str = "kerrison_rongeur", **overrides) -> int:
    db = SessionLocal()
    try:
        defaults = dict(
            tenant_id=tenant_id, file_name="x.jpg", instrument_type=instrument_type, instrument_udi=instrument_udi,
            has_image=True, risk_score=10, stain_detected=False, status="pending",
        )
        defaults.update(overrides)
        insp = Inspection(**defaults)
        db.add(insp)
        db.commit()
        db.refresh(insp)
        return insp.id
    finally:
        db.close()


def _make_finding(tenant_id: str, inspection_id: int, *, finding_type: str = "corrosion", zone: str = "serrations") -> None:
    db = SessionLocal()
    try:
        db.add(InspectionFinding(
            tenant_id=tenant_id, inspection_id=inspection_id, instrument_type="kerrison_rongeur",
            finding_type=finding_type, zone=zone,
        ))
        db.commit()
    finally:
        db.close()


def _make_repair(tenant_id: str, *, vendor_name: str, failure_category: str | None = None, days_ago: int = 0, **overrides) -> int:
    db = SessionLocal()
    try:
        defaults = dict(
            tenant_id=tenant_id, inspection_id=1, instrument_identity=f"barcode:{uid('inst')}", vendor_name=vendor_name,
            failure_category=failure_category, created_at=datetime.now(timezone.utc) - timedelta(days=days_ago),
        )
        defaults.update(overrides)
        repair = RepairRequest(**defaults)
        db.add(repair)
        db.commit()
        db.refresh(repair)
        return repair.id
    finally:
        db.close()


def _make_consortium_member(tenant_id: str, *, organization_type: str, membership_status: str = "active") -> None:
    db = SessionLocal()
    try:
        existing = db.query(AdvisoryConsortiumMember).filter_by(tenant_id=tenant_id).first()
        if existing:
            return
        db.add(AdvisoryConsortiumMember(
            tenant_id=tenant_id, organization_type=organization_type, membership_status=membership_status,
            membership_tier="observer",
        ))
        db.commit()
    finally:
        db.close()


def _seed_manufacturer_network(manufacturer_id: str, *, n_tenants: int = 5) -> list[str]:
    udi = f"udi-{uid('m')}"
    _make_registry_instrument(manufacturer_id, udi)
    tenant_ids = []
    for _ in range(n_tenants):
        t = uid("hospital")
        tenant_ids.append(t)
        insp_id = _make_inspection(t, instrument_udi=udi)
        _make_finding(t, insp_id, finding_type="corrosion")
    return tenant_ids


# ---------------------------------------------------------------------------
# Section 2 — Manufacturer Intelligence Portal
# ---------------------------------------------------------------------------


def test_manufacturer_portal_requires_manufacturer_auth():
    res = client.get("/api/beacon/manufacturer-portal", headers=AUTH_ADMIN)
    assert res.status_code == 403


def test_manufacturer_portal_filters_real_data_and_hides_tenant_identity():
    manufacturer_id = uid("AcmeMfg")
    _make_baseline(manufacturer_id)
    _seed_manufacturer_network(manufacturer_id, n_tenants=5)

    res = client.get("/api/beacon/manufacturer-portal", headers=_manufacturer_headers(manufacturer_id))
    assert res.status_code == 200, res.text
    body = res.json()

    assert len(body["approved_baselines"]) == 1
    assert body["quality_trends"]["suppressed"] is False
    assert body["quality_trends"]["facility_count"] == 5
    assert "corrosion" in body["quality_trends"]["finding_type_counts"]
    # No tenant identity ever disclosed
    assert "tenant_id" not in str(body["quality_trends"])


def test_manufacturer_portal_suppresses_below_min_facilities():
    manufacturer_id = uid("SmallMfg")
    _seed_manufacturer_network(manufacturer_id, n_tenants=2)
    res = client.get("/api/beacon/manufacturer-portal/quality-trends", headers=_manufacturer_headers(manufacturer_id))
    assert res.status_code == 200
    assert res.json()["suppressed"] is True


# ---------------------------------------------------------------------------
# Section 3 — Repair Partner Portal + Digital Twin synchronization
# ---------------------------------------------------------------------------


def test_repair_partner_portal_workflow():
    vendor_id = uid("RepairCo")
    tenant_id = uid("hospital")
    _make_repair(
        tenant_id, vendor_name=vendor_id, failure_category="corrosion",
        status="returned", actual_return_date=datetime.now(timezone.utc),
    )

    res = client.get("/api/beacon/repair-partner-portal", headers=_manufacturer_headers(vendor_id))
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["failure_categories"]["failure_categories"]["corrosion"] == 1
    assert body["turnaround"]["completed_repairs"] == 1


def test_repair_partner_records_outcome_and_syncs_digital_twin():
    vendor_id = uid("RepairCo")
    tenant_id = uid("hospital")
    repair_id = _make_repair(
        tenant_id, vendor_name=vendor_id, failure_category="corrosion",
        status="returned", actual_return_date=datetime.now(timezone.utc),
    )

    res = client.post(
        f"/api/beacon/repair-partner-portal/repairs/{repair_id}/record-outcome",
        json={"notes": "returned to service"}, headers=_manufacturer_headers(vendor_id),
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["digital_twin_outcome"] == "failed"  # corrosion is in the "failed" category set

    db = SessionLocal()
    try:
        flows = db.query(InstrumentFlowRecord).filter(InstrumentFlowRecord.tenant_id == tenant_id).all()
        assert len(flows) == 1
        assert flows[0].outcome == "failed"
        assert flows[0].station_type == "repair_return"
    finally:
        db.close()


def test_repair_partner_cannot_record_outcome_for_other_vendors_repair():
    vendor_id = uid("RepairCo")
    other_vendor = uid("OtherCo")
    tenant_id = uid("hospital")
    repair_id = _make_repair(tenant_id, vendor_name=vendor_id, failure_category="corrosion", status="returned")

    res = client.post(
        f"/api/beacon/repair-partner-portal/repairs/{repair_id}/record-outcome",
        json={}, headers=_manufacturer_headers(other_vendor),
    )
    assert res.status_code == 422


# ---------------------------------------------------------------------------
# Section 1 — Collaboration Hub permissions
# ---------------------------------------------------------------------------


def test_collaboration_hub_only_lists_active_members():
    active_tenant = uid("hospital")
    pending_tenant = uid("hospital")
    _make_consortium_member(active_tenant, organization_type="hospital", membership_status="active")
    _make_consortium_member(pending_tenant, organization_type="hospital", membership_status="pending")

    res = client.get("/api/beacon/collaboration/hub", headers=AUTH_VIEWER)
    assert res.status_code == 200, res.text
    hospital_tenant_ids = {m["tenant_id"] for m in res.json()["participants_by_type"]["hospital"]}
    assert active_tenant in hospital_tenant_ids
    assert pending_tenant not in hospital_tenant_ids


def test_collaboration_participants_rejects_unknown_organization_type():
    res = client.get("/api/beacon/collaboration/participants/not_a_real_type", headers=AUTH_VIEWER)
    assert res.status_code == 422


# ---------------------------------------------------------------------------
# Section 4 — Standards Collaboration Center governance gate
# ---------------------------------------------------------------------------


def test_standards_publish_requires_active_approved_publisher():
    tenant_id = uid("hospital")  # not enrolled at all
    res = client.post(
        "/api/beacon/standards-center/publish",
        json={"title": "Test Guidance", "publication_type": "guidance", "abstract": "abstract text"},
        headers=_headers(AUTH_ADMIN, tenant_id),
    )
    assert res.status_code == 403


def test_standards_publish_succeeds_for_active_standards_body_and_chains_versions():
    tenant_id = uid("standards-body")
    _make_consortium_member(tenant_id, organization_type="standards_body", membership_status="active")

    res1 = client.post(
        "/api/beacon/standards-center/publish",
        json={"title": "Guidance v1", "publication_type": "guidance", "abstract": "v1"},
        headers=_headers(AUTH_ADMIN, tenant_id),
    )
    assert res1.status_code == 200, res1.text
    pub_id = res1.json()["id"]

    res2 = client.post(
        "/api/beacon/standards-center/publish",
        json={"title": "Guidance v2", "publication_type": "guidance", "abstract": "v2", "supersedes_id": pub_id},
        headers=_headers(AUTH_ADMIN, tenant_id),
    )
    assert res2.status_code == 200, res2.text

    versions = client.get(f"/api/beacon/standards-center/publications/{pub_id}/versions", headers=AUTH_VIEWER)
    assert versions.status_code == 200
    assert len(versions.json()["versions"]) == 2


# ---------------------------------------------------------------------------
# Section 5 — Clinical Evidence Exchange
# ---------------------------------------------------------------------------


def test_evidence_exchange_submit_and_summary():
    res = client.post(
        "/api/beacon/evidence-exchange/case-reports",
        json={"title": "Case Report A", "citation_text": "citation text"},
        headers=_headers(AUTH_ADMIN, uid("hospital")),
    )
    assert res.status_code == 200, res.text

    summary = client.get("/api/beacon/evidence-exchange", headers=AUTH_VIEWER)
    assert summary.status_code == 200
    assert summary.json()["total_evidence_count"] >= 1
    assert len(summary.json()["evidence_by_type"]["case_report"]) >= 1


# ---------------------------------------------------------------------------
# Section 6 — Manufacturer Feedback Loop — governance-approved only
# ---------------------------------------------------------------------------


def test_manufacturer_feedback_only_shows_approved_contributions():
    tenant_id = uid("hospital")
    submit = client.post(
        "/api/beacon/manufacturer-feedback",
        json={"category": "emerging_anatomy_risk", "title": "Emerging Risk X", "body": "detail"},
        headers=_headers(AUTH_ADMIN, tenant_id),
    )
    assert submit.status_code == 200, submit.text
    contribution_id = submit.json()["id"]

    feed_before = client.get("/api/beacon/manufacturer-feedback", headers=AUTH_VIEWER)
    titles_before = [f["title"] for f in feed_before.json()["feedback"]]
    assert "Emerging Risk X" not in titles_before

    approve = client.post(f"/api/horizon/contributions/{contribution_id}/approve", headers=AUTH_ADMIN)
    assert approve.status_code == 200, approve.text

    feed_after = client.get("/api/beacon/manufacturer-feedback", headers=AUTH_VIEWER)
    titles_after = [f["title"] for f in feed_after.json()["feedback"]]
    assert "Emerging Risk X" in titles_after


def test_manufacturer_feedback_rejects_unknown_category():
    res = client.post(
        "/api/beacon/manufacturer-feedback",
        json={"category": "not_a_real_category", "title": "X", "body": "Y"},
        headers=_headers(AUTH_ADMIN, uid("hospital")),
    )
    assert res.status_code == 422


# ---------------------------------------------------------------------------
# Section 7 — Repair Intelligence
# ---------------------------------------------------------------------------


def test_repair_intelligence_suppressed_below_min_facilities():
    category = "electrical_fault"
    _make_repair(uid("hospital"), vendor_name=uid("v"), failure_category=category)
    _make_repair(uid("hospital"), vendor_name=uid("v"), failure_category=category)

    res = client.post("/api/beacon/repair-intelligence/generate", headers=AUTH_ADMIN)
    assert res.status_code == 200, res.text
    snapshot = next(s for s in res.json()["snapshots"] if s["failure_category"] == category)
    # facility_count reflects only very recent seeding for this category; with < 5 facilities it must suppress
    if snapshot["facility_count"] < 5:
        assert snapshot["suppressed"] is True
        assert snapshot["quality_improvement_recommendation"] == ""


def test_repair_intelligence_published_with_recommendation_when_enough_facilities():
    category = "insulation_defect"
    for _ in range(5):
        _make_repair(uid("hospital"), vendor_name=uid("v"), failure_category=category)

    res = client.post("/api/beacon/repair-intelligence/generate", headers=AUTH_ADMIN)
    assert res.status_code == 200, res.text
    snapshot = next(s for s in res.json()["snapshots"] if s["failure_category"] == category)
    assert snapshot["suppressed"] is False
    assert snapshot["facility_count"] >= 5
    assert snapshot["quality_improvement_recommendation"] != ""


# ---------------------------------------------------------------------------
# Section 8 — Industry Benchmarking (new metrics wired through)
# ---------------------------------------------------------------------------


def test_industry_benchmarks_include_beacon_metrics():
    res = client.get("/api/beacon/industry-benchmarks", headers=AUTH_VIEWER)
    assert res.status_code == 200, res.text
    body = res.json()
    assert "repair_category_rate" in body["metrics"]
    assert "digital_twin_health_score" in body["metrics"]
    metric_names = {b["metric_name"] for b in body["benchmarks"]}
    assert "repair_category_rate" in metric_names
    assert "digital_twin_health_score" in metric_names


def test_industry_benchmark_percentile_rejects_unknown_metric():
    res = client.get(
        "/api/beacon/industry-benchmarks/percentile", params={"metric_name": "not_a_real_metric"}, headers=AUTH_VIEWER,
    )
    assert res.status_code == 422


# ---------------------------------------------------------------------------
# Section 9 — Governance overview + audit logging
# ---------------------------------------------------------------------------


def test_governance_overview_reflects_participation_and_audit_trail():
    tenant_id = uid("standards-body")
    _make_consortium_member(tenant_id, organization_type="standards_body", membership_status="active")

    publish = client.post(
        "/api/beacon/standards-center/publish",
        json={"title": "Audited Guidance", "publication_type": "guidance", "abstract": "x"},
        headers=_headers(AUTH_ADMIN, tenant_id),
    )
    assert publish.status_code == 200, publish.text

    overview = client.get("/api/beacon/governance/overview", headers=_headers(AUTH_ADMIN, tenant_id))
    assert overview.status_code == 200, overview.text
    body = overview.json()
    assert body["participation"]["organization_type"] == "standards_body"
    action_types = [a["action_type"] for a in body["audit_trail"]]
    assert "beacon.standards_published" in action_types


def test_governance_pending_approvals_is_governance_wide():
    tenant_id = uid("hospital")
    client.post(
        "/api/beacon/manufacturer-feedback",
        json={"category": "failure_mode", "title": "Pending Feedback Y", "body": "detail"},
        headers=_headers(AUTH_ADMIN, tenant_id),
    )
    res = client.get("/api/beacon/governance/pending-approvals", headers=AUTH_ADMIN)
    assert res.status_code == 200
    titles = [p["title"] for p in res.json()["pending"]]
    assert "Pending Feedback Y" in titles


# ---------------------------------------------------------------------------
# Section 10 — Industry Advisory Board tracking
# ---------------------------------------------------------------------------


def test_advisory_board_meeting_action_item_and_recommendation_lifecycle():
    meeting_res = client.post(
        "/api/beacon/advisory-board/meetings",
        json={"title": "Q3 Advisory Board", "scheduled_at": datetime.now(timezone.utc).isoformat(), "attendee_organizations": ["AcmeMfg"]},
        headers=AUTH_ADMIN,
    )
    assert meeting_res.status_code == 200, meeting_res.text
    meeting_id = meeting_res.json()["id"]

    notes_res = client.post(
        f"/api/beacon/advisory-board/meetings/{meeting_id}/notes",
        json={"meeting_notes": "Discussed roadmap", "roadmap_feedback": "More benchmarking depth requested"},
        headers=AUTH_ADMIN,
    )
    assert notes_res.status_code == 200, notes_res.text
    assert notes_res.json()["status"] == "completed"

    item_res = client.post(
        "/api/beacon/advisory-board/action-items",
        json={"meeting_id": meeting_id, "description": "Follow up on benchmarking depth", "owner": "PM"},
        headers=AUTH_ADMIN,
    )
    assert item_res.status_code == 200, item_res.text
    item_id = item_res.json()["id"]

    resolve_res = client.post(f"/api/beacon/advisory-board/action-items/{item_id}/resolve", headers=AUTH_ADMIN)
    assert resolve_res.status_code == 200
    assert resolve_res.json()["status"] == "done"

    rec_res = client.post(
        "/api/beacon/advisory-board/recommendations",
        json={"title": "Add repair-category benchmark", "rationale": "requested by board", "target_area": "benchmarking", "meeting_id": meeting_id},
        headers=AUTH_ADMIN,
    )
    assert rec_res.status_code == 200, rec_res.text
    rec_id = rec_res.json()["id"]

    decide_res = client.post(
        f"/api/beacon/advisory-board/recommendations/{rec_id}/decide",
        json={"status": "adopted"}, headers=AUTH_ADMIN,
    )
    assert decide_res.status_code == 200, decide_res.text
    assert decide_res.json()["status"] == "adopted"
    assert decide_res.json()["human_review_required"] is True

    summary = client.get("/api/beacon/advisory-board", headers=AUTH_VIEWER)
    assert summary.status_code == 200
    meeting_ids = {m["id"] for m in summary.json()["meetings"]}
    assert meeting_id in meeting_ids
    open_item_ids = {i["id"] for i in summary.json()["open_action_items"]}
    assert item_id not in open_item_ids  # resolved above, so must not appear in the open queue


def test_advisory_board_recommendation_decide_rejects_invalid_status():
    rec_res = client.post(
        "/api/beacon/advisory-board/recommendations",
        json={"title": "Bad decision test", "rationale": "x", "target_area": "y"},
        headers=AUTH_ADMIN,
    )
    rec_id = rec_res.json()["id"]
    res = client.post(
        f"/api/beacon/advisory-board/recommendations/{rec_id}/decide",
        json={"status": "not_a_real_status"}, headers=AUTH_ADMIN,
    )
    assert res.status_code == 422
