"""Regression suite — the deterministic placeholder must never populate a
production clinical outcome.

Every test here runs with the deterministic scorer OFF (the production default:
``AI_ALLOW_DEMO_SCORING`` unset → False), exercising the SAME path a deployed
pilot hits. With no eligible trained model the authoritative verdict is
AI_UNAVAILABLE, and no fabricated score, finding, probability, confidence, risk
level, clinical interpretation, mentor content, or baseline image-match percent
may appear on any clinician-facing surface (API response, inspection history, or
the printable clinical report). Real instrument identification, approved-baseline
metadata resolution, image-quality/coverage, and any genuine compatible-image
comparison stay operational, and qualified human review is always required.

These tests deliberately carry NO ``enable_demo_scoring`` mark — turning the demo
scorer on here would defeat their purpose.

Image bytes are built inline with Pillow (repo convention). Each test uses a
unique instrument type to stay isolated on the shared test DB.
"""
import io

from fastapi.testclient import TestClient
from PIL import Image

from app.main import app
from app.db.session import SessionLocal
from app.models.baseline_library import BaselineLibraryEntry
from app.services.baseline_comparison_scoring_service import (
    CLEANING_ASSESSMENT_UNAVAILABLE,
    _authoritative_ai_analysis,
)
from app.services.ml.image_similarity_service import compare_against_baseline

client = TestClient(app)

AUTH_ADMIN = {"Authorization": "Bearer dev-token"}
AUTH_OPERATOR = {"Authorization": "Bearer operator-token"}

SHA = "beadfeed" + "0" * 56


def _png(color=(120, 120, 120), size=(64, 64)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format="PNG")
    return buf.getvalue()


def _seed_approved_baseline(instrument_type: str) -> None:
    """A real, approved manufacturer baseline RECORD (metadata only — no ACTIVE
    linked image bytes), so baseline resolution works but image similarity can't
    be fabricated."""
    db = SessionLocal()
    try:
        db.query(BaselineLibraryEntry).filter(
            BaselineLibraryEntry.instrument_category == instrument_type
        ).delete()
        db.add(BaselineLibraryEntry(
            udi=f"pe-udi-{instrument_type}", instrument_category=instrument_type,
            manufacturer_name="Acme", model_name="X", baseline_type="manufacturer",
            approval_status="approved",
        ))
        db.commit()
    finally:
        db.close()


def _submit(instrument_type: str, *, declared=None) -> dict:
    payload = {
        "instrument_type": instrument_type,
        "site_name": "Pilot Hospital",
        "facility_name": "Pilot Hospital",
        "has_image": True,
        "image_sha256": SHA,
        "file_name": "pilot.jpg",
    }
    if declared is not None:
        payload["finding_categories"] = declared
    resp = client.post("/api/inspections", json=payload, headers=AUTH_OPERATOR)
    assert resp.status_code == 201, resp.text
    return resp.json()


# 1. With an approved baseline but no trained model, the authoritative AI verdict
#    is AI_UNAVAILABLE on the real submission route (not the demo scorer).
def test_route_reports_ai_unavailable_not_scored():
    itype = "pe_unavailable"
    _seed_approved_baseline(itype)
    body = _submit(itype)

    analysis = body["analysis"]
    assert analysis["analysis_status"] == "ai_unavailable"
    assert analysis["ai_analysis"]["status"] == "AI_UNAVAILABLE"
    assert analysis["ai_analysis"]["manual_inspection_required"] is True
    # Baseline RECORD still resolved (real metadata preserved).
    assert analysis["baseline_source"] == "manufacturer"
    assert body["baseline_source"] == "manufacturer"


# 2. No fabricated detection / clearance / score / confidence is produced.
def test_no_fabricated_score_or_confidence():
    itype = "pe_nofab"
    _seed_approved_baseline(itype)
    analysis = _submit(itype)["analysis"]

    assert analysis["inspection_score"] is None
    assert analysis["risk_level"] is None
    assert analysis["confidence"] is None
    assert analysis["predicted_findings"] == []
    # No AI observation is asserted from pixels that were never evaluated.
    assert analysis["ai_analysis"]["observation"] is None
    # The heuristic baseline-match number is never presented as image similarity.
    assert analysis["baseline_match_is_image_similarity"] is False
    assert analysis.get("baseline_match_score") is None


