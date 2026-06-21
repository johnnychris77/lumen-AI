"""Abstract base class for CV model providers.

Swap the provider by setting CV_PROVIDER env var:
  CV_PROVIDER=mock        — deterministic mock (default, no GPU required)
  CV_PROVIDER=onnx        — ONNX Runtime local inference
  CV_PROVIDER=openai      — GPT-4o vision API
  CV_PROVIDER=roboflow    — Roboflow hosted inference
  CV_PROVIDER=custom      — BYO provider registered via CVRegistry
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from app.schemas.cv import (
    BaselineComparisonResult,
    CVAnalysisRequest,
    CVInferenceResult,
    IdentifierReads,
    InstrumentIdentity,
)


class BaseCVProvider(ABC):
    """All CV providers implement this interface."""

    @property
    @abstractmethod
    def provider_name(self) -> str: ...

    @property
    @abstractmethod
    def model_versions(self) -> dict[str, str]: ...

    @abstractmethod
    def analyze(self, req: CVAnalysisRequest) -> CVInferenceResult:
        """Run full CV pipeline on the supplied image."""
        ...

    @abstractmethod
    def identify_instrument(
        self, image_url: str, instrument_hint: str = ""
    ) -> InstrumentIdentity:
        """Classify instrument type and model from image."""
        ...

    @abstractmethod
    def read_identifiers(self, image_url: str) -> IdentifierReads:
        """Decode barcode / QR / KeyDot from image."""
        ...

    @abstractmethod
    def compare_baseline(
        self, inspection_url: str, baseline_url: str
    ) -> BaselineComparisonResult:
        """Compute structural similarity between inspection and reference."""
        ...
