"""P4.7 local-only inference policy, isolated from existing production routes.

This module intentionally does not claim that model weights are installed or
that other inspection paths are free of external provider calls.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path


class LocalInferenceUnavailable(RuntimeError):
    """A real, approved local model is not ready; never synthesize a finding."""


def verify_local_weights(path: str | None = None, expected_sha256: str | None = None) -> dict:
    """Fail closed unless a readable, hash-pinned model artifact exists locally.

    Does not load weights or make any network request. Loading and inference
    must be separately integrated and reviewed before any route uses this.
    """
    raw = path if path is not None else os.getenv("LUMENAI_MODEL_PATH", "")
    expected = expected_sha256 if expected_sha256 is not None else os.getenv("LUMENAI_MODEL_SHA256", "")
    if not raw or not expected or len(expected) != 64:
        raise LocalInferenceUnavailable("Local model path and SHA-256 pin required")
    try:
        int(expected, 16)
    except ValueError as exc:
        raise LocalInferenceUnavailable("Invalid SHA-256 pin") from exc
    p = Path(raw)
    if not p.is_file():
        raise LocalInferenceUnavailable("Local model artifact unavailable")
    digest = hashlib.sha256()
    try:
        with p.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
    except OSError as exc:
        raise LocalInferenceUnavailable("Local model artifact unreadable") from exc
    if digest.hexdigest() != expected.lower():
        raise LocalInferenceUnavailable("Local model artifact integrity mismatch")
    return {"runtime": "local-only", "model_path": str(p), "sha256": digest.hexdigest(), "verified": True}
