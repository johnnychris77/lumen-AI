import hashlib

import pytest

from app.ai.local_inference_policy import LocalInferenceUnavailable, verify_local_weights


def test_missing_weights_fail_closed(tmp_path):
    with pytest.raises(LocalInferenceUnavailable):
        verify_local_weights(str(tmp_path / "missing.pt"), "a" * 64)


def test_missing_pin_fail_closed(tmp_path):
    model = tmp_path / "model.pt"
    model.write_bytes(b"test-only")
    with pytest.raises(LocalInferenceUnavailable):
        verify_local_weights(str(model), "")


def test_mismatched_pin_fail_closed(tmp_path):
    model = tmp_path / "model.pt"
    model.write_bytes(b"test-only")
    with pytest.raises(LocalInferenceUnavailable):
        verify_local_weights(str(model), "0" * 64)


def test_matching_pin_uses_local_file_only(tmp_path, monkeypatch):
    model = tmp_path / "model.pt"
    data = b"test-only"
    model.write_bytes(data)
    def forbid_network(*args, **kwargs):
        raise AssertionError("unexpected outbound connection")
    import socket
    monkeypatch.setattr(socket.socket, "connect", forbid_network)
    result = verify_local_weights(str(model), hashlib.sha256(data).hexdigest())
    assert result["verified"] is True
    assert result["runtime"] == "local-only"
