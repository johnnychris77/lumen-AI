"""CV provider registry — resolves the active provider, fail-closed (P4.7.1).

Before P4.7.1 an unset or unknown ``CV_PROVIDER`` silently selected the mock
provider, whose findings are pseudo-random numbers seeded from the image URL.
That default is removed:

* ``mock`` is available ONLY when simulation is explicitly permitted (an
  explicit dev/test ``APP_ENV`` AND ``AI_ALLOW_DEMO_SCORING``), see
  ``app.ai.inference_gate``.
* An unset provider, an unknown provider, a provider that is not installed, or
  a provider whose model artifacts fail integrity verification all resolve to
  ``UnavailableCVProvider`` — never to the mock.
"""
from __future__ import annotations

import logging
import os

from app.ai.inference_gate import STATUS_FAILED, simulation_permitted
from app.cv.base import BaseCVProvider
from app.cv.unavailable_provider import DEFAULT_REASON, UnavailableCVProvider

logger = logging.getLogger(__name__)

SIMULATION_DISABLED_REASON = (
    "The simulated (mock) CV provider is disabled outside an explicit "
    "development/test environment."
)


class CVRegistry:
    _providers: dict[str, type[BaseCVProvider]] = {}
    _instances: dict[str, BaseCVProvider] = {}

    @classmethod
    def register(cls, name: str, provider_cls: type[BaseCVProvider]) -> None:
        cls._providers[name] = provider_cls

    @classmethod
    def _instance(cls, name: str) -> BaseCVProvider:
        inst = cls._instances.get(name)
        if inst is None:
            inst = cls._providers[name]()
            cls._instances[name] = inst
        return inst

    @classmethod
    def get_provider(cls) -> BaseCVProvider:
        """Resolve the provider for THIS call.

        The simulation gate is evaluated on every call (it is never cached), so
        a process that starts in one configuration cannot keep serving the mock
        after the gate closes.
        """
        requested = os.getenv("CV_PROVIDER", "").strip().lower()

        if requested in ("", "mock"):
            if simulation_permitted() and "mock" in cls._providers:
                return cls._instance("mock")
            return UnavailableCVProvider(
                SIMULATION_DISABLED_REASON if requested == "mock" else DEFAULT_REASON
            )

        if requested not in cls._providers:
            return UnavailableCVProvider("The configured CV provider is not available in this build.")

        try:
            return cls._instance(requested)
        except Exception as exc:  # missing weights, failed integrity pin, missing runtime
            # Log the class only: messages may contain filesystem paths.
            logger.warning("CV provider %r could not be initialised (%s)", requested, type(exc).__name__)
            from app.ai.local_inference_policy import LocalInferenceUnavailable

            reason = (
                f"CV model unavailable: {exc}" if isinstance(exc, LocalInferenceUnavailable)
                else "The configured CV model could not be initialised."
            )
            return UnavailableCVProvider(reason, status=STATUS_FAILED)

    @classmethod
    def reset(cls) -> None:
        """Drop cached provider instances (useful in tests)."""
        cls._instances.clear()


# ── Auto-register built-in providers ─────────────────────────────────────────
from app.cv.mock_provider import MockCVProvider  # noqa: E402

CVRegistry.register("mock", MockCVProvider)


def _try_register_onnx() -> None:
    """Register the ONNX provider class. Construction (which loads and
    integrity-checks the model artifacts) happens lazily in ``get_provider``
    and fails closed there."""
    try:
        from app.cv.onnx_provider import OnnxCVProvider  # noqa: PLC0415
        CVRegistry.register("onnx", OnnxCVProvider)
    except Exception:  # pragma: no cover - import-time failure of the module itself
        pass


_try_register_onnx()
