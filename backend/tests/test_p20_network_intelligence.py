"""P20: Network Intelligence Platform & Market Leadership — test suite.

Covers all 5 phases:
  1 – National SPD Registry & intelligence sharing
  2 – Instrument Lifecycle Intelligence
  3 – Recall Early Warning System
  4 – Research Data Exchange
  5 – Executive Intelligence dashboards & snapshots

All tests use ENABLE_DEV_AUTH + DEV_AUTH_TOKEN (dev-token).
"""
import time

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
HEADERS = {"Authorization": "Bearer dev-token"}
TS = str(int(time.time()))[-6:]
TENANT = f"p20-{TS}"
TENANT2 = f"p20b-{TS}"


# ---------------------------------------------------------------------------
# Phase 1 — SPD Registry
# ---------------------------------------------------------------------------

def test_register_facility():
    r = client.post("/api/network-intelligence/registry", json={
        "tenant_id": TENANT, "facility_type": "hospital",
        "bed_count_range": "300-499", "region": "northeast",
        "participation_tier": "contributor",
    }, headers=HEADERS)
    assert r.status_code == 201
    body = r.json()
    assert body["facility_pseudonym"].startswith("SPD-")
    assert body["participation_tier"] == "contributor"


def test_register_facility_duplicate_returns_409():
    payload = {"tenant_id": TENANT + "-dup", "facility_type": "hospital"}
    client.post("/api/network-intelligence/registry", json=payload, headers=HEADERS)
    r = client.post("/api/network-intelligence/registry", json=payload, headers=HEADERS)
    assert r.status_code == 409


def test_get_registry_own_record():
    tid = TENANT + "-get"
    client.post("/api/network-intelligence/registry", json={"tenant_id": tid, "facility_type": "asc"},
                headers=HEADERS)
    r = client.get(f"/api/network-intelligence/registry?tenant_id={tid}", headers=HEADERS)
    assert r.status_code == 200
    assert r.json()["facility_type"] == "asc"


def test_get_registry_not_found():
    r = client.get("/api/network-intelligence/registry?tenant_id=nobody", headers=HEADERS)
    assert r.status_code == 404


def test_network_summary_below_k_floor():
    r = client.get("/api/network-intelligence/registry/network-summary", headers=HEADERS)
    assert r.status_code == 200
    body = r.json()
    # May be suppressed or not depending on how many registrations exist;
    # just verify the response has the right shape
    assert "suppressed" in body or "total_active_facilities" in body


def test_intelligence_sharing_agreement():
    r = client.post("/api/network-intelligence/sharing-agreements", json={
        "tenant_id": TENANT, "agreed_by": "admin@test.com",
        "sharing_scope": "benchmark",
    }, headers=HEADERS)
    assert r.status_code == 201
    assert r.json()["status"] == "active"


def test_withdraw_agreement():
    r = client.post("/api/network-intelligence/sharing-agreements", json={
        "tenant_id": TENANT + "-withdraw", "agreed_by": "admin@test.com",
        "sharing_scope": "benchmark",
    }, headers=HEADERS)
    agreement_id = r.json()["id"]
    r2 = client.delete(
        f"/api/network-intelligence/sharing-agreements/{agreement_id}?withdrawn_by=admin",
        headers=HEADERS)
    assert r2.status_code == 200
    assert r2.json()["status"] == "withdrawn"


def test_withdraw_already_withdrawn_returns_409():
    r = client.post("/api/network-intelligence/sharing-agreements", json={
        "tenant_id": TENANT + "-w2", "agreed_by": "admin@test.com",
        "sharing_scope": "benchmark",
    }, headers=HEADERS)
    aid = r.json()["id"]
    client.delete(f"/api/network-intelligence/sharing-agreements/{aid}?withdrawn_by=admin",
                  headers=HEADERS)
    r2 = client.delete(f"/api/network-intelligence/sharing-agreements/{aid}?withdrawn_by=admin",
                       headers=HEADERS)
    assert r2.status_code == 409


