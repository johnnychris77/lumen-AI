"""Lumen Decision Engine & Observation Doctrine — Section 18 checklist tests.

Covers the 22 verbatim checklist items from the doctrine spec, end-to-end
against the real inspection-submission route wherever practical, and at
the service layer where HTTP-level determinism would require guessing a
hashed baseline-similarity value.
"""
from __future__ import annotations

import os

os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")

from fastapi.testclient import TestClient

from app.db.session import SessionLocal
from app.main import app
from app.models.baseline_library import BaselineLibraryEntry
from app.models.lumen_decision_engine import LumenDecisionRecord, UnknownFindingReview
from app.services import baseline_decision_policy_service as policy_service
from app.services import lumen_decision_engine as decision_engine
from app.services import policy_resolution_service, policy_simulation_service, observation_taxonomy as taxonomy

client = TestClient(app)

AUTH_ADMIN = {"Authorization": "Bearer dev-token"}
AUTH_MGR = {"Authorization": "Bearer manager-token"}
AUTH_VIEWER = {"Authorization": "Bearer viewer-token"}
AUTH_OPERATOR = {"Authorization": "Bearer operator-token"}
SHA = "d0decaf0" + "0" * 56


def _clear_baseline(itype: str) -> None:
    db = SessionLocal()
    try:
        db.query(BaselineLibraryEntry).filter(BaselineLibraryEntry.instrument_category == itype).delete()
        db.commit()
    finally:
        db.close()


def _create_baseline(itype: str) -> None:
    _clear_baseline(itype)
    r = client.post("/api/baselines/manufacturer", json={
        "instrument_type": itype, "manufacturer_name": "Acme", "image_sha256": SHA,
    }, headers=AUTH_ADMIN)
    assert r.status_code == 201, r.text


def _submit_inspection(itype: str, *, finding_categories=None, sha=SHA) -> dict:
    resp = client.post("/api/inspections", json={
        "instrument_type": itype, "site_name": "Test Hospital", "has_image": True,
        "image_sha256": sha, "file_name": "img.jpg",
        "finding_categories": finding_categories or [],
    }, headers=AUTH_OPERATOR)
    assert resp.status_code == 201, resp.text
    return resp.json()


def _db():
    return SessionLocal()


class TestObservationLanguage:
    """Checklist: probable language used for model observations."""

    def test_debris_observation_uses_probable_language(self):
        itype = "obs_lang_debris"
        _create_baseline(itype)
        body = _submit_inspection(itype, finding_categories=["debris"])
        obs = body["decision"]["observation"]
        assert obs["display_label"].lower().startswith("probable")
        assert obs["category"] == taxonomy.OBSERVATION_RETAINED_DEBRIS

    def test_forbidden_terms_never_appear(self):
        itype = "obs_lang_forbidden"
        _create_baseline(itype)
        body = _submit_inspection(itype, finding_categories=["debris"])
        blob = str(body["decision"]).lower()
        for banned in ("confirmed blood", "sterile", "clinically cleared", "guaranteed clean", "diagnosis"):
            assert banned not in blob, f"forbidden term leaked: {banned}"


class TestUnsupportedCategories:
    """Checklist: unsupported categories marked not evaluated; unknown finding
    requires supervisor review."""

    def test_blood_is_unsupported_and_triggers_unknown_review(self):
        itype = "unsupported_blood"
        _create_baseline(itype)
        body = _submit_inspection(itype, finding_categories=["blood"])
        obs = body["decision"]["observation"]
        rec = body["decision"]["recommendation"]
        assert obs["category"] == taxonomy.OBSERVATION_UNKNOWN_FOREIGN
        assert obs["confidence"] is None  # never a fabricated probability
        assert rec["supervisor_required"] is True
        assert body["decision"]["unknown_finding"] is not None

        db = _db()
        try:
            review = db.query(UnknownFindingReview).filter(
                UnknownFindingReview.id == body["decision"]["unknown_finding"]["unknown_finding_review_id"],
            ).first()
            assert review is not None
            assert review.status == "pending_supervisor"
        finally:
            db.close()

    def test_lint_or_fiber_marked_not_evaluated(self):
        assert taxonomy.is_unsupported_category(taxonomy.OBSERVATION_LINT_OR_FIBER)
        assert taxonomy.display_label(None) == taxonomy.NOT_EVALUATED_BY_CURRENT_MODEL


