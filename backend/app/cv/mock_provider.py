"""Deterministic mock CV provider.

No GPU or external API required. Outputs are seeded from the image URL
so the same input always returns the same result — stable for tests and demos.

Design:
- Seeds a PRNG from hash(image_url) for reproducibility.
- Mimics realistic finding distributions based on instrument category keywords.
- Barcode/QR values are parsed from the URL path or returned as fixture strings.
- Baseline match % is high (85-98) for known fixture URLs, moderate otherwise.
"""
from __future__ import annotations

import hashlib
import os
import random
import time
import uuid
from typing import Any

from app.cv.base import BaseCVProvider
from app.schemas.cv import (
    BaselineComparisonResult,
    BoundingBox,
    CVAnalysisRequest,
    CVInferenceResult,
    IdentifierReads,
    InstrumentIdentity,
    RegionOfInterest,
)

# ── Fixture knowledge ─────────────────────────────────────────────────────────

_KNOWN_INSTRUMENTS: dict[str, dict[str, str]] = {
    "frazier": {"name": "Frazier Suction Tube 8Fr", "category": "lumened instrument", "model": "FRAZ-8FR-001"},
    "kerrison": {"name": "Kerrison Rongeur 3mm", "category": "non-lumened instrument", "model": "KR-3MM-STR"},
    "laparoscope": {"name": "Laparoscope 10mm 0°", "category": "rigid scope", "model": "LAP-10-STR"},
    "bovie": {"name": "Bovie Electrosurgical Pencil", "category": "other", "model": "BOVIE-E1"},
}

_FINDING_CATALOGUE: list[dict[str, Any]] = [
    {"label": "blood residue", "finding_category": "blood / retained blood residue", "severity": "critical", "weight": 0.18},
    {"label": "bone fragment", "finding_category": "bone / bone fragment", "severity": "high", "weight": 0.08},
    {"label": "retained tissue", "finding_category": "tissue / retained tissue", "severity": "high", "weight": 0.10},
    {"label": "debris accumulation", "finding_category": "debris / retained debris", "severity": "medium", "weight": 0.15},
    {"label": "surface corrosion", "finding_category": "corrosion / surface rust", "severity": "medium", "weight": 0.12},
    {"label": "hairline crack", "finding_category": "crack / hairline fracture", "severity": "critical", "weight": 0.06},
    {"label": "insulation degradation", "finding_category": "insulation damage", "severity": "critical", "weight": 0.05},
    {"label": "bioburden residue", "finding_category": "bioburden / retained debris", "severity": "high", "weight": 0.14},
    {"label": "surface pitting", "finding_category": "pitting", "severity": "medium", "weight": 0.07},
    {"label": "lumen blockage", "finding_category": "lumen blockage", "severity": "high", "weight": 0.05},
]

_BARCODE_FIXTURES: dict[str, str] = {
    "frazier": "STRYKER-FRAZ-8FR-001",
    "kerrison": "STRYKER-KR-3MM-001",
    "default": "LUMENAI-DEMO-INSTR-001",
}

_QR_FIXTURES: dict[str, str] = {
    "frazier": "QR-STR-FRAZ-8FR-001",
    "kerrison": "QR-STR-KR-3MM-001",
    "default": "QR-LUMENAI-DEMO-001",
}


def _seed_from_url(url: str) -> int:
    return int(hashlib.md5(url.encode()).hexdigest()[:8], 16)  # noqa: S324


def _instrument_hint(url: str, instrument_hint: str) -> str:
    combined = (url + instrument_hint).lower()
    for key in _KNOWN_INSTRUMENTS:
        if key in combined:
            return key
    return "default"