def test_aggregate_snapshot_below_k_floor_rejected():
    r = client.post("/api/network-intelligence/aggregate-snapshots", json={
        "metric_name": "pass_rate", "n_participants": 3, "p50": 92.0, "mean": 91.5,
    }, headers=HEADERS)
    assert r.status_code == 409


def test_aggregate_snapshot_created():
    r = client.post("/api/network-intelligence/aggregate-snapshots", json={
        "metric_name": "pass_rate", "n_participants": 10, "p50": 92.0, "mean": 91.5,
        "p25": 88.0, "p75": 95.0, "p90": 98.0, "captured_by": "steward",
    }, headers=HEADERS)
    assert r.status_code == 201
    assert r.json()["metric_name"] == "pass_rate"


def test_list_aggregate_snapshots():
    r = client.get("/api/network-intelligence/aggregate-snapshots", headers=HEADERS)
    assert r.status_code == 200
    assert "snapshots" in r.json()
    assert "disclaimer" in r.json()


# ---------------------------------------------------------------------------
# Phase 2 — Instrument Lifecycle
# ---------------------------------------------------------------------------

def test_create_lifecycle_record():
    r = client.post("/api/network-intelligence/lifecycle/instruments", json={
        "tenant_id": TENANT, "facility_id": "F1",
        "instrument_uid": "INST-001", "manufacturer_name": "AcmeSurg",
        "model_name": "Laparoscope-X", "instrument_category": "laparoscope",
        "udi": "00888888001234", "acquisition_source": "new_purchase",
    }, headers=HEADERS)
    assert r.status_code == 201
    assert r.json()["lifecycle_status"] == "active"


def test_create_lifecycle_record_duplicate_returns_409():
    payload = {
        "tenant_id": TENANT + "-lc", "facility_id": "F1",
        "instrument_uid": "INST-DUP", "manufacturer_name": "AcmeSurg",
        "model_name": "Model-A", "instrument_category": "forceps",
    }
    client.post("/api/network-intelligence/lifecycle/instruments", json=payload, headers=HEADERS)
    r = client.post("/api/network-intelligence/lifecycle/instruments", json=payload, headers=HEADERS)
    assert r.status_code == 409


def test_list_lifecycle_records():
    client.post("/api/network-intelligence/lifecycle/instruments", json={
        "tenant_id": TENANT + "-list", "facility_id": "F1",
        "instrument_uid": "INST-LST", "manufacturer_name": "AcmeSurg",
        "model_name": "Model-B", "instrument_category": "retractor",
    }, headers=HEADERS)
    r = client.get(f"/api/network-intelligence/lifecycle/instruments?tenant_id={TENANT}-list",
                   headers=HEADERS)
    assert r.status_code == 200
    assert len(r.json()["instruments"]) >= 1


def test_log_lifecycle_event_inspected():
    tid = TENANT + "-ev"
    client.post("/api/network-intelligence/lifecycle/instruments", json={
        "tenant_id": tid, "facility_id": "F1",
        "instrument_uid": "INST-EV1", "manufacturer_name": "AcmeSurg",
        "model_name": "Trocar-Y", "instrument_category": "trocar",
    }, headers=HEADERS)
    r = client.post("/api/network-intelligence/lifecycle/events", json={
        "tenant_id": tid, "instrument_uid": "INST-EV1",
        "event_type": "inspected", "outcome": "pass",
        "performed_by": "tech_a",
    }, headers=HEADERS)
    assert r.status_code == 201
    assert r.json()["event_type"] == "inspected"


