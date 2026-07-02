"""Phase 17 — Model Training Pipeline & AI Readiness.

Covers dataset-split leakage prevention, model registry, deployment gates
(experimental cannot drive; pilot needs disclaimer; validated allows override;
deprecated unusable), shadow mode (stores without showing a recommendation), and
safety metrics (blood false-negative rate, anatomy-zone performance).
"""
from fastapi.testclient import TestClient

from app.main import app
from app.services.ml.dataset_split import split_dataset, has_no_group_leakage
from app.services.ml.evaluation import evaluate, safety_metrics
from app.services.ml.deployment_gates import (
    capabilities, evaluate_promotion, usable_for_new_inspection,
)
from app.services.ml.training_pipeline import prepare_training_run

client = TestClient(app)
AUTH = {"Authorization": "Bearer dev-token"}
AUTH_VIEWER = {"Authorization": "Bearer viewer-token"}


# ── Dataset split ─────────────────────────────────────────────────────────────

def _samples(n_inspections=30, imgs=2):
    out = []
    for insp in range(1, n_inspections + 1):
        fam = "rigid_scope" if insp % 2 else "drill_bit"
        for k in range(imgs):
            out.append({
                "id": f"{insp}-{k}", "inspection_id": insp, "instrument_serial": f"S{insp}",
                "instrument_family": fam, "anatomy_zone": "o-ring area", "finding": "blood",
                "severity": "moderate", "manufacturer": "M", "image_quality": "good",
            })
    return out


class TestDatasetSplit:
    def test_split_preserves_inspection_grouping(self):
        samples = _samples()
        r = split_dataset(samples)
        assert has_no_group_leakage(r)
        # No inspection's images straddle two splits.
        by_insp = {}
        for s in samples:
            by_insp.setdefault(s["inspection_id"], set()).add(r["assignments"][s["id"]])
        assert all(len(v) == 1 for v in by_insp.values())

    def test_split_ratios_roughly_70_15_15(self):
        r = split_dataset(_samples(100, imgs=1))
        total = r["total_samples"]
        assert 0.6 <= r["counts"]["train"] / total <= 0.8
        assert r["counts"]["train"] + r["counts"]["validation"] + r["counts"]["test"] == total

    def test_prepare_run_is_not_started_and_leakage_free(self):
        run = prepare_training_run("finding", _samples())
        assert run["training_status"] == "not_started"
        assert run["leakage_free"] is True
        assert run["model_artifact"] is None  # nothing fabricated


# ── Evaluation / safety metrics ───────────────────────────────────────────────

class TestEvaluation:
    def test_blood_false_negative_metric_tracked(self):
        y_true = ["blood", "blood", "none", "tissue"]
        y_pred = ["blood", "none", "none", "tissue"]  # one blood missed
        m = safety_metrics(y_true, y_pred)
        assert m["blood_false_negative_rate"] == 0.5
        assert m["tissue_false_negative_rate"] == 0.0

    def test_anatomy_zone_performance_calculated(self):
        y_true = ["blood", "none", "blood", "none"]
        y_pred = ["blood", "none", "none", "none"]
        zones = ["o-ring area", "o-ring area", "hinge", "hinge"]
        ev = evaluate(y_true, y_pred, ["blood", "none"], groups={"anatomy_zone": zones})
        breakdown = ev["performance_breakdowns"]["anatomy_zone"]
        assert breakdown["o-ring area"]["accuracy"] == 1.0
        assert breakdown["hinge"]["accuracy"] == 0.5


# ── Deployment gates (service level) ──────────────────────────────────────────