class MockCVProvider(BaseCVProvider):
    """Deterministic mock — no external dependencies."""

    @property
    def provider_name(self) -> str:
        return "mock"

    @property
    def model_versions(self) -> dict[str, str]:
        return {
            "instrument_classifier": "mock-v1.0",
            "finding_detector": "mock-v1.0",
            "identifier_reader": "mock-v1.0",
            "baseline_comparator": "mock-v1.0",
        }

    # ── Public interface ──────────────────────────────────────────────────────

    def identify_instrument(self, image_url: str, instrument_hint: str = "") -> InstrumentIdentity:
        rng = random.Random(_seed_from_url(image_url))
        key = _instrument_hint(image_url, instrument_hint)
        info = _KNOWN_INSTRUMENTS.get(key)
        if info:
            return InstrumentIdentity(
                recognized=True,
                instrument_name=info["name"],
                instrument_category=info["category"],
                model_number=info["model"],
                confidence=round(rng.uniform(0.88, 0.98), 3),
                match_method="visual" if not instrument_hint else "barcode",
            )
        return InstrumentIdentity(
            recognized=rng.random() > 0.2,
            instrument_name=instrument_hint or "Unknown Surgical Instrument",
            instrument_category="other",
            model_number="",
            confidence=round(rng.uniform(0.55, 0.75), 3),
            match_method="visual",
        )

    def read_identifiers(self, image_url: str) -> IdentifierReads:
        rng = random.Random(_seed_from_url(image_url + "id"))
        key = _instrument_hint(image_url, "")
        barcode = _BARCODE_FIXTURES.get(key, _BARCODE_FIXTURES["default"])
        qr = _QR_FIXTURES.get(key, _QR_FIXTURES["default"])
        # Simulate occasional read failures
        barcode_ok = rng.random() > 0.15
        qr_ok = rng.random() > 0.20
        return IdentifierReads(
            barcode_value=barcode if barcode_ok else "",
            barcode_confidence=round(rng.uniform(0.90, 0.99), 3) if barcode_ok else 0.0,
            barcode_format="code_128" if barcode_ok else "",
            qr_value=qr if qr_ok else "",
            qr_confidence=round(rng.uniform(0.88, 0.99), 3) if qr_ok else 0.0,
            key_dot_value="",   # KeyDot requires dedicated hardware scanner
            key_dot_confidence=0.0,
            udi_value=barcode if barcode_ok else "",
        )

    def compare_baseline(self, inspection_url: str, baseline_url: str) -> BaselineComparisonResult:
        if not baseline_url:
            return BaselineComparisonResult(
                compared=False,
                verdict="no_baseline",
                comparison_method="mock",
            )
        rng = random.Random(_seed_from_url(inspection_url + baseline_url))
        # Fixture URLs → high match; unknown → moderate
        is_fixture = any(k in baseline_url.lower() for k in _KNOWN_INSTRUMENTS)
        match_pct = round(rng.uniform(85, 98) if is_fixture else rng.uniform(48, 82), 1)
        ssim = round(match_pct / 100 * rng.uniform(0.95, 1.0), 3)
        color_delta = round(rng.uniform(1.2, 4.5) if match_pct > 80 else rng.uniform(8.0, 22.0), 2)
        verdict = "pass" if match_pct >= 80 else "review_required" if match_pct >= 60 else "fail"

        anomalies: list[RegionOfInterest] = []
        if match_pct < 80:
            anomalies.append(RegionOfInterest(
                roi_id=str(uuid.uuid4())[:8],
                label="baseline deviation",
                finding_category="baseline mismatch",
                severity="medium" if match_pct >= 60 else "high",
                confidence=round(1.0 - match_pct / 100, 3),
                bbox=BoundingBox(x=0.2, y=0.3, width=0.4, height=0.3),
                area_pct=round(rng.uniform(5, 25), 1),
                evidence_description=f"Visual deviation from baseline ({match_pct}% match)",
                model_name="baseline_comparator",
            ))
        return BaselineComparisonResult(
            compared=True,
            match_pct=match_pct,
            structural_similarity=ssim,
            color_delta=color_delta,
            anomaly_regions=anomalies,
            comparison_method="mock",
            baseline_image_url=baseline_url,
            verdict=verdict,
        )

    def _detect_findings(self, image_url: str, instrument_category: str) -> list[RegionOfInterest]:
        rng = random.Random(_seed_from_url(image_url + "findings"))
        # Lumened instruments and scopes are higher-risk
        risk_factor = 1.4 if any(k in instrument_category.lower() for k in ["lumened", "scope"]) else 1.0
        regions: list[RegionOfInterest] = []
        for entry in _FINDING_CATALOGUE:
            raw_p = entry["weight"] * risk_factor
            if rng.random() < min(raw_p, 0.55):
                confidence = round(rng.uniform(0.70, 0.97), 3)
                severity = entry["severity"]
                # Downgrade severity on moderate confidence
                if confidence < 0.80 and severity == "critical":
                    severity = "high"
                regions.append(RegionOfInterest(
                    roi_id=str(uuid.uuid4())[:8],
                    label=entry["label"],
                    finding_category=entry["finding_category"],
                    severity=severity,
                    confidence=confidence,
                    bbox=BoundingBox(
                        x=round(rng.uniform(0.05, 0.70), 3),
                        y=round(rng.uniform(0.05, 0.70), 3),
                        width=round(rng.uniform(0.05, 0.30), 3),
                        height=round(rng.uniform(0.05, 0.25), 3),
                    ),
                    area_pct=round(rng.uniform(0.5, 12.0), 1),
                    evidence_description=f"Detected {entry['label']} in inspection image",
                    model_name="finding_detector",
                ))
        return regions

    def _aggregate_scores(self, regions: list[RegionOfInterest]) -> tuple[float, float, float]:
        """Return (contamination_score, damage_score, overall) — 0-100, higher = cleaner."""
        contamination_cats = {
            "blood / retained blood residue", "bone / bone fragment",
            "tissue / retained tissue", "debris / retained debris",
            "bioburden / retained debris",
        }
        damage_cats = {
            "corrosion / surface rust", "crack / hairline fracture",
            "insulation damage", "pitting", "lumen blockage",
            "mechanical damage", "seal integrity failure",
        }
        sev_weight = {"critical": 25, "high": 15, "medium": 8, "low": 3}
        c_pen = sum(sev_weight.get(r.severity, 5) for r in regions if r.finding_category in contamination_cats)
        d_pen = sum(sev_weight.get(r.severity, 5) for r in regions if r.finding_category in damage_cats)
        c_score = max(0.0, round(100.0 - c_pen, 1))
        d_score = max(0.0, round(100.0 - d_pen, 1))
        overall = round((c_score * 0.6 + d_score * 0.4), 1)
        return c_score, d_score, overall

    def _build_ranking_inputs(
        self,
        identity: InstrumentIdentity,
        identifiers: IdentifierReads,
        regions: list[RegionOfInterest],
        baseline: BaselineComparisonResult | None,
        req: CVAnalysisRequest,
    ) -> dict[str, Any]:
        dominant = max(regions, key=lambda r: r.confidence, default=None)
        baseline_status = ""
        if baseline:
            if baseline.verdict == "pass":
                baseline_status = "approved_baseline_found"
            elif baseline.verdict == "review_required":
                baseline_status = "pending_baseline_review"
            else:
                baseline_status = "no_approved_baseline"
        return {
            "finding_id": req.finding_id,
            "finding_category": dominant.finding_category if dominant else "other",
            "severity": dominant.severity if dominant else "low",
            "confidence_score": round(dominant.confidence if dominant else 0.5, 3),
            "instrument_id": req.instrument_id,
            "instrument_name": identity.instrument_name,
            "instrument_category": identity.instrument_category,
            "barcode_value": identifiers.barcode_value,
            "qr_code_value": identifiers.qr_value,
            "key_dot_value": identifiers.key_dot_value,
            "baseline_status": baseline_status,
            "instrument_match_status": "matched" if identity.recognized else "unmatched",
            "tenant_id": req.tenant_id,
        }

    def analyze(self, req: CVAnalysisRequest) -> CVInferenceResult:
        t0 = time.monotonic()
        image_url = req.image_url or f"data:image/{req.tenant_id}"
        inference_id = f"inf-{uuid.uuid4().hex[:12]}"
        warnings: list[str] = []

        if not req.image_url and not req.image_data_b64:
            warnings.append("No image_url or image_data_b64 provided; using mock fixture.")

        identity = self.identify_instrument(image_url, req.instrument_name)
        identifiers = self.read_identifiers(image_url) if "identifier_reading" in req.requested_capabilities else IdentifierReads()
        regions = self._detect_findings(image_url, req.instrument_category or identity.instrument_category) if any(
            c in req.requested_capabilities for c in ["contamination_detection", "damage_detection"]
        ) else []
        baseline = self.compare_baseline(image_url, req.baseline_image_url) if req.baseline_image_url and "baseline_comparison" in req.requested_capabilities else None
        c_score, d_score, overall = self._aggregate_scores(regions)
        ranking_inputs = self._build_ranking_inputs(identity, identifiers, regions, baseline, req)

        # R9: apply temperature scaling to region confidence scores
        temperature = float(os.environ.get("CV_CALIBRATION_TEMPERATURE", "1.0"))
        if temperature != 1.0 and regions:
            import math
            regions = [
                r.model_copy(update={"confidence": round(
                    1.0 / (1.0 + math.exp(-math.log(r.confidence / (1 - r.confidence + 1e-9)) / temperature)), 4
                )})
                for r in regions
            ]

        # R10: flag for active learning review when dominant confidence is low
        dominant_conf = max((r.confidence for r in regions), default=1.0)
        review_required = dominant_conf < float(os.environ.get("CV_REVIEW_CONFIDENCE_THRESHOLD", "0.70"))

        processing_ms = int((time.monotonic() - t0) * 1000)
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
            processing_ms=processing_ms,
            image_url=image_url,
            warnings=warnings,
            calibration_temperature=temperature,
            review_required=review_required,
            provider_cost_usd=0.0,   # R12: mock has no cost
        )