def test_log_lifecycle_event_defect_updates_rate():
    tid = TENANT + "-defect"
    client.post("/api/network-intelligence/lifecycle/instruments", json={
        "tenant_id": tid, "facility_id": "F1",
        "instrument_uid": "INST-DEF", "manufacturer_name": "AcmeSurg",
        "model_name": "Model-C", "instrument_category": "scissors",
    }, headers=HEADERS)
    # 2 inspections, 1 fail → defect_rate = 0.5
    client.post("/api/network-intelligence/lifecycle/events", json={
        "tenant_id": tid, "instrument_uid": "INST-DEF",
        "event_type": "inspected", "outcome": "pass"}, headers=HEADERS)
    client.post("/api/network-intelligence/lifecycle/events", json={
        "tenant_id": tid, "instrument_uid": "INST-DEF",
        "event_type": "inspected", "outcome": "fail"}, headers=HEADERS)
    recs = client.get(f"/api/network-intelligence/lifecycle/instruments?tenant_id={tid}",
                      headers=HEADERS).json()["instruments"]
    assert recs[0]["defect_rate"] == pytest.approx(0.5, abs=0.01)


def test_log_lifecycle_event_retired():
    tid = TENANT + "-retire"
    client.post("/api/network-intelligence/lifecycle/instruments", json={
        "tenant_id": tid, "facility_id": "F1",
        "instrument_uid": "INST-RET", "manufacturer_name": "AcmeSurg",
        "model_name": "Model-D", "instrument_category": "clamp",
    }, headers=HEADERS)
    r = client.post("/api/network-intelligence/lifecycle/events", json={
        "tenant_id": tid, "instrument_uid": "INST-RET",
        "event_type": "retired", "notes": "end_of_life",
    }, headers=HEADERS)
    assert r.status_code == 201
    recs = client.get(f"/api/network-intelligence/lifecycle/instruments?tenant_id={tid}",
                      headers=HEADERS).json()["instruments"]
    assert recs[0]["lifecycle_status"] == "retired"


def test_lifecycle_event_invalid_type_returns_400():
    tid = TENANT + "-bad"
    client.post("/api/network-intelligence/lifecycle/instruments", json={
        "tenant_id": tid, "facility_id": "F1",
        "instrument_uid": "INST-BAD", "manufacturer_name": "AcmeSurg",
        "model_name": "Model-E", "instrument_category": "needle",
    }, headers=HEADERS)
    r = client.post("/api/network-intelligence/lifecycle/events", json={
        "tenant_id": tid, "instrument_uid": "INST-BAD",
        "event_type": "invented_event_type",
    }, headers=HEADERS)
    assert r.status_code == 400


def test_list_lifecycle_events():
    tid = TENANT + "-evlist"
    client.post("/api/network-intelligence/lifecycle/instruments", json={
        "tenant_id": tid, "facility_id": "F1",
        "instrument_uid": "INST-EL", "manufacturer_name": "AcmeSurg",
        "model_name": "Model-F", "instrument_category": "grasper",
    }, headers=HEADERS)
    client.post("/api/network-intelligence/lifecycle/events", json={
        "tenant_id": tid, "instrument_uid": "INST-EL", "event_type": "inspected",
        "outcome": "pass"}, headers=HEADERS)
    r = client.get(f"/api/network-intelligence/lifecycle/events?tenant_id={tid}&instrument_uid=INST-EL",
                   headers=HEADERS)
    assert r.status_code == 200
    assert len(r.json()["events"]) == 1


def test_lifecycle_benchmark_below_k_floor_rejected():
    r = client.post("/api/network-intelligence/lifecycle/benchmarks", json={
        "instrument_category": "trocar", "metric_name": "median_lifespan_cycles",
        "n_facilities": 4, "p50": 200.0, "mean": 195.0,
    }, headers=HEADERS)
    assert r.status_code == 409


def test_lifecycle_benchmark_created():
    r = client.post("/api/network-intelligence/lifecycle/benchmarks", json={
        "instrument_category": "trocar", "metric_name": "median_lifespan_cycles",
        "n_facilities": 8, "p50": 220.0, "mean": 215.0,
    }, headers=HEADERS)
    assert r.status_code == 201


