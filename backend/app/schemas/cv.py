"""Computer Vision inference schemas for LumenAI P4."""
from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel, Field


# ── Input ─────────────────────────────────────────────────────────────────────

class CVAnalysisRequest(BaseModel):
    """Primary image analysis request."""
    image_url: str = ""
    image_data_b64: str = ""          # base64-encoded image bytes (alternative to URL)
    context: Literal["inspection", "baseline_comparison", "barcode_scan", "training"] = "inspection"
    instrument_name: str = ""
    instrument_category: str = ""
    instrument_id: int | None = None
    finding_id: int | None = None
    baseline_image_url: str = ""      # if set, runs baseline comparison
    barcode_hint: str = ""            # optional known barcode to aid recognition
    # P4.7.1 (SEC-R2-01): accepted for backward compatibility ONLY. It is never
    # trusted — every CV route overwrites it with the tenant of the
    # authenticated, membership-verified caller before any work is done.
    tenant_id: str = "default-tenant"
    facility_id: str = ""              # identifies the hospital/facility within a multi-hospital tenant
    requested_capabilities: list[str] = Field(
        default_factory=lambda: [
            "instrument_recognition",
            "identifier_reading",
            "contamination_detection",
            "damage_detection",
            "baseline_comparison",
        ]
    )


class BaselineCompareRequest(BaseModel):
    """Dedicated baseline comparison between inspection image and reference."""
    inspection_image_url: str
    baseline_image_url: str
    instrument_name: str = ""
    instrument_category: str = ""
    tenant_id: str = "default-tenant"


class CVVideoAnalysisRequest(BaseModel):
    """R11: Borescope video analysis request."""
    video_url: str
    sample_fps: float = Field(default=1.0, ge=0.1, le=10.0)
    instrument_name: str = ""
    instrument_category: str = ""
    tenant_id: str = "default-tenant"
    requested_capabilities: list[str] = Field(
        default_factory=lambda: [
            "instrument_recognition",
            "contamination_detection",
            "damage_detection",
        ]
    )


class CVVideoFrame(BaseModel):
    """Single frame result within a video analysis."""
    frame_index: int
    timestamp_sec: float
    inference_id: str
    regions: list[RegionOfInterest] = Field(default_factory=list)
    # None = not evaluated (never a default "100 = clean").
    contamination_score: float | None = Field(ge=0.0, le=100.0, default=None)
    damage_score: float | None = Field(ge=0.0, le=100.0, default=None)
    status: str = "success"


class CVVideoAnalysisResult(BaseModel):
    """R11: Aggregated video analysis result."""
    video_url: str
    frames_analyzed: int
    total_duration_sec: float
    # None = no frame was evaluated by a real model (never a default "100 = clean").
    worst_contamination_score: float | None = Field(ge=0.0, le=100.0, default=None)
    worst_damage_score: float | None = Field(ge=0.0, le=100.0, default=None)
    finding_timeline: list[CVVideoFrame] = Field(default_factory=list)
    composite_regions: list[RegionOfInterest] = Field(default_factory=list)
    provider: str = ""
    processing_ms: int = 0
    warnings: list[str] = Field(default_factory=list)
    # P4.7.1: explicit result state — see CVInferenceResult.
    status: str = "success"
    simulated: bool = False
    evidence_class: str = ""
    unavailable_reason: str = ""
    human_review_required: bool = True


class AnnotationRequest(BaseModel):
    """R10: Human annotation of a low-confidence inference."""
    annotator_id: str
    confirmed_regions: list[dict] = Field(default_factory=list)
    rejected_region_ids: list[str] = Field(default_factory=list)
    corrected_severity: str = ""
    notes: str = ""


# ── Sub-models ────────────────────────────────────────────────────────────────

class BoundingBox(BaseModel):
    """Normalized [0-1] bounding box."""
    x: float = Field(ge=0.0, le=1.0)
    y: float = Field(ge=0.0, le=1.0)
    width: float = Field(ge=0.0, le=1.0)
    height: float = Field(ge=0.0, le=1.0)


class RegionOfInterest(BaseModel):
    """A single detected region with label, confidence, and location."""
    roi_id: str
    label: str                         # human-readable ("blood residue", "crack", …)
    finding_category: str              # maps to P3 category enum
    severity: str                      # low | medium | high | critical
    confidence: float = Field(ge=0.0, le=1.0)
    bbox: BoundingBox | None = None
    area_pct: float = 0.0             # % of image area affected
    evidence_description: str = ""
    model_name: str = ""               # which sub-model detected this
    # P4.7.1: True when this region was produced by the dev/test simulation, not
    # by a model looking at the image. A simulated region is never a detection.
    simulated: bool = False


class InstrumentIdentity(BaseModel):
    """Instrument recognition result."""
    recognized: bool
    instrument_name: str = ""
    instrument_category: str = ""
    model_number: str = ""
    confidence: float = 0.0
    match_method: str = ""             # "barcode" | "qr" | "keydot" | "visual" | "none"


