"""Optional research-dependency detection.

PyTorch and other heavy CV dependencies are optional extras installed only in an
isolated research environment (``backend/requirements-research.txt``). Production
and CI never install them, so research code must degrade gracefully: governance,
provenance, splitting, checkpoint-verification and the deterministic smoke path
all work with no torch; only the real DINOv2 embedding path requires it.
"""
from __future__ import annotations

import importlib.util


class ResearchDependencyMissing(RuntimeError):
    """A real deep-learning backend was requested but is not installed here."""


def torch_available() -> bool:
    """True iff ``torch`` can be imported in this environment."""
    try:
        return importlib.util.find_spec("torch") is not None
    except (ImportError, ValueError):
        return False


def require_torch() -> None:
    """Raise a clear, actionable error when torch is needed but absent."""
    if not torch_available():
        raise ResearchDependencyMissing(
            "PyTorch is not installed in this environment. The real DINOv2 "
            "embedding path requires it. Install it ONLY in an isolated research "
            "environment via `pip install -r backend/requirements-research.txt` — "
            "never in the production API image. For CPU smoke tests, use the "
            "deterministic stub embedder instead (StubEmbedder)."
        )
