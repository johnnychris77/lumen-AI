"""R5: ONNX Runtime CV provider.

Requires:
  pip install onnxruntime pillow numpy
  CV_ONNX_MODEL_DIR=/path/to/models   (contains instrument_classifier.onnx,
                                        finding_detector.onnx)

This provider implements the same BaseCVProvider interface as MockCVProvider
so it can be selected at runtime via  CV_PROVIDER=onnx  without any API changes.

When ONNX model files are not present, falls back to raising a clear
ConfigurationError so the registry can log it and remain on the mock.
"""
from __future__ import annotations

import os
import time
import uuid
from pathlib import Path
from typing import Any

from app.cv.base import BaseCVProvider
from app.cv.ssim_comparator import compare_images
from app.schemas.cv import (
    BaselineComparisonResult,
    BoundingBox,
    CVAnalysisRequest,
    CVInferenceResult,
    IdentifierReads,
    InstrumentIdentity,
    RegionOfInterest,
)


class OnnxCVProvider(BaseCVProvider):
    """Production CV provider backed by local ONNX Runtime inference."""

    MODEL_DIR = Path(os.environ.get("CV_ONNX_MODEL_DIR", "/opt/lumenai/models"))

    def __init__(self) -> None:
        try:
            import onnxruntime as ort  # type: ignore[import-untyped]
        except ImportError as exc:
            raise RuntimeError(
                "onnxruntime is not installed. "
                "Run: pip install onnxruntime  (CPU) or onnxruntime-gpu"
            ) from exc

        classifier_path = self.MODEL_DIR / "instrument_classifier.onnx"
        detector_path = self.MODEL_DIR / "finding_detector.onnx"

        if not classifier_path.exists():
            raise FileNotFoundError(
                f"ONNX model not found: {classifier_path}. "
                "Set CV_ONNX_MODEL_DIR to the directory containing "
                "instrument_classifier.onnx and finding_detector.onnx"
            )

        self._classifier = ort.InferenceSession(str(classifier_path))
        self._detector = ort.InferenceSession(str(detector_path)) if detector_path.exists() else None
        self._ort = ort

    @property
    def provider_name(self) -> str:
        return "onnx"

    @property
    def model_versions(self) -> dict[str, str]:
        return {
            "instrument_classifier": _read_version_tag(self.MODEL_DIR / "instrument_classifier.version"),
            "finding_detector": _read_version_tag(self.MODEL_DIR / "finding_detector.version"),
            "identifier_reader": "pyzbar-0.1",
            "baseline_comparator": "ssim-scikit-1.0",
        }

    def identify_instrument(self, image_url: str, instrument_hint: str = "") -> InstrumentIdentity:
        try:
            import numpy as np
            import httpx  # noqa: E401

            resp = httpx.get(image_url, timeout=5.0, follow_redirects=True)
            img = _preprocess_image(resp.content, size=(224, 224))
            outputs = self._classifier.run(None, {"input": img})
            # outputs[0] shape: [1, num_classes]; outputs[1]: class labels (optional)
            probs = outputs[0][0]
            top_idx = int(np.argmax(probs))
            confidence = float(probs[top_idx])

            # Read label map from model directory
            labels = _load_labels(self.MODEL_DIR / "instrument_classes.txt")
            instrument_name = labels[top_idx] if top_idx < len(labels) else "Unknown"

            return InstrumentIdentity(
                recognized=confidence >= 0.60,
                instrument_name=instrument_name,
                instrument_category=_infer_category(instrument_name),
                confidence=round(confidence, 4),
                match_method="onnx_classifier",
            )
        except Exception as exc:
            return InstrumentIdentity(
                recognized=False,
                instrument_name=instrument_hint or "",
                error_message=str(exc),
            )

    def read_identifiers(self, image_url: str) -> IdentifierReads:
        from app.cv.identifier_decoder import decode_from_url
        decoded = decode_from_url(image_url)
        return IdentifierReads(
            barcode_value=decoded.barcode_value,
            barcode_confidence=decoded.barcode_confidence,
            barcode_format=decoded.barcode_format,
            qr_value=decoded.qr_value,
            qr_confidence=decoded.qr_confidence,
            key_dot_value=decoded.key_dot_value,
            key_dot_confidence=decoded.key_dot_confidence,
            udi_value=decoded.udi_value,
        )

    def compare_baseline(self, inspection_url: str, baseline_url: str) -> BaselineComparisonResult:
        if not baseline_url:
            return BaselineComparisonResult(compared=False, verdict="no_baseline", comparison_method="ssim")
        result = compare_images(inspection_url, baseline_url)
        verdict = "pass" if result.match_pct >= 80 else "review_required" if result.match_pct >= 60 else "fail"
        anomalies: list[RegionOfInterest] = []
        for x, y, w, h in result.diff_regions:
            anomalies.append(RegionOfInterest(
                roi_id=str(uuid.uuid4())[:8],
                label="baseline deviation",
                finding_category="baseline mismatch",
                severity="medium" if result.match_pct >= 60 else "high",
                confidence=round(1.0 - result.structural_similarity, 3),
                bbox=BoundingBox(x=x, y=y, width=w, height=h),
                model_name="ssim_comparator",
            ))
        return BaselineComparisonResult(
            compared=True,
            match_pct=result.match_pct,
            structural_similarity=result.structural_similarity,
            color_delta=result.color_delta,
            anomaly_regions=anomalies,
            comparison_method=result.backend,
            baseline_image_url=baseline_url,
            verdict=verdict,
        )

    def analyze(self, req: CVAnalysisRequest) -> CVInferenceResult:
        t0 = time.monotonic()
        inference_id = f"inf-{uuid.uuid4().hex[:12]}"
        warnings: list[str] = []
        image_url = req.image_url

        if not image_url and not req.image_data_b64:
            warnings.append("No image_url or image_data_b64 provided")

        identity = self.identify_instrument(image_url, req.instrument_name)
        identifiers = (
            self.read_identifiers(image_url)
            if "identifier_reading" in req.requested_capabilities
            else IdentifierReads()
        )
        regions = self._run_detector(image_url, req) if self._detector else []
        baseline = (
            self.compare_baseline(image_url, req.baseline_image_url)
            if req.baseline_image_url and "baseline_comparison" in req.requested_capabilities
            else None
        )

        from app.cv.mock_provider import MockCVProvider
        _mock = MockCVProvider()
        c_score, d_score, overall = _mock._aggregate_scores(regions)
        ranking_inputs = _mock._build_ranking_inputs(identity, identifiers, regions, baseline, req)

        return CVInferenceResult(
            inference_id=inference_id,
            status="success",
            context=req.context,
            tenant_id=req.tenant_id,
            facility_id=req.facility_id,
            instrument_identity=identity,
            identifier_reads=identifiers,
            regions=regions,
            contamination_score=c_score,
            damage_score=d_score,
            overall_cleanliness_score=overall,
            baseline_comparison=baseline,
            ranking_inputs=ranking_inputs,
            provider=self.provider_name,
            model_versions=self.model_versions,
            processing_ms=int((time.monotonic() - t0) * 1000),
            image_url=image_url,
            warnings=warnings,
        )

    def _run_detector(self, image_url: str, req: CVAnalysisRequest) -> list[RegionOfInterest]:
        try:
            import httpx  # noqa: E401

            resp = httpx.get(image_url, timeout=8.0, follow_redirects=True)
            img = _preprocess_image(resp.content, size=(640, 640))
            outputs = self._detector.run(None, {"images": img})
            # outputs[0]: [1, num_detections, 6]  (x1,y1,x2,y2,conf,class)
            detections = outputs[0][0]
            labels = _load_labels(self.MODEL_DIR / "finding_classes.txt")
            regions: list[RegionOfInterest] = []
            for det in detections:
                x1, y1, x2, y2, conf, cls_idx = det
                if conf < 0.45:
                    continue
                label = labels[int(cls_idx)] if int(cls_idx) < len(labels) else "unknown"
                regions.append(RegionOfInterest(
                    roi_id=str(uuid.uuid4())[:8],
                    label=label,
                    finding_category=label,
                    severity=_severity_from_class(label),
                    confidence=round(float(conf), 4),
                    bbox=BoundingBox(
                        x=round(float(x1), 4), y=round(float(y1), 4),
                        width=round(float(x2 - x1), 4), height=round(float(y2 - y1), 4),
                    ),
                    model_name="finding_detector",
                ))
            return regions
        except Exception:
            return []