# 3. No pseudo clinical-decision payload is attached when the AI is unavailable
#    (the Explainable Clinical Decision panel would otherwise fabricate an
#    "Acceptable" integrity assessment / 0% confidence).
def test_no_clinical_decision_payload_when_unavailable():
    itype = "pe_nocd"
    _seed_approved_baseline(itype)
    analysis = _submit(itype)["analysis"]

    assert analysis.get("clinical_decision") is None


# 4. No mentor / executive-summary content is invented from absent findings.
def test_no_mentor_or_executive_content_invented():
    itype = "pe_nomentor"
    _seed_approved_baseline(itype)
    analysis = _submit(itype)["analysis"]

    # Mentor/executive fields only exist inside a completed clinical_decision —
    # which is absent here, so none of them can carry invented clinical content.
    for leaked in ("spd_mentor", "clinical_interpretation", "executive_summary",
                   "clinical_reasoning", "next_actions"):
        assert leaked not in analysis, f"unexpected invented content: {leaked}"


# 5. KPI categories are explicitly "Not evaluated" — never "No" / "Clear" / clean.
def test_categories_marked_not_evaluated():
    itype = "pe_noteval"
    _seed_approved_baseline(itype)
    analysis = _submit(itype)["analysis"]

    assert analysis["not_evaluated"] is True
    assert isinstance(analysis["not_evaluated_kpis"], list)
    assert len(analysis["not_evaluated_kpis"]) > 0
    # No KPI is asserted as a negative/clean result.
    assert analysis["kpi_summary"] == {}
    assert CLEANING_ASSESSMENT_UNAVAILABLE.lower().startswith("ai analysis unavailable")
    assert analysis["overall_cleaning_assessment"] == CLEANING_ASSESSMENT_UNAVAILABLE


# 6. A metadata-only baseline yields NO image-similarity percentage.
def test_metadata_only_baseline_no_similarity_percentage():
    itype = "pe_meta"
    _seed_approved_baseline(itype)
    analysis = _submit(itype)["analysis"]

    sim = analysis["ai_analysis"]["baseline_image_similarity"]
    assert sim is None or sim.get("similarity") is None


# 7. A GENUINE compatible-image comparison is labelled visual similarity —
#    explicitly not verified cleanliness (the only place a real % may appear).
def test_real_image_comparison_is_labelled_visual_similarity():
    img = _png((40, 50, 60))
    comp = compare_against_baseline(
        image_bytes=img, baseline_image_bytes=img,
        candidate_instrument_family="fam", baseline_instrument_family="fam",
        baseline_available=True, baseline_id=3, baseline_version="v1",
    )
    assert comp["similarity"] == 1.0
    assert comp["status"] == "exact_match"
    # The authoritative surface labels a genuine comparison as visual similarity
    # and is the only place a real % may appear.
    ai = _authoritative_ai_analysis({
        "analysis_status": "completed", "model": {}, "observation": None,
        "supported_categories": [], "unsupported_categories": [], "baseline_comparison": comp,
    })
    sim = ai["baseline_image_similarity"]
    assert sim["similarity"] == 1.0
    assert sim["is_image_comparison"] is True
    assert "not verified cleanliness" in sim["label"].lower()


# 8. The printable clinical report carries no fabricated conclusion.
def test_clinical_report_pdf_has_no_fabricated_conclusion():
    itype = "pe_pdf"
    _seed_approved_baseline(itype)
    inspection_id = _submit(itype)["id"]

    resp = client.get(f"/api/inspections/{inspection_id}/clinical-report.pdf", headers=AUTH_ADMIN)
    assert resp.status_code == 200, resp.text
    assert resp.headers["content-type"] == "application/pdf"
    body = resp.content
    assert body[:5] == b"%PDF-"
    # The report is driven by the AI_UNAVAILABLE analysis (no clinical_decision),
    # so it cannot contain a fabricated numeric cleanliness score line.
    assert b"/ 100" not in body


# 9. Technician-declared findings are kept as HUMAN observations, never AI.
def test_declared_findings_attributed_to_human_not_ai():
    itype = "pe_declared"
    _seed_approved_baseline(itype)
    analysis = _submit(itype, declared=["blood"])["analysis"]

    # Declared "blood" is a technician observation…
    assert any("blood" in o.lower() for o in analysis["technician_declared_observations"])
    # …and never an AI detection.
    assert analysis["predicted_findings"] == []
    assert analysis["ai_analysis"]["observation"] is None