def test_list_lifecycle_benchmarks():
    r = client.get("/api/network-intelligence/lifecycle/benchmarks", headers=HEADERS)
    assert r.status_code == 200
    assert "disclaimer" in r.json()


# ---------------------------------------------------------------------------
# Phase 3 — Recall Early Warning
# ---------------------------------------------------------------------------

def test_create_recall_early_warning():
    r = client.post("/api/network-intelligence/recall-early-warning", json={
        "instrument_category": "laparoscope",
        "finding_type": "contamination",
        "n_facilities_reporting": 5,
        "first_observed": "2026-01-01T00:00:00",
        "last_observed": "2026-06-01T00:00:00",
        "anomaly_score": 0.72,
        "warning_level": "advisory",
        "manufacturer_pseudonym": "MFR-ABC",
    }, headers=HEADERS)
    assert r.status_code == 201
    body = r.json()
    assert body["signal_ref"].startswith("REW-")
    assert body["human_review_required"] is True


def test_recall_warning_below_floor_rejected():
    r = client.post("/api/network-intelligence/recall-early-warning", json={
        "instrument_category": "forceps",
        "finding_type": "defect",
        "n_facilities_reporting": 2,
        "first_observed": "2026-01-01T00:00:00",
        "last_observed": "2026-06-01T00:00:00",
        "anomaly_score": 0.5,
        "warning_level": "watch",
    }, headers=HEADERS)
    assert r.status_code == 409


def test_list_recall_early_warnings():
    r = client.get("/api/network-intelligence/recall-early-warning", headers=HEADERS)
    assert r.status_code == 200
    assert "disclaimer" in r.json()


def test_review_recall_warning():
    r = client.post("/api/network-intelligence/recall-early-warning", json={
        "instrument_category": "retractor",
        "finding_type": "defect",
        "n_facilities_reporting": 4,
        "first_observed": "2026-01-01T00:00:00",
        "last_observed": "2026-06-01T00:00:00",
        "anomaly_score": 0.6,
        "warning_level": "watch",
    }, headers=HEADERS)
    wid = r.json()["id"]
    r2 = client.post(
        f"/api/network-intelligence/recall-early-warning/{wid}/review"
        "?decision=monitor&reviewed_by=steward_alice",
        headers=HEADERS)
    assert r2.status_code == 200
    assert r2.json()["status"] == "under_review"


def test_review_recall_warning_escalate():
    r = client.post("/api/network-intelligence/recall-early-warning", json={
        "instrument_category": "trocar",
        "finding_type": "failure",
        "n_facilities_reporting": 7,
        "first_observed": "2026-02-01T00:00:00",
        "last_observed": "2026-06-10T00:00:00",
        "anomaly_score": 0.91,
        "warning_level": "alert",
    }, headers=HEADERS)
    wid = r.json()["id"]
    r2 = client.post(
        f"/api/network-intelligence/recall-early-warning/{wid}/review"
        "?decision=escalate&reviewed_by=steward_bob",
        headers=HEADERS)
    assert r2.status_code == 200
    assert r2.json()["status"] == "escalated"


def test_review_invalid_decision_returns_400():
    r = client.post("/api/network-intelligence/recall-early-warning", json={
        "instrument_category": "scissors",
        "finding_type": "corrosion",
        "n_facilities_reporting": 3,
        "first_observed": "2026-01-01T00:00:00",
        "last_observed": "2026-06-01T00:00:00",
        "anomaly_score": 0.4,
        "warning_level": "watch",
    }, headers=HEADERS)
    wid = r.json()["id"]
    r2 = client.post(
        f"/api/network-intelligence/recall-early-warning/{wid}/review"
        "?decision=publish&reviewed_by=anyone",
        headers=HEADERS)
    assert r2.status_code == 400


def test_anomaly_detection_run_logged():
    r = client.post(
        "/api/network-intelligence/anomaly-detection/run"
        "?triggered_by=manual&categories_scanned=12&signals_surfaced=2&signals_escalated=0",
        headers=HEADERS)
    assert r.status_code == 201
    assert r.json()["run_status"] == "complete"


