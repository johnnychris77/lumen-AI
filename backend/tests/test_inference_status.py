"""Tests for app.ai.inference_status.get_inference_status()."""
from __future__ import annotations

import os

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

ADMIN_AUTH = {"Authorization": "Bearer dev-token"}
OPERATOR_AUTH = {"Authorization": "Bearer operator-token"}


class TestGetInferenceStatus:
    def test_identifies_placeholder_mode_when_no_weights_or_deps(self):
        """With no model weights file and no ultralytics/onnxruntime installed
        (this test environment), the honest answer is deterministic_placeholder."""
        from app.ai.inference_status import get_inference_status

        # Make sure no stray LUMENAI_MODEL_PATH from another test points at a
        # real file, and that the default path really doesn't exist here.
        os.environ.pop("LUMENAI_MODEL_PATH", None)
        assert not os.path.exists("models/lumenai_model.pt")

        status = get_inference_status()
        assert status["mode"] == "deterministic_placeholder"
        assert status["model_weights_present"] is False
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

    def test_reports_trained_model_when_weights_and_yolo_present(self, tmp_path, monkeypatch):
        """If a weights file exists AND ultralytics is importable, mode flips
        to trained_model -- proves this isn't a hardcoded placeholder label."""
        import sys
        import types
        from app.ai import inference_status

        fake_weights = tmp_path / "lumenai_model.pt"
        fake_weights.write_bytes(b"not a real model, just a presence check")
        monkeypatch.setenv("LUMENAI_MODEL_PATH", str(fake_weights))

        fake_ultralytics = types.ModuleType("ultralytics")
        fake_ultralytics.YOLO = object
        monkeypatch.setitem(sys.modules, "ultralytics", fake_ultralytics)

        status = inference_status.get_inference_status()
        assert status["mode"] == "trained_model"
        assert status["model_weights_present"] is True
        assert status["yolo_available"] is True
        assert status["ready_for_production"] is True


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
        assert body["mode"] in ("deterministic_placeholder", "trained_model")
        assert "ready_for_production" in body