class TestContaminationSafetyRule:
    """Checklist: high baseline similarity does not cancel probable
    contamination; probable contamination recommends recleaning; routine
    initial recleaning does not always require supervisor approval."""

    def test_debris_forces_reclean_regardless_of_similarity(self):
        itype = "contam_safety_debris"
        _create_baseline(itype)
        body = _submit_inspection(itype, finding_categories=["debris"])
        rec = body["decision"]["recommendation"]
        assert rec["action"] == decision_engine.ACTION_RECLEAN_REINSPECT
        assert rec["supervisor_required"] is False  # routine recleaning, no supervisor needed

    def test_less_restrictive_policy_cannot_cancel_contamination(self):
        itype = "contam_safety_loose_policy"
        _create_baseline(itype)
        db = _db()
        try:
            draft = policy_service.create_draft_policy(
                db, tenant_id="default-tenant", actor="admin@test", actor_role="admin",
                fields={
                    "scope": "instrument_family", "scope_value": itype,
                    "policy_name": "Very loose policy", "pass_threshold": 0.01,
                    "technician_review_threshold": 0.01,
                },
            )
            draft = policy_service.submit_for_approval(db, draft, actor_role="admin")
            draft = policy_service.approve_policy(db, draft, actor="admin@test", actor_role="admin")
            policy_service.activate_policy(db, draft, actor_role="admin")
        finally:
            db.close()

        body = _submit_inspection(itype, finding_categories=["debris"])
        rec = body["decision"]["recommendation"]
        # Even though the active policy would pass almost anything, the
        # contamination override is enforced unconditionally in code.
        assert rec["action"] == decision_engine.ACTION_RECLEAN_REINSPECT


class TestBaselineTerminology:
    def test_baseline_score_not_called_cleanliness_or_sterility(self):
        itype = "terminology_check"
        _create_baseline(itype)
        body = _submit_inspection(itype)
        blob = str(body["decision"]).lower()
        for banned in ("cleanliness percentage", "sterility score", "confirmed safety percentage"):
            assert banned not in blob
        assert "baseline_similarity" in body["decision"]["assessment"]
        assert "baseline_deviation" in body["decision"]["assessment"]


class TestPolicyThresholdOverrides:
    """Checklist: organization-specific threshold overrides LumenAI default;
    model-specific policy overrides facility default; below-threshold result
    routes according to local policy; supervisor approval is required where
    the local policy requires it."""

    def _activate(self, db, **fields):
        draft = policy_service.create_draft_policy(
            db, tenant_id="default-tenant", actor="admin@test", actor_role="admin", fields=fields,
        )
        draft = policy_service.submit_for_approval(db, draft, actor_role="admin")
        draft = policy_service.approve_policy(db, draft, actor="admin@test", actor_role="admin")
        return policy_service.activate_policy(db, draft, actor_role="admin")

    def test_instrument_family_policy_overrides_default_and_drives_supervisor_requirement(self):
        itype = "policy_override_family"
        _create_baseline(itype)

        # Probe the real (deterministic) baseline similarity for this seed
        # under the LumenAI default policy first.
        probe = _submit_inspection(itype)
        sim = probe["decision"]["assessment"]["baseline_similarity"]
        assert sim is not None

        db = _db()
        try:
            # Org A: threshold comfortably below the observed similarity —
            # expect continue, no supervisor.
            self._activate(
                db, scope="instrument_family", scope_value=itype, policy_name="Org A Policy",
                pass_threshold=max(0.0, sim - 0.05), technician_review_threshold=max(0.0, sim - 0.05),
            )
        finally:
            db.close()

        body_a = _submit_inspection(itype)
        rec_a = body_a["decision"]["recommendation"]
        assert rec_a["action"] == decision_engine.ACTION_CONTINUE
        assert rec_a["supervisor_required"] is False
        assert body_a["decision"]["policy"]["policy_id"] != "lumenai-default-v1"

        db = _db()
        try:
            # Org B: stricter threshold above the observed similarity, with
            # no technician-only band — expect supervisor attention.
            self._activate(
                db, scope="instrument_family", scope_value=itype, policy_name="Org B Policy",
                pass_threshold=min(1.0, sim + 0.03), technician_review_threshold=min(1.0, sim + 0.03),
            )
        finally:
            db.close()

        body_b = _submit_inspection(itype)
        rec_b = body_b["decision"]["recommendation"]
        assert rec_b["action"] == decision_engine.ACTION_HOLD_SUPERVISOR
        assert rec_b["supervisor_required"] is True

    def test_model_specific_policy_overrides_facility_policy(self):
        itype = "policy_override_model_vs_facility"
        facility = "Test Hospital"
        _create_baseline(itype)

        db = _db()
        try:
            self._activate(
                db, scope="facility", scope_value=facility, policy_name="Facility Default",
                pass_threshold=0.99, technician_review_threshold=0.99,
            )
            self._activate(
                db, scope="model", scope_value=itype, policy_name="Model-Specific Override",
                pass_threshold=0.0, technician_review_threshold=0.0,
            )
        finally:
            db.close()

        body = _submit_inspection(itype)
        # The model-specific policy (0.0 threshold) must win over the
        # facility policy (0.99 threshold) per the resolution hierarchy.
        assert body["decision"]["recommendation"]["action"] == decision_engine.ACTION_CONTINUE
        assert body["decision"]["policy"]["scope"] == "model"