def test_list_anomaly_runs():
    r = client.get("/api/network-intelligence/anomaly-detection/runs", headers=HEADERS)
    assert r.status_code == 200
    assert "runs" in r.json()


def test_manufacturer_profile_below_k_floor_rejected():
    r = client.post("/api/network-intelligence/manufacturer-intelligence", json={
        "manufacturer_pseudonym": "MFR-XYZ",
        "instrument_category": "forceps",
        "n_facilities_contributing": 3,
        "network_defect_rate": 0.05,
        "network_pass_rate": 0.95,
        "network_repair_rate": 0.02,
    }, headers=HEADERS)
    assert r.status_code == 409


def test_manufacturer_profile_created():
    r = client.post("/api/network-intelligence/manufacturer-intelligence", json={
        "manufacturer_pseudonym": "MFR-AAA",
        "instrument_category": "laparoscope",
        "n_facilities_contributing": 10,
        "network_defect_rate": 0.04,
        "network_pass_rate": 0.96,
        "network_repair_rate": 0.015,
        "intelligence_grade": "A",
    }, headers=HEADERS)
    assert r.status_code == 201


def test_list_manufacturer_profiles():
    r = client.get("/api/network-intelligence/manufacturer-intelligence", headers=HEADERS)
    assert r.status_code == 200
    assert "disclaimer" in r.json()


# ---------------------------------------------------------------------------
# Phase 4 — Research Data Exchange
# ---------------------------------------------------------------------------

def test_create_research_dataset():
    r = client.post("/api/network-intelligence/research/datasets", json={
        "title": "SPD Defect Rate 2024–2026",
        "dataset_type": "benchmark_series",
        "n_facilities_contributing": 20,
        "n_records": 5000,
        "created_by": "researcher_alice",
    }, headers=HEADERS)
    assert r.status_code == 201
    assert r.json()["release_status"] == "draft"
    assert r.json()["dataset_ref"].startswith("RDS-")


def test_research_dataset_below_k_floor_rejected():
    r = client.post("/api/network-intelligence/research/datasets", json={
        "title": "Tiny Dataset",
        "dataset_type": "lifecycle_cohort",
        "n_facilities_contributing": 4,
        "n_records": 100,
        "created_by": "researcher_bob",
    }, headers=HEADERS)
    assert r.status_code == 409


def test_approve_research_dataset():
    r = client.post("/api/network-intelligence/research/datasets", json={
        "title": "Lifecycle Study 2026",
        "dataset_type": "lifecycle_cohort",
        "n_facilities_contributing": 12,
        "n_records": 800,
        "created_by": "researcher_carol",
    }, headers=HEADERS)
    ds_id = r.json()["id"]
    r2 = client.post(
        f"/api/network-intelligence/research/datasets/{ds_id}/approve?approved_by=irb_board",
        headers=HEADERS)
    assert r2.status_code == 200
    assert r2.json()["release_status"] == "approved"


def test_release_research_dataset():
    r = client.post("/api/network-intelligence/research/datasets", json={
        "title": "Recall Signal Cohort",
        "dataset_type": "recall_signal_cohort",
        "n_facilities_contributing": 15,
        "n_records": 300,
        "created_by": "researcher_dan",
    }, headers=HEADERS)
    ds_id = r.json()["id"]
    client.post(f"/api/network-intelligence/research/datasets/{ds_id}/approve?approved_by=irb",
                headers=HEADERS)
    r3 = client.post(f"/api/network-intelligence/research/datasets/{ds_id}/release",
                     headers=HEADERS)
    assert r3.status_code == 200
    assert r3.json()["release_status"] == "released"


