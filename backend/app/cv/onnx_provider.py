"""R5: ONNX Runtime CV provider — local inference, fail-closed (P4.7.1).

Requires:
  pip install onnxruntime pillow numpy
  CV_ONNX_MODEL_DIR=/path/to/models   (instrument_classifier.onnx,
                                        finding_detector.onnx)
  CV_ONNX_CLASSIFIER_SHA256=<64 hex>   SHA-256 pin of instrument_classifier.onnx
  CV_ONNX_DETECTOR_SHA256=<64 hex>     SHA-256 pin of finding_detector.onnx

P4.7.1 contract:

* **Integrity before load.** Each artifact is verified against its operator-
  supplied SHA-256 pin (``app.ai.local_inference_policy.verify_local_weights``)
  BEFORE an inference session is created. A missing file, missing pin or hash
  mismatch raises, and the registry resolves to the unavailable provider. No
  artifact is ever downloaded.
* **Failure is never "clean".** A missing detector, an unreadable image, or any
  exception during inference yields ``status="ai_unavailable"`` / ``"failed"``
  with no regions and no scores — never an empty-but-successful result
  (SCI-16).
* **No arbitrary fetch.** Image bytes come from the uploaded payload, or from an
  allow-listed https host through ``app.cv.safe_fetch`` (SEC-R2-02).

A passing integrity check proves the bytes are the pinned bytes. It is not
evidence that the model detects defects.
"""
from __future__ import annotations

import base64
import os
import time
import uuid
from pathlib import Path
from typing import Any

from app.ai.inference_gate import STATUS_AI_UNAVAILABLE, STATUS_FAILED
from app.ai.local_inference_policy import LocalInferenceUnavailable, verify_local_weights
from app.cv.base import BaseCVProvider
from app.cv.evidence import EVIDENCE_MODEL_INFERENCE
from app.cv.safe_fetch import ImageFetchError, UnsafeImageURLError, fetch_image_bytes
from app.cv.ssim_comparator import compare_image_bytes
from app.cv.unavailable_provider import unavailable_result
from app.schemas.cv import (
    BaselineComparisonResult,
    BoundingBox,
    CVAnalysisRequest,
    CVInferenceResult,
    IdentifierReads,
    InstrumentIdentity,
    RegionOfInterest,
)

_DETECTION_CAPABILITIES = ("contamination_detection", "damage_detection")


class CVInferenceError(RuntimeError):
    """Model loading or execution failed. Never interpreted as 'no findings'."""


class ImageUnavailableError(RuntimeError):
    """No image bytes could be obtained through a permitted route."""