class IdentifierReads(BaseModel):
    """Decoded identifier values from the image."""
    barcode_value: str = ""
    barcode_confidence: float = 0.0
    barcode_format: str = ""           # code_128 | ean_13 | etc.
    qr_value: str = ""
    qr_confidence: float = 0.0
    key_dot_value: str = ""
    key_dot_confidence: float = 0.0
    udi_value: str = ""


class BaselineComparisonResult(BaseModel):
    """Structural similarity between inspection image and reference baseline."""
    compared: bool
    match_pct: float = 0.0            # 0-100
    structural_similarity: float = 0.0  # SSIM-like 0-1
    color_delta: float = 0.0          # perceptual color distance (lower = more similar)
    anomaly_regions: list[RegionOfInterest] = Field(default_factory=list)
    comparison_method: str = ""       # "mock" | "ssim" | "feature_match" | "embedding"
    baseline_image_url: str = ""
    verdict: str = ""                 # "pass" | "review_required" | "fail"


class CVKPISummary(BaseModel):
    total_analyses: int
    recognized_count: int
    recognition_rate_pct: float
    barcode_read_count: int
    qr_read_count: int
    key_dot_read_count: int
    blood_detections: int
    bone_detections: int
    tissue_detections: int
    corrosion_detections: int
    crack_detections: int
    insulation_defect_detections: int
    residue_detections: int
    baseline_comparisons_run: int
    baseline_pass_count: int
    baseline_fail_count: int
    avg_confidence: float
    avg_baseline_match_pct: float
    # R12: telemetry
    avg_processing_ms: float = 0.0
    total_provider_cost_usd: float = 0.0
    # R10: active learning queue size
    review_queue_size: int = 0
    # P4.7.1 (SCI-17): the defect/recognition KPIs above count ONLY records
    # produced by integrity-verified model inference. Everything else is
    # reported here, separately, and never added into those KPIs.
    genuine_analyses: int = 0
    simulated_excluded_count: int = 0
    unavailable_or_failed_count: int = 0
    legacy_unverified_excluded_count: int = 0
    evidence_basis: str = "model_inference_only"


# ── Primary inference result ───────────────────────────────────────────────────

class CVInferenceResult(BaseModel):
    """Full output of one CV pipeline run."""
    inference_id: str
    # "ai_unavailable": no approved, integrity-verified model could run — nothing
    # was evaluated. "failed": a model was configured but loading or execution
    # failed. Neither is ever a clean instrument.
    status: Literal["success", "partial", "failed", "ai_unavailable"] = "success"
    context: str = "inspection"
    tenant_id: str = "default-tenant"
    facility_id: str = ""

    # Recognition
    instrument_identity: InstrumentIdentity
    identifier_reads: IdentifierReads

    # Findings (all detected ROIs across all sub-models)
    regions: list[RegionOfInterest] = Field(default_factory=list)

    # Aggregate scores (0-100, higher = cleaner instrument). None = not
    # evaluated. P4.7.1: the default is no longer 100 ("perfectly clean") — a
    # result that never ran must not carry a score.
    contamination_score: float | None = Field(ge=0.0, le=100.0, default=None)
    damage_score: float | None = Field(ge=0.0, le=100.0, default=None)
    overall_cleanliness_score: float | None = Field(ge=0.0, le=100.0, default=None)

    # Baseline
    baseline_comparison: BaselineComparisonResult | None = None

    # P3 ranking engine inputs — ready to POST to /api/enterprise/ranking/score
    ranking_inputs: dict[str, Any] = Field(default_factory=dict)

    # Provenance
    provider: str = ""                 # "mock" | "onnx" | "openai_vision" | "roboflow"
    model_versions: dict[str, str] = Field(default_factory=dict)
    processing_ms: int = 0
    image_url: str = ""
    error_message: str = ""
    warnings: list[str] = Field(default_factory=list)

    # R7: Internal archive key (populated after pipeline persist)
    archived_image_key: str = ""

    # R9: Calibration temperature applied to confidence scores (1.0 = uncalibrated)
    calibration_temperature: float = 1.0

    # R12: Provider cost for this inference (0.0 for local/mock providers)
    provider_cost_usd: float = 0.0

    # R10: Active learning — set True when overall confidence < threshold
    review_required: bool = False

    # ── P4.7.1 evidence provenance ────────────────────────────────────────────
    # True when the content was produced by the dev/test simulation (mock
    # provider), not by a model looking at the image.
    simulated: bool = False
    # "model_inference" | "simulated" | "ai_unavailable" | "failed" |
    # "legacy_unverified" — see app.cv.evidence.
    evidence_class: str = ""
    # Why nothing was evaluated (status ai_unavailable / failed).
    unavailable_reason: str = ""
    # Outcome of SHA-256 pin verification for the model artifacts that ran.
    model_integrity: dict[str, Any] = Field(default_factory=dict)
    # No CV output authorizes instrument release; a person always reviews.
    human_review_required: bool = True