def test_release_unapproved_dataset_rejected():
    r = client.post("/api/network-intelligence/research/datasets", json={
        "title": "Unapproved Set",
        "dataset_type": "benchmark_series",
        "n_facilities_contributing": 6,
        "n_records": 200,
        "created_by": "researcher_ed",
    }, headers=HEADERS)
    ds_id = r.json()["id"]
    r2 = client.post(f"/api/network-intelligence/research/datasets/{ds_id}/release",
                     headers=HEADERS)
    assert r2.status_code == 409


def test_create_research_study_requires_claims_acknowledgment():
    r = client.post("/api/network-intelligence/research/studies", json={
        "title": "SPD Quality Study",
        "principal_investigator": "Dr. Smith",
        "claims_discipline_acknowledged": False,
    }, headers=HEADERS)
    assert r.status_code == 422


def test_create_research_study():
    r = client.post("/api/network-intelligence/research/studies", json={
        "title": "SPD Quality Study 2026",
        "principal_investigator": "Dr. Jones",
        "institution": "State University Medical Center",
        "study_type": "observational",
        "claims_discipline_acknowledged": True,
    }, headers=HEADERS)
    assert r.status_code == 201
    assert r.json()["study_ref"].startswith("STU-")


def test_record_publication_with_causation_claim_rejected():
    r = client.post("/api/network-intelligence/research/publications", json={
        "study_ref": "STU-2026-FAKE",
        "publication_title": "Causation Study",
        "causation_claim_present": True,
    }, headers=HEADERS)
    assert r.status_code == 422


def test_record_publication():
    r = client.post("/api/network-intelligence/research/publications", json={
        "study_ref": "STU-2026-FAKE",
        "publication_title": "Observational Analysis of SPD Defect Trends",
        "journal": "Journal of Sterile Processing",
        "causation_claim_present": False,
    }, headers=HEADERS)
    assert r.status_code == 201
    assert r.json()["governance_cleared"] is False  # requires separate clearance


def test_list_research_datasets():
    r = client.get("/api/network-intelligence/research/datasets", headers=HEADERS)
    assert r.status_code == 200
    assert "disclaimer" in r.json()


# ---------------------------------------------------------------------------
# Phase 5 — Executive Intelligence
# ---------------------------------------------------------------------------

def test_create_executive_dashboard():
    r = client.post("/api/network-intelligence/executive/dashboards", json={
        "tenant_id": TENANT, "dashboard_name": "Q2 2026 Network Overview",
        "dashboard_type": "national_benchmark", "created_by": "ceo@hospital.org",
    }, headers=HEADERS)
    assert r.status_code == 201
    assert r.json()["dashboard_type"] == "national_benchmark"


def test_create_dashboard_invalid_type_returns_400():
    r = client.post("/api/network-intelligence/executive/dashboards", json={
        "tenant_id": TENANT, "dashboard_name": "Bad Dashboard",
        "dashboard_type": "invalid_type", "created_by": "admin",
    }, headers=HEADERS)
    assert r.status_code == 400


def test_list_executive_dashboards():
    r = client.get(f"/api/network-intelligence/executive/dashboards?tenant_id={TENANT}",
                   headers=HEADERS)
    assert r.status_code == 200
    assert "dashboards" in r.json()


def test_capture_executive_snapshot():
    r = client.post("/api/network-intelligence/executive/snapshots", json={
        "tenant_id": TENANT,
        "network_pass_rate_p50": 92.5,
        "tenant_pass_rate": 94.1,
        "network_defect_rate_p50": 3.2,
        "tenant_defect_rate": 2.8,
        "open_early_warnings_network": 2,
        "tenant_recall_exposure_score": 12.5,
        "accreditation_readiness_score": 88.0,
        "network_percentile": 71.0,
        "captured_by": "steward",
    }, headers=HEADERS)
    assert r.status_code == 201
    assert r.json()["human_review_required"] is True


def test_list_executive_snapshots():
    r = client.get(f"/api/network-intelligence/executive/snapshots?tenant_id={TENANT}",
                   headers=HEADERS)
    assert r.status_code == 200
    assert "disclaimer" in r.json()


