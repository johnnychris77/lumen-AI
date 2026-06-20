"""CV provider registry — resolves the active provider from CV_PROVIDER env var."""
from __future__ import annotations

import os
from typing import ClassVar

from app.cv.base import BaseCVProvider


class CVRegistry:
    _providers: ClassVar[dict[str, type[BaseCVProvider]]] = {}
    _active: ClassVar[BaseCVProvider | None] = None

    @classmethod
    def register(cls, name: str, provider_cls: type[BaseCVProvider]) -> None:
        cls._providers[name] = provider_cls

    @classmethod
    def get_provider(cls) -> BaseCVProvider:
        if cls._active is not None:
            return cls._active
        name = os.getenv("CV_PROVIDER", "mock").strip().lower()
        if name not in cls._providers:
            # Always fall back to mock — never fail on missing provider
            name = "mock"
        cls._active = cls._providers[name]()
        return cls._active

    @classmethod
    def reset(cls) -> None:
        """Force re-instantiation on next call (useful in tests)."""
        cls._active = None


# ── Auto-register built-in providers ─────────────────────────────────────────
from app.cv.mock_provider import MockCVProvider  # noqa: E402

CVRegistry.register("mock", MockCVProvider)