class OnnxCVProvider(BaseCVProvider):
    """Local ONNX Runtime inference over integrity-pinned artifacts."""

    def __init__(self) -> None:
        try:
            import onnxruntime as ort  # type: ignore[import-untyped]
        except ImportError as exc:
            raise LocalInferenceUnavailable("ONNX runtime is not installed") from exc

        self.model_dir = Path(os.environ.get("CV_ONNX_MODEL_DIR", "/opt/lumenai/models"))
        classifier_path = self.model_dir / "instrument_classifier.onnx"
        detector_path = self.model_dir / "finding_detector.onnx"

        # Verify BEFORE creating any session. Raises LocalInferenceUnavailable.
        classifier_check = verify_local_weights(
            str(classifier_path), os.environ.get("CV_ONNX_CLASSIFIER_SHA256", ""),
        )
        self._integrity: dict[str, Any] = {
            "verified": True,
            "artifacts": {"instrument_classifier": classifier_check["sha256"]},
        }
        self._classifier = ort.InferenceSession(str(classifier_path))

        self._detector = None
        if detector_path.is_file():
            detector_check = verify_local_weights(
                str(detector_path), os.environ.get("CV_ONNX_DETECTOR_SHA256", ""),
            )
            self._integrity["artifacts"]["finding_detector"] = detector_check["sha256"]
            self._detector = ort.InferenceSession(str(detector_path))
        self._ort = ort

    # ── identity ──────────────────────────────────────────────────────────────

    @property
    def provider_name(self) -> str:
        return "onnx"

    @property
    def model_versions(self) -> dict[str, str]:
        ver_file = self.model_dir / "VERSION"
        tag = _read_version_tag(ver_file)
        return {
            "instrument_classifier": tag,
            "finding_detector": tag if self._detector is not None else "not_installed",
        }

    # ── image acquisition (single permitted route) ────────────────────────────

    @staticmethod
    def _image_bytes(image_url: str, image_data_b64: str = "") -> bytes:
        """Uploaded bytes are preferred; a URL is fetched only through the
        SSRF-safe, allow-listed fetcher. Raises ImageUnavailableError."""
        if image_data_b64:
            raw_b64 = image_data_b64.split(",", 1)[-1] if "," in image_data_b64 else image_data_b64
            try:
                return base64.b64decode(raw_b64, validate=True)
            except Exception as exc:
                raise ImageUnavailableError("Uploaded image payload is not valid base64.") from exc
        if not image_url:
            raise ImageUnavailableError("No image was supplied.")
        try:
            return fetch_image_bytes(image_url)
        except (UnsafeImageURLError, ImageFetchError) as exc:
            raise ImageUnavailableError(str(exc)) from exc

    # ── model execution (all failures raise) ──────────────────────────────────

    def _classify(self, image_bytes: bytes, instrument_hint: str = "") -> InstrumentIdentity:
        try:
            import numpy as np

            img = _preprocess_image(image_bytes, size=(224, 224))
            outputs = self._classifier.run(None, {"input": img})
            probs = outputs[0][0]
            top_idx = int(np.argmax(probs))
            confidence = float(probs[top_idx])
            labels = _load_labels(self.model_dir / "instrument_classes.txt")
            instrument_name = labels[top_idx] if top_idx < len(labels) else "Unknown"
        except Exception as exc:
            raise CVInferenceError("Instrument classifier failed.") from exc
        return InstrumentIdentity(
            recognized=confidence >= 0.60,
            instrument_name=instrument_name,
            instrument_category=_infer_category(instrument_name),
            confidence=round(confidence, 4),
            match_method="onnx_classifier",
        )

    def _run_detector(self, image_bytes: bytes) -> list[RegionOfInterest]:
        """Run the finding detector. ANY failure raises CVInferenceError — it
        is never converted into an empty region list (SCI-16)."""
        if self._detector is None:
            raise CVInferenceError("Finding detector is not installed.")
        try:
            img = _preprocess_image(image_bytes, size=(640, 640))
            outputs = self._detector.run(None, {"images": img})
            # outputs[0]: [1, num_detections, 6]  (x1,y1,x2,y2,conf,class)
            detections = outputs[0][0]
            labels = _load_labels(self.model_dir / "finding_classes.txt")
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
        except Exception as exc:
            raise CVInferenceError("Finding detector failed.") from exc
        return regions

    # ── BaseCVProvider interface ──────────────────────────────────────────────

    def identify_instrument(self, image_url: str, instrument_hint: str = "") -> InstrumentIdentity:
        """Interface method. Never raises and never guesses: an image that
        cannot be obtained or classified is reported as not recognized."""
        try:
            return self._classify(self._image_bytes(image_url), instrument_hint)
        except (ImageUnavailableError, CVInferenceError):
            return InstrumentIdentity(recognized=False, match_method="none")

    def read_identifiers(self, image_url: str) -> IdentifierReads:
        try:
            return self._read_identifiers(self._image_bytes(image_url))
        except ImageUnavailableError:
            return IdentifierReads()

    @staticmethod
    def _read_identifiers(image_bytes: bytes) -> IdentifierReads:
        from app.cv.identifier_decoder import decode_from_image_bytes

        decoded = decode_from_image_bytes(image_bytes)
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
        try:
            return self._compare_baseline_bytes(
                self._image_bytes(inspection_url), self._image_bytes(baseline_url), baseline_url,
            )
        except ImageUnavailableError:
            return BaselineComparisonResult(
                compared=False, verdict="unavailable", comparison_method="unavailable",
                baseline_image_url=baseline_url,
            )

    @staticmethod
    def _compare_baseline_bytes(raw_a: bytes, raw_b: bytes, baseline_url: str) -> BaselineComparisonResult:
        """A REAL pixel comparison, or an explicit 'unavailable' — never a
        fabricated similarity."""
        result = compare_image_bytes(raw_a, raw_b)
        if result is None:
            return BaselineComparisonResult(
                compared=False, verdict="unavailable", comparison_method="unavailable",
                baseline_image_url=baseline_url,
            )
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
        warnings: list[str] = []
        wants_detection = any(c in req.requested_capabilities for c in _DETECTION_CAPABILITIES)

        def _not_evaluated(reason: str, status: str) -> CVInferenceResult:
            return unavailable_result(
                req, reason=reason, status=status, provider=self.provider_name,
                model_versions=self.model_versions, model_integrity=self._integrity,
                warnings=warnings,
            )

        # Defect detection was requested but no detector exists: nothing can be
        # evaluated. This is NOT "no findings".
        if wants_detection and self._detector is None:
            return _not_evaluated("Finding detector model is not installed.", STATUS_AI_UNAVAILABLE)

        try:
            image_bytes = self._image_bytes(req.image_url, req.image_data_b64)
        except ImageUnavailableError as exc:
            return _not_evaluated(f"Image not available for analysis: {exc}", STATUS_AI_UNAVAILABLE)

        try:
            identity = self._classify(image_bytes, req.instrument_name)
            regions = self._run_detector(image_bytes) if wants_detection else []
        except CVInferenceError as exc:
            return _not_evaluated(f"Model execution failed: {exc}", STATUS_FAILED)

        identifiers = (
            self._read_identifiers(image_bytes)
            if "identifier_reading" in req.requested_capabilities
            else IdentifierReads()
        )

        baseline = None
        if req.baseline_image_url and "baseline_comparison" in req.requested_capabilities:
            try:
                baseline = self._compare_baseline_bytes(
                    image_bytes, self._image_bytes(req.baseline_image_url), req.baseline_image_url,
                )
            except ImageUnavailableError:
                baseline = BaselineComparisonResult(
                    compared=False, verdict="unavailable", comparison_method="unavailable",
                    baseline_image_url=req.baseline_image_url,
                )

        from app.cv.mock_provider import MockCVProvider  # arithmetic helpers only
        _helper = MockCVProvider()
        if wants_detection:
            c_score, d_score, overall = _helper._aggregate_scores(regions)
        else:
            c_score = d_score = overall = None  # detection was not requested: no score
        ranking_inputs = (
            _helper._build_ranking_inputs(identity, identifiers, regions, baseline, req) if regions else {}
        )

        return CVInferenceResult(
            inference_id=f"inf-{uuid.uuid4().hex[:12]}",
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
            image_url=req.image_url,
            warnings=warnings,
            simulated=False,
            evidence_class=EVIDENCE_MODEL_INFERENCE,
            model_integrity=self._integrity,
            human_review_required=True,
        )


# ── Helpers ───────────────────────────────────────────────────────────────────

def _preprocess_image(raw: bytes, size: tuple[int, int]) -> Any:
    import io

    import numpy as np
    from PIL import Image
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