def test_executive_network_intelligence_summary():
    r = client.get(
        f"/api/network-intelligence/executive/network-intelligence-summary?tenant_id={TENANT}",
        headers=HEADERS)
    assert r.status_code == 200
    body = r.json()
    assert "open_recall_early_warnings" in body
    assert "active_research_studies" in body
    assert body["human_review_required"] is True
    assert "disclaimer" in body


def test_tenant_isolation_lifecycle():
    """Lifecycle records from one tenant must not appear in another's query."""
    t1 = TENANT + "-iso1"
    t2 = TENANT + "-iso2"
    for t in (t1, t2):
        client.post("/api/network-intelligence/lifecycle/instruments", json={
            "tenant_id": t, "facility_id": "F1",
            "instrument_uid": f"INST-{t}", "manufacturer_name": "AcmeSurg",
            "model_name": "Model-ISO", "instrument_category": "clamp",
        }, headers=HEADERS)
    r1 = client.get(f"/api/network-intelligence/lifecycle/instruments?tenant_id={t1}",
                    headers=HEADERS).json()["instruments"]
    r2 = client.get(f"/api/network-intelligence/lifecycle/instruments?tenant_id={t2}",
                    headers=HEADERS).json()["instruments"]
    uids1 = {i["instrument_uid"] for i in r1}
    uids2 = {i["instrument_uid"] for i in r2}
    assert uids1.isdisjoint(uids2), "Tenant isolation violated: instrument_uids overlap"


# ---------------------------------------------------------------------------
# Tier 1 recommendations: compute-from-data, agreement gating, P15 promotion
# ---------------------------------------------------------------------------

def _seed_consenting_facility(tid, category, n_inspections, n_defects, scope="benchmark"):
    """Register a facility, sign a benchmark agreement, and feed it lifecycle data."""
    client.post("/api/network-intelligence/sharing-agreements", json={
        "tenant_id": tid, "agreed_by": "admin@test.com", "sharing_scope": scope,
    }, headers=HEADERS)
    uid = f"INST-{tid}"
    client.post("/api/network-intelligence/lifecycle/instruments", json={
        "tenant_id": tid, "facility_id": "F1", "instrument_uid": uid,
        "manufacturer_name": "AcmeSurg", "model_name": "M", "instrument_category": category,
    }, headers=HEADERS)
    for i in range(n_inspections):
        outcome = "fail" if i < n_defects else "pass"
        client.post("/api/network-intelligence/lifecycle/events", json={
            "tenant_id": tid, "instrument_uid": uid,
            "event_type": "inspected", "outcome": outcome,
        }, headers=HEADERS)
    return uid


def test_compute_benchmark_requires_consenting_floor():
    """Fewer than k consenting facilities → 409, even if data exists."""
    cat = f"computecat-a-{TS}"
    # Only 3 consenting facilities (< floor of 5)
    for i in range(3):
        _seed_consenting_facility(f"{TENANT}-ca{i}", cat, 4, 1)
    r = client.post(
        f"/api/network-intelligence/lifecycle/benchmarks/compute"
        f"?instrument_category={cat}&metric_name=defect_rate",
        headers=HEADERS)
    assert r.status_code == 409
    assert "k-anonymity" in r.json()["detail"]


def test_compute_benchmark_from_consenting_data():
    """>= k consenting facilities with data → benchmark computed in code."""
    cat = f"computecat-b-{TS}"
    for i in range(6):
        _seed_consenting_facility(f"{TENANT}-cb{i}", cat, 4, 1)  # defect_rate 0.25 each
    r = client.post(
        f"/api/network-intelligence/lifecycle/benchmarks/compute"
        f"?instrument_category={cat}&metric_name=defect_rate",
        headers=HEADERS)
    assert r.status_code == 201
    body = r.json()
    assert body["n_facilities"] == 6
    assert body["data_points"] == 6
    assert body["noise_applied"] is True
    # p50 should be near 0.25 but noised — sanity bound, not exact
    assert 0.0 <= body["p50"] <= 1.0


