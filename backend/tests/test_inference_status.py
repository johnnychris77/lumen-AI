"""Tests for app.ai.inference_status.get_inference_status()."""
from __future__ import annotations

import os

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

ADMIN_AUTH = {"Authorization": "Bearer dev-token"}
OPERATOR_AUTH = {"Authorization": "Bearer operator-token"}


class TestGetInferenceStatus:
    def test_reports_unavailable_when_no_weights_and_simulation_not_permitted(self):
        """P4.7.1: with no model weights and the simulation gate closed (the
        suite default, and every production/research deployment), the honest
        answer is "unavailable" -- nothing is evaluated and nothing is
        fabricated. It is no longer reported as a running placeholder."""
        from app.ai.inference_status import get_inference_status

        # Make sure no stray LUMENAI_MODEL_PATH from another test points at a
        # real file, and that the default path really doesn't exist here.
        os.environ.pop("LUMENAI_MODEL_PATH", None)
        assert not os.path.exists("models/lumenai_model.pt")

        status = get_inference_status()
        assert status["mode"] == "unavailable"
        assert status["simulation_permitted"] is False
        assert status["model_weights_present"] is False
        assert status["weights_verified"] is False
        assert status["ready_for_production"] is False

    def test_reports_placeholder_only_when_simulation_explicitly_permitted(self, enable_demo_scoring):
        """The deterministic placeholder is reported only where the dev/test
        simulation is explicitly opted in."""
        from app.ai.inference_status import get_inference_status

        os.environ.pop("LUMENAI_MODEL_PATH", None)
        status = get_inference_status()
        assert status["mode"] == "deterministic_placeholder"
        assert status["simulation_permitted"] is True
        assert status["ready_for_production"] is False

    def test_ready_for_production_false_unless_trained_and_weights_present(self):
        from app.ai.inference_status import get_inference_status
        status = get_inference_status()
        assert status["ready_for_production"] == (
            status["mode"] == "trained_model" and status["model_weights_present"]
        )

    def test_returns_all_expected_fields(self):
        from app.ai.inference_status import get_inference_status
        status = get_inference_status()
        for field in (
            "mode", "model_path", "onnx_available", "yolo_available",
            "model_weights_present", "ready_for_production",
        ):
            assert field in status

    def _fake_runtime(self, tmp_path, monkeypatch):
        import sys
        import types

        fake_weights = tmp_path / "lumenai_model.pt"
        fake_weights.write_bytes(b"not a real model, just bytes to hash")
        monkeypatch.setenv("LUMENAI_MODEL_PATH", str(fake_weights))

        fake_ultralytics = types.ModuleType("ultralytics")
        fake_ultralytics.YOLO = object
        monkeypatch.setitem(sys.modules, "ultralytics", fake_ultralytics)
        return fake_weights

    def test_weights_file_presence_alone_is_not_a_trained_model(self, tmp_path, monkeypatch):
        """P4.7.1: a file at the model path plus an importable runtime used to
        flip the mode to trained_model. Presence is not proof -- without a
        SHA-256 pin the artifact is unverified and the mode stays unavailable."""
        from app.ai import inference_status

        self._fake_runtime(tmp_path, monkeypatch)
        monkeypatch.delenv("LUMENAI_MODEL_SHA256", raising=False)

        status = inference_status.get_inference_status()
        assert status["model_weights_present"] is True
        assert status["yolo_available"] is True
        assert status["weights_verified"] is False
        assert status["mode"] == "unavailable"
        assert status["ready_for_production"] is False

    def test_hash_mismatch_is_not_a_trained_model(self, tmp_path, monkeypatch):
        from app.ai import inference_status

        self._fake_runtime(tmp_path, monkeypatch)
        monkeypatch.setenv("LUMENAI_MODEL_SHA256", "0" * 64)

        status = inference_status.get_inference_status()
        assert status["weights_verified"] is False
        assert status["mode"] == "unavailable"
        assert status["ready_for_production"] is False

    def test_reports_trained_model_only_when_weights_match_the_pin(self, tmp_path, monkeypatch):
        """Mode flips to trained_model only when the runtime is importable AND
        the artifact's SHA-256 equals the operator-supplied pin."""
        import hashlib
        from app.ai import inference_status

        fake_weights = self._fake_runtime(tmp_path, monkeypatch)
        monkeypatch.setenv(
            "LUMENAI_MODEL_SHA256", hashlib.sha256(fake_weights.read_bytes()).hexdigest()
        )

        status = inference_status.get_inference_status()
        assert status["mode"] == "trained_model"
        assert status["model_weights_present"] is True
        assert status["weights_verified"] is True
        assert status["yolo_available"] is True
        assert status["ready_for_production"] is True
        # A verified artifact is a loader state, not a performance claim.
        assert "not a release authorization" in status["governance_note"]


class TestInferenceStatusEndpoint:
    def test_requires_auth(self):
        r = client.get("/api/v1/system/inference-status")
        assert r.status_code in (401, 403)

    def test_forbidden_for_non_admin_role(self):
        r = client.get("/api/v1/system/inference-status", headers=OPERATOR_AUTH)
        assert r.status_code == 403

    def test_admin_can_read_status(self):
        r = client.get("/api/v1/system/inference-status", headers=ADMIN_AUTH)
        assert r.status_code == 200
        body = r.json()
        assert body["mode"] in ("unavailable", "deterministic_placeholder", "trained_model")
        assert "ready_for_production" in body
        assert "weights_verified" in body