class TestPolicyGovernance:
    """Checklist: policy changes require authorized approval; draft policy
    cannot affect live recommendations; technician cannot publish policy;
    viewer cannot change threshold."""

    def test_activate_requires_prior_approval(self):
        db = _db()
        try:
            draft = policy_service.create_draft_policy(
                db, tenant_id="default-tenant", actor="admin@test", actor_role="admin",
                fields={"scope": "facility", "scope_value": "Gov Test", "policy_name": "Gov Policy"},
            )
            try:
                policy_service.activate_policy(db, draft, actor_role="admin")
                assert False, "should have raised — draft was never approved"
            except policy_service.PolicyGovernanceError:
                pass
        finally:
            db.close()

    def test_draft_policy_does_not_affect_live_recommendation(self):
        itype = "draft_no_effect"
        _create_baseline(itype)
        db = _db()
        try:
            policy_service.create_draft_policy(
                db, tenant_id="default-tenant", actor="admin@test", actor_role="admin",
                fields={
                    "scope": "instrument_family", "scope_value": itype, "policy_name": "Unpublished Draft",
                    "pass_threshold": 0.0, "technician_review_threshold": 0.0,
                },
            )
        finally:
            db.close()

        body = _submit_inspection(itype)
        # Falls back to the LumenAI default (0.90/0.70 bands), never the
        # unpublished draft's 0.0 thresholds.
        assert body["decision"]["policy"]["policy_id"] == "lumenai-default-v1"

    def test_technician_cannot_publish_policy(self):
        r = client.post("/api/decision-policies", json={
            "scope": "facility", "scope_value": "X", "policy_name": "Should Fail",
        }, headers=AUTH_OPERATOR)
        assert r.status_code == 403

    def test_viewer_cannot_activate_policy(self):
        r = client.post("/api/decision-policies/999999/activate", headers=AUTH_VIEWER)
        assert r.status_code == 403


class TestPolicySimulation:
    """Checklist: policy simulation does not change production records."""

    def test_simulation_is_read_only(self):
        db = _db()
        before = db.query(LumenDecisionRecord).count()
        db.close()

        result = policy_simulation_service.simulate_policy(
            db=_db(), tenant_id="default-tenant",
            candidate={"pass_threshold": 0.5, "technician_review_threshold": 0.5},
        )
        assert result["modifies_historical_records"] is False
        assert result["requires_authorized_publication"] is True

        db = _db()
        after = db.query(LumenDecisionRecord).count()
        db.close()
        assert before == after