def test_compute_benchmark_excludes_non_consenting():
    """A facility without an active agreement must not count toward k or data."""
    cat = f"computecat-c-{TS}"
    # 5 consenting
    for i in range(5):
        _seed_consenting_facility(f"{TENANT}-cc{i}", cat, 4, 2)
    # 1 NON-consenting facility (no agreement) with data
    noconsent = f"{TENANT}-cc-noconsent"
    uid = f"INST-{noconsent}"
    client.post("/api/network-intelligence/lifecycle/instruments", json={
        "tenant_id": noconsent, "facility_id": "F1", "instrument_uid": uid,
        "manufacturer_name": "AcmeSurg", "model_name": "M", "instrument_category": cat,
    }, headers=HEADERS)
    client.post("/api/network-intelligence/lifecycle/events", json={
        "tenant_id": noconsent, "instrument_uid": uid,
        "event_type": "inspected", "outcome": "pass"}, headers=HEADERS)
    r = client.post(
        f"/api/network-intelligence/lifecycle/benchmarks/compute"
        f"?instrument_category={cat}&metric_name=defect_rate",
        headers=HEADERS)
    assert r.status_code == 201
    # Only the 5 consenting facilities count — not the 6th
    assert r.json()["n_facilities"] == 5


def test_compute_benchmark_invalid_metric():
    r = client.post(
        f"/api/network-intelligence/lifecycle/benchmarks/compute"
        f"?instrument_category=anything&metric_name=bogus_metric",
        headers=HEADERS)
    assert r.status_code == 400


def test_promote_requires_escalated_status():
    """A candidate (un-escalated) warning cannot be promoted."""
    r = client.post("/api/network-intelligence/recall-early-warning", json={
        "instrument_category": "laparoscope", "finding_type": "contamination",
        "n_facilities_reporting": 5,
        "first_observed": "2026-01-01T00:00:00", "last_observed": "2026-06-01T00:00:00",
        "anomaly_score": 0.8, "warning_level": "advisory",
    }, headers=HEADERS)
    wid = r.json()["id"]
    r2 = client.post(
        f"/api/network-intelligence/recall-early-warning/{wid}/promote?promoted_by=steward",
        headers=HEADERS)
    assert r2.status_code == 409


def test_promote_escalated_warning_to_recall_signal():
    """Escalated warning → formal P15 RecallSignal; idempotent on re-promote."""
    r = client.post("/api/network-intelligence/recall-early-warning", json={
        "instrument_category": "trocar", "finding_type": "failure",
        "n_facilities_reporting": 6,
        "first_observed": "2026-02-01T00:00:00", "last_observed": "2026-06-10T00:00:00",
        "anomaly_score": 0.93, "warning_level": "alert",
        "manufacturer_pseudonym": "MFR-PROMOTE",
    }, headers=HEADERS)
    wid = r.json()["id"]
    # Escalate first (human review gate)
    client.post(
        f"/api/network-intelligence/recall-early-warning/{wid}/review"
        "?decision=escalate&reviewed_by=steward_bob", headers=HEADERS)
    # Promote
    p = client.post(
        f"/api/network-intelligence/recall-early-warning/{wid}/promote?promoted_by=steward_bob",
        headers=HEADERS)
    assert p.status_code == 201
    body = p.json()
    assert body["signal_id"].startswith("RS-")
    assert body["signal_type"] == "recurring_failure"
    assert body["already_promoted"] is False
    # Idempotent re-promote
    p2 = client.post(
        f"/api/network-intelligence/recall-early-warning/{wid}/promote?promoted_by=steward_bob",
        headers=HEADERS)
    assert p2.json()["already_promoted"] is True
    assert p2.json()["signal_id"] == body["signal_id"]
