"""P4.7.1 — single gate for simulated (non-model) inference output.

LumenAI ships no trained defect-detection model. Two legacy code paths can
nevertheless manufacture defect findings without looking at pixels:

* ``app.ai.inference.LumenAIModel._deterministic_fallback`` (SHA-256-seeded), and
* ``app.cv.mock_provider.MockCVProvider`` (seeded from the image URL).

Neither may ever run in a production, staging, research or otherwise
unclassified environment. They survive only as an explicitly opted-in
development/test simulation, and everything they emit is stamped
``simulated=True`` so it can never be read as a detection.

The gate deliberately reuses the existing fail-closed switch
(``Settings.demo_scoring_effective``): it is True only when BOTH

* ``AI_ALLOW_DEMO_SCORING`` is explicitly enabled, and
* ``APP_ENV`` is explicitly one of the recognised dev/test values (an unset
  ``APP_ENV`` is NOT permitted).

A model integrity check passing is never, on its own, evidence that a real
defect detector exists; see ``app.ai.local_inference_policy``.
"""
from __future__ import annotations

# Explicit, non-detection result states shared by every inference path.
STATUS_AI_UNAVAILABLE = "ai_unavailable"
STATUS_FAILED = "failed"

# Stored on legacy ``Inspection.inference_mode``.
MODE_AI_UNAVAILABLE = "ai_unavailable"
MODE_INFERENCE_FAILED = "inference_failed"
MODE_SIMULATED = "deterministic-fallback"
MODE_TRAINED = "trained-yolo"

# Sentinel stored in ``detected_issue`` when nothing was evaluated. It is never a
# defect category and never means "clean".
NOT_EVALUATED = "not_evaluated"


def simulation_permitted() -> bool:
    """True only in an explicit dev/test environment that opted in to simulation.

    Fail-closed: any error resolving settings is treated as "not permitted".
    """
    try:
        from app.config import get_settings

        return bool(get_settings().demo_scoring_effective)
    except Exception:
        return False