# 10. No model result authorizes instrument release; human review is required.
def test_no_automatic_release_authorization():
    itype = "pe_release"
    _seed_approved_baseline(itype)
    body = _submit(itype)
    analysis = body["analysis"]

    assert analysis["ai_analysis"]["authorizes_release"] is False
    assert analysis["ai_analysis"]["human_review_required"] is True
    assert analysis["human_review_required"] is True
    assert body["supervisor_review_required"] is True


# 11. The surfaced status never simultaneously claims "scored" / "AI complete"
#     while the authoritative AI is unavailable.
def test_status_not_contradictory():
    itype = "pe_status"
    _seed_approved_baseline(itype)
    body = _submit(itype)

    assert body["analysis"]["ai_analysis"]["status"] == "AI_UNAVAILABLE"
    # Not scored — the route must not mark an AI_UNAVAILABLE result as scored.
    assert body["score_status"] != "scored"
    assert body["score_status"] != "scored_after_override"
    # The Lumen decision engine reports NOT a model observation.
    assert body["decision"]["observation"]["status"] != "model_observation"
    assert body["decision"]["human_decision_required"] is True


# 12. API, inspection history, and the clinical report agree on the same honest
#     verdict for one inspection — no surface disagrees.
def test_api_history_and_report_agree():
    itype = "pe_agree"
    _seed_approved_baseline(itype)
    body = _submit(itype)
    inspection_id = body["id"]

    # API: AI_UNAVAILABLE, not scored.
    assert body["analysis"]["analysis_status"] == "ai_unavailable"
    assert body["score_status"] == "ai_unavailable"

    # History: same inspection surfaces not-scored with no fabricated score.
    hist = client.get("/api/history?limit=100", headers=AUTH_ADMIN)
    assert hist.status_code == 200, hist.text
    record = next(it for it in hist.json()["items"] if it["id"] == inspection_id)
    assert record["score_status"] == "ai_unavailable"
    assert record["inspection_score"] is None
    assert record["supervisor_review_required"] is True

    # Report: renders for the same inspection without a fabricated score line.
    pdf = client.get(f"/api/inspections/{inspection_id}/clinical-report.pdf", headers=AUTH_ADMIN)
    assert pdf.status_code == 200, pdf.text
    assert pdf.content[:5] == b"%PDF-"


# 13. A baseline override cannot unlock scoring when the blocker is model
#     availability (not a missing baseline) — it must not bypass the no-model
#     safety state by marking the record scored_after_override.
def test_baseline_override_rejected_when_ai_unavailable():
    itype = "pe_override"
    _seed_approved_baseline(itype)
    body = _submit(itype)
    assert body["score_status"] == "ai_unavailable"
    inspection_id = body["id"]

    resp = client.post(
        f"/api/inspections/{inspection_id}/baseline-override",
        json={"baseline_source": "vendor", "override_reason": "attempting to force a score"},
        headers=AUTH_ADMIN,
    )
    assert resp.status_code == 409, resp.text

    # The record stays in the honest no-model safety state — never scored.
    hist = client.get("/api/history?limit=100", headers=AUTH_ADMIN)
    record = next(it for it in hist.json()["items"] if it["id"] == inspection_id)
    assert record["score_status"] == "ai_unavailable"
    assert record["inspection_score"] is None


# 14. Technician-declared observations survive in the durable record (history)
#     with human provenance, distinct from AI findings, even when AI is unavailable.
def test_declared_observations_persisted_in_history():
    itype = "pe_declared_durable"
    _seed_approved_baseline(itype)
    body = _submit(itype, declared=["blood"])
    inspection_id = body["id"]

    hist = client.get("/api/history?limit=100", headers=AUTH_ADMIN)
    record = next(it for it in hist.json()["items"] if it["id"] == inspection_id)
    # Durable human observation is present and attributed to the technician…
    assert any("blood" in o.lower() for o in record["technician_declared_observations"])
    # …and never surfaced as an AI finding/score.
    assert record["inspection_score"] is None
    assert record["ai_analysis_status"] == "AI_UNAVAILABLE"