class TestDeploymentGates:
    def test_experimental_cannot_drive_recommendation(self):
        assert capabilities("experimental")["can_drive_clinical_recommendation"] is False
        assert capabilities("experimental")["can_run_shadow_mode"] is True

    def test_pilot_requires_disclaimer_and_is_advisory_only(self):
        caps = capabilities("pilot")
        assert caps["requires_human_review_disclaimer"] is True
        assert caps["can_provide_advisory"] is True
        assert caps["can_drive_clinical_recommendation"] is False

    def test_validated_allows_supervisor_override(self):
        caps = capabilities("validated")
        assert caps["can_drive_clinical_recommendation"] is True
        assert caps["supervisor_override_allowed"] is True

    def test_deprecated_not_usable_for_new_inspection(self):
        assert usable_for_new_inspection("deprecated") is False

    def test_no_auto_promotion_without_requirements(self):
        blocked = evaluate_promotion("experimental", "pilot", approver="a")
        assert blocked["allowed"] is False
        assert "supervisor_validation" in blocked["unmet"]

    def test_cannot_skip_stage(self):
        assert evaluate_promotion("experimental", "validated", approver="a")["allowed"] is False


# ── API: registry + promotion + shadow ────────────────────────────────────────

class TestModelPipelineApi:
    def _register(self, model_id="m-api-1", mtype="finding"):
        return client.post("/api/model-pipeline/models", headers=AUTH, json={
            "model_id": model_id, "model_version": "0.1", "model_type": mtype,
        })

    def test_registry_records_model_version(self):
        r = self._register("m-registry")
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["model_version"] == "0.1"
        assert body["approval_status"] == "experimental"  # never higher on create
        assert body["capabilities"]["can_drive_clinical_recommendation"] is False

    def test_experimental_model_cannot_drive_via_api(self):
        r = self._register("m-exp")
        assert r.json()["capabilities"]["can_drive_clinical_recommendation"] is False

    def test_promotion_blocked_then_allowed_with_checklist(self):
        mid = self._register("m-promote").json()["id"]
        blocked = client.post(f"/api/model-pipeline/models/{mid}/promote", headers=AUTH,
                              json={"target_stage": "pilot"})
        assert blocked.status_code == 409
        ok = client.post(f"/api/model-pipeline/models/{mid}/promote", headers=AUTH, json={
            "target_stage": "pilot", "sample_size": 300,
            "checklist": {
                "supervisor_validation": True, "minimum_sample_size": True,
                "false_negative_review": True, "edge_case_review": True,
                "limitations_documented": True,
            },
        })
        assert ok.status_code == 200, ok.text
        assert ok.json()["model"]["approval_status"] == "pilot"
        assert ok.json()["model"]["capabilities"]["requires_human_review_disclaimer"] is True

    def test_shadow_mode_stores_without_showing_recommendation(self):
        self._register("m-shadow")
        s = client.post("/api/model-pipeline/shadow-predictions", headers=AUTH, json={
            "model_id": "m-shadow", "predicted_label": "blood", "predicted_confidence": "0.9",
        })
        assert s.status_code == 201, s.text
        body = s.json()
        assert body["shadow_mode"] is True
        assert body["clinical_recommendation_shown"] is False
        assert "predicted_label" not in body  # the silent prediction is not surfaced

    def test_deprecated_model_cannot_run_shadow(self):
        # Register, deprecate, then a shadow prediction must be refused.
        mid = self._register("m-dep").json()["id"]
        dep = client.post(f"/api/model-pipeline/models/{mid}/promote", headers=AUTH,
                          json={"target_stage": "deprecated"})
        assert dep.status_code == 200, dep.text
        s = client.post("/api/model-pipeline/shadow-predictions", headers=AUTH, json={
            "model_id": "m-dep", "predicted_label": "blood",
        })
        assert s.status_code == 409

    def test_viewer_cannot_register_model(self):
        r = client.post("/api/model-pipeline/models", headers=AUTH_VIEWER, json={
            "model_id": "m-viewer", "model_version": "0.1", "model_type": "finding",
        })
        assert r.status_code == 403

    def test_tasks_and_gates_discovery(self):
        t = client.get("/api/model-pipeline/tasks", headers=AUTH)
        assert t.status_code == 200
        assert "finding" in t.json()["tasks"]
        assert "blood" in t.json()["safety_critical_findings"]
        g = client.get("/api/model-pipeline/deployment-gates", headers=AUTH)
        assert g.status_code == 200
        assert set(g.json()["stages"]) == {"experimental", "pilot", "validated", "deprecated"}