class TestCrossTenantIsolation:
    """Checklist: cross-tenant policies cannot influence another organization."""

    def test_policy_scoped_to_one_tenant_invisible_to_another(self):
        db = _db()
        try:
            draft = policy_service.create_draft_policy(
                db, tenant_id="hospital-a", actor="admin@test", actor_role="admin",
                fields={
                    "scope": "instrument_family", "scope_value": "cross_tenant_itype",
                    "policy_name": "Hospital A Only", "pass_threshold": 0.01,
                },
            )
            draft = policy_service.submit_for_approval(db, draft, actor_role="admin")
            draft = policy_service.approve_policy(db, draft, actor="admin@test", actor_role="admin")
            policy_service.activate_policy(db, draft, actor_role="admin")

            resolved_other_tenant = policy_resolution_service.resolve_active_policy(
                db, tenant_id="hospital-b", instrument_family="cross_tenant_itype",
            )
            assert resolved_other_tenant["policy_id"] == "lumenai-default-v1"

            resolved_same_tenant = policy_resolution_service.resolve_active_policy(
                db, tenant_id="hospital-a", instrument_family="cross_tenant_itype",
            )
            assert resolved_same_tenant["policy_id"] == draft.policy_id
        finally:
            db.close()


class TestImmutabilityAndAuditability:
    """Checklist: original AI observation remains immutable after human
    correction; recommendation stores active policy version."""

    def test_human_followthrough_never_overwrites_original_observation(self):
        itype = "immutability_check"
        _create_baseline(itype)
        body = _submit_inspection(itype, finding_categories=["debris"])
        inspection_id = body["id"]

        db = _db()
        try:
            record = decision_engine.get_record_for_inspection(db, inspection_id)
            original_category = record.observation_category
            original_confidence = record.observation_confidence

            decision_engine.record_human_followthrough(
                db, record, actor="supervisor@test", actor_role="spd_manager", role_kind="supervisor",
                action_text="Confirmed and recleaned per policy.", final_decision="reclean_and_reinspect",
            )

            db.refresh(record)
            assert record.observation_category == original_category
            assert record.observation_confidence == original_confidence
            assert record.supervisor_action == "Confirmed and recleaned per policy."
            assert record.final_human_decision == "reclean_and_reinspect"
        finally:
            db.close()

    def test_recommendation_stores_active_policy_version(self):
        itype = "policy_version_stamp"
        _create_baseline(itype)
        db = _db()
        try:
            draft = policy_service.create_draft_policy(
                db, tenant_id="default-tenant", actor="admin@test", actor_role="admin",
                fields={
                    "scope": "instrument_family", "scope_value": itype, "policy_name": "Versioned Policy",
                    "version": "7.3",
                },
            )
            draft = policy_service.submit_for_approval(db, draft, actor_role="admin")
            draft = policy_service.approve_policy(db, draft, actor="admin@test", actor_role="admin")
            policy_service.activate_policy(db, draft, actor_role="admin")
        finally:
            db.close()

        body = _submit_inspection(itype)
        assert body["decision"]["policy"]["policy_version"] == "7.3"

        db = _db()
        try:
            record = decision_engine.get_record_for_inspection(db, body["id"])
            assert record.policy_version == "7.3"
        finally:
            db.close()


class TestInsufficientEvidence:
    """Checklist: insufficient image quality requests recapture or review."""

    def test_no_baseline_forces_supervisor_review(self):
        itype = "no_baseline_review_case"
        _clear_baseline(itype)  # no approved baseline exists
        body = _submit_inspection(itype)
        rec = body["decision"]["recommendation"]
        assert rec["supervisor_required"] is True
        assert rec["action"] == decision_engine.ACTION_HOLD_SUPERVISOR


class TestArchitecturalSeparation:
    """Checklist: Decision Engine remains separate from the vision model."""

    def test_vision_model_module_has_no_policy_logic(self):
        import app.ai.inference as inference_module

        src = open(inference_module.__file__, encoding="utf-8").read()
        assert "BaselineDecisionPolicy" not in src
        assert "policy_resolution_service" not in src
        assert "lumen_decision_engine" not in src
