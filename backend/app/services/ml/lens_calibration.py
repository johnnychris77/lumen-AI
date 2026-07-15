"""Project Lens — Section 10: confidence calibration and abstention.

Temperature scaling (Guo et al., 2017) fit by grid search — a single scalar
``T`` that rescales a raw probability's logit before re-applying the
sigmoid. Pure Python (``math.log``/``math.exp`` only), consistent with the
rest of this codebase's no-numpy/no-sklearn constraint. Distinct from, and
layered on top of, the existing ``app.services.ml.evaluation.
calibration_report()`` (reliability bins + ECE) — that function still runs
on the *temperature-scaled* confidences produced here, so the reliability
report reflects what the live adapter will actually return.
"""
from __future__ import annotations

import math
from typing import Any

_EPS = 1e-6
_TEMPERATURE_GRID = [round(0.25 + 0.05 * i, 2) for i in range(76)]  # 0.25 .. 4.00
DEFAULT_ABSTENTION_THRESHOLD = 0.6  # used only when no bin met target_accuracy


def _clamp(p: float) -> float:
    return min(max(p, _EPS), 1.0 - _EPS)


def _logit(p: float) -> float:
    p = _clamp(p)
    return math.log(p / (1.0 - p))


def apply_temperature(raw_probability: float, temperature: float) -> float:
    """Rescale one raw probability by temperature ``T`` (T=1.0 is a no-op)."""
    if temperature <= 0:
        raise ValueError("temperature must be positive")
    z = _logit(raw_probability) / temperature
    return 1.0 / (1.0 + math.exp(-z))


def _negative_log_likelihood(y_correct: list[bool], raw_confidences: list[float], temperature: float) -> float:
    total = 0.0
    for correct, p in zip(y_correct, raw_confidences):
        calibrated = _clamp(apply_temperature(p, temperature))
        total += -math.log(calibrated if correct else (1.0 - calibrated))
    return total / len(y_correct)


def fit_temperature(y_correct: list[bool], raw_confidences: list[float]) -> dict[str, Any]:
    """Grid-search the temperature minimizing NLL on held-out (validation or
    test) predictions. Returns ``{"temperature": T, "nll": ...}``, or an
    honest ``None`` temperature (interpreted as "no scaling applied,
    T=1.0") when there are too few predictions to fit anything meaningful.
    """
    if len(y_correct) != len(raw_confidences):
        raise ValueError("y_correct and raw_confidences must be the same length")
    if len(y_correct) < 5 or len(set(y_correct)) < 2:
        return {
            "temperature": 1.0, "nll": None,
            "note": "Too few predictions (or only one outcome class) to fit a temperature; using T=1.0 (no rescaling).",
        }

    best_t, best_nll = 1.0, float("inf")
    for t in _TEMPERATURE_GRID:
        nll = _negative_log_likelihood(y_correct, raw_confidences, t)
        if nll < best_nll:
            best_t, best_nll = t, nll

    return {"temperature": best_t, "nll": round(best_nll, 4), "note": None}


def calibrated_confidences(raw_confidences: list[float], temperature: float) -> list[float]:
    return [round(apply_temperature(p, temperature), 4) for p in raw_confidences]


def resolve_abstention_threshold(calibration_report: dict[str, Any]) -> tuple[float, bool]:
    """Returns ``(threshold, is_data_derived)``. Prefers
    ``evaluation.calibration_report()``'s own ``recommended_threshold``
    (computed from real reliability bins); falls back to a disclosed
    default only when that could not be computed from this run's data."""
    recommended = calibration_report.get("recommended_threshold")
    if recommended is not None:
        return recommended, True
    return DEFAULT_ABSTENTION_THRESHOLD, False