# ── Helpers ───────────────────────────────────────────────────────────────────

def _preprocess_image(raw: bytes, size: tuple[int, int]) -> Any:
    import numpy as np
    from PIL import Image
    import io
    img = Image.open(io.BytesIO(raw)).convert("RGB").resize(size)
    arr = np.array(img).astype(np.float32) / 255.0
    return arr.transpose(2, 0, 1)[None]  # NCHW


def _load_labels(path: Path) -> list[str]:
    if path.exists():
        return [line.strip() for line in path.read_text().splitlines() if line.strip()]
    return []


def _read_version_tag(path: Path) -> str:
    return path.read_text().strip() if path.exists() else "unknown"


def _infer_category(name: str) -> str:
    nl = name.lower()
    if "scope" in nl or "laparoscope" in nl or "endoscope" in nl:
        return "rigid scope"
    if "frazier" in nl or "suction" in nl or "lumen" in nl:
        return "lumened instrument"
    return "non-lumened instrument"


def _severity_from_class(label: str) -> str:
    ll = label.lower()
    if any(k in ll for k in ["blood", "crack", "insulation", "bone"]):
        return "critical"
    if any(k in ll for k in ["tissue", "corrosion", "blockage"]):
        return "high"
    if any(k in ll for k in ["debris", "pitting", "bioburden"]):
        return "medium"
    return "low"
