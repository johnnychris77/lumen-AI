"""TRC-001 — first controlled real-instrument image ingestion (research-only).

A fail-closed runner for LumenAI's first controlled ingestion exercise: two actual
operator-captured trocar photographs supplied in a PRIVATE intake kit (never committed
to git). It reuses the existing governance + retention services — it builds no new image
store.

Order of operations (fail-closed at every step):

1. Locate the private intake kit + provisional manifest. Absent ⇒ ``BLOCKED_MISSING_INTAKE_KIT``.
2. Resolve dataset-specific authorization (institutional + research-use + retention) via
   ``scientific_authorization``. Unresolved ⇒ ``BLOCKED_AUTHORIZATION``, retain nothing.
3. Only then: load JPEG bytes, verify the original SHA-256 against the manifest, validate
   decode/type/dimensions, retain via ``image_retention_service.retain_image`` (real DB),
   verify retrieval + stored hash + tenant isolation, and record the persisted ids.

Both images stay ``ground_truth_status = unknown`` and ``baseline_review = pending_review``;
neither is ever auto-labelled normal/clean/corroded/contaminated, and both are
research-training-ineligible. The borescope image is recorded as a DISPLAY photograph,
not a raw borescope export. The two images link to the SAME physical trocar while keeping
distinct image identities and modalities.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
from dataclasses import asdict, dataclass, field

from sqlalchemy.orm import Session

# The two known image identities for TRC-001 (fixed; the manifest supplies hashes/files).
TRC001_INSTRUMENT_ID = "TRC-001"
TRC001_IMAGES = {
    "TRC-001-EXT-001": {
        "modality": "external_camera", "source": "operator_captured", "condition": "unverified",
        "is_borescope_display_photo": False, "raw_borescope_export": False,
    },
    "TRC-001-BORE-001": {
        "modality": "borescope", "source": "operator_captured", "condition": "unverified",
        "reference_status": "provisional_baseline", "manufacturer_baseline": False,
        # It is a photograph of a borescope display, NOT a raw borescope export.
        "is_borescope_display_photo": True, "raw_borescope_export": False,
    },
}

# Documentation that must exist as governance records before ingestion is permitted.
_REQUIRED_AUTHORIZATION_DOCS = [
    "institutional data-authorization GovernanceApproval for the TRC-001 dataset",
    "dataset-scoped research-use consent GovernanceApproval for the TRC-001 dataset",
    "tenant research-use ConsentRecord (granted, not withdrawn)",
    "image-use rights + instrument source permission for the operator-captured trocar",
    "research retention authorization for the isolated research environment",
]


@dataclass
class ImageIntakeResult:
    image_id: str
    modality: str
    original_sha256: str = ""
    dimensions: tuple | None = None
    authorization: str = "not_evaluated"
    ingestion_attempted: bool = False
    ingestion_successful: bool = False
    retained_image_id: int | None = None
    stored_sha256: str = ""
    checksum_match: bool | None = None
    retrieval_verified: bool = False
    tenant_isolation_ok: bool | None = None
    exif_stripped: bool | None = None
    ground_truth_status: str = "unknown"
    baseline_review: str = "pending_review"
    research_training_eligible: bool = False
    is_borescope_display_photo: bool = False
    raw_borescope_export: bool = False
    reason: str = ""

    def to_dict(self) -> dict:
        d = asdict(self)
        d["dimensions"] = list(self.dimensions) if self.dimensions else None
        return d


@dataclass
class IntakeReport:
    status: str
    instrument_id: str = TRC001_INSTRUMENT_ID
    images: list = field(default_factory=list)
    imported_count: int = 0
    missing_documentation: list = field(default_factory=list)
    note: str = ""

    def to_dict(self) -> dict:
        return {"status": self.status, "instrument_id": self.instrument_id,
                "images": [i.to_dict() for i in self.images], "imported_count": self.imported_count,
                "missing_documentation": list(self.missing_documentation), "note": self.note}


def _blocked_images(reason: str) -> list:
    return [ImageIntakeResult(image_id=k, modality=v["modality"],
                              is_borescope_display_photo=v.get("is_borescope_display_photo", False),
                              raw_borescope_export=v.get("raw_borescope_export", False),
                              authorization="BLOCKED", reason=reason)
            for k, v in TRC001_IMAGES.items()]


def _validate_decode(data: bytes) -> tuple:
    """Return (width, height) if the bytes decode as a readable image; raise otherwise."""
    from PIL import Image, UnidentifiedImageError  # noqa: PLC0415

    try:
        img = Image.open(io.BytesIO(data))
        img.verify()                      # integrity check
        img2 = Image.open(io.BytesIO(data))
        img2.load()
        return img2.size
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise ValueError(f"image did not decode: {exc}") from exc


def run_trc001_intake(
    db: Session, *, kit_dir: str | None, tenant_id: str, dataset_id: str, auth=None,
) -> IntakeReport:
    """Execute the TRC-001 intake, fail-closed. See module docstring for the order."""
    # 1) Private intake kit present?
    manifest_path = os.path.join(kit_dir, "manifest.json") if kit_dir else ""
    if not kit_dir or not os.path.exists(manifest_path):
        return IntakeReport(
            status="BLOCKED_MISSING_INTAKE_KIT", images=_blocked_images("intake_kit_absent"),
            missing_documentation=["TRC-001-private-intake-kit.zip (manifest + operator JPEG bytes)"],
            note="No private intake kit/manifest present. Nothing loaded or retained; no IDs created.",
        )

    # 2) Authorization (fail-closed), resolved against governance records.
    from research.lens_vision.scientific_authorization import (  # noqa: PLC0415
        ScientificAuthorizationError,
        verify_data_authorization,
    )
    try:
        verify_data_authorization(db, tenant_id=tenant_id, dataset_id=dataset_id, auth=auth)
    except ScientificAuthorizationError as exc:
        return IntakeReport(
            status="BLOCKED_AUTHORIZATION", images=_blocked_images(f"authorization_unresolved: {exc}"),
            missing_documentation=list(_REQUIRED_AUTHORIZATION_DOCS),
            note="Authorization not resolved against governance records. No bytes retained; no IDs created. "
                 "Capturing an image personally does not establish institutional/research-use permission.",
        )

    # 3) Authorized — load the manifest and ingest each image.
    with open(manifest_path, encoding="utf-8") as f:
        manifest = json.load(f)
    entries = {e.get("image_id"): e for e in manifest.get("images", [])}

    from app.services.image_retention_service import retain_image  # noqa: PLC0415
    from app.models.retained_image import RetainedImage  # noqa: PLC0415

    results: list = []
    imported = 0
    for image_id, spec in TRC001_IMAGES.items():
        r = ImageIntakeResult(
            image_id=image_id, modality=spec["modality"],
            is_borescope_display_photo=spec.get("is_borescope_display_photo", False),
            raw_borescope_export=spec.get("raw_borescope_export", False),
            authorization="resolved")
        entry = entries.get(image_id)
        if entry is None:
            r.reason = "image_absent_from_manifest"
            results.append(r)
            continue
        fpath = os.path.join(kit_dir, str(entry.get("filename") or ""))
        if not os.path.exists(fpath):
            r.reason = "image_file_absent"
            results.append(r)
            continue
        with open(fpath, "rb") as fh:
            data = fh.read()
        r.original_sha256 = hashlib.sha256(data).hexdigest()
        # Verify original hash against the manifest (fail-closed).
        if r.original_sha256 != str(entry.get("sha256") or ""):
            r.reason = "manifest_hash_mismatch"
            results.append(r)
            continue
        # Validate decode / dimensions / readability BEFORE retaining.
        try:
            r.dimensions = _validate_decode(data)
        except ValueError as exc:
            r.reason = f"decode_failed: {exc}"      # do not persist malformed bytes
            results.append(r)
            continue
        # Retain through the existing service (real DB; EXIF-stripped; consent-gated).
        r.ingestion_attempted = True
        retained = retain_image(
            db, data=data, tenant_id=tenant_id, instrument_type=TRC001_INSTRUMENT_ID,
            content_type=str(entry.get("content_type") or "image/jpeg"),
            source="trc001_research_intake", uploaded_by="research-operator", consent=True)
        if retained is None:
            r.reason = "retention_disabled_or_no_consent"
            results.append(r)
            continue
        r.retained_image_id = retained.id
        r.stored_sha256 = retained.sha256
        r.exif_stripped = bool(retained.exif_stripped)
        # Retrieve the actual stored bytes and confirm readability + integrity.
        fetched = (
            db.query(RetainedImage)
            .filter(RetainedImage.tenant_id == tenant_id, RetainedImage.id == retained.id)
            .first()
        )
        if fetched is not None and fetched.image_bytes:
            r.retrieval_verified = True
            r.checksum_match = (hashlib.sha256(fetched.image_bytes).hexdigest() == retained.sha256)
            try:
                _validate_decode(fetched.image_bytes)
            except ValueError:
                r.checksum_match = False
        # Tenant isolation: the row is not visible under a different tenant.
        other = (
            db.query(RetainedImage)
            .filter(RetainedImage.tenant_id != tenant_id, RetainedImage.id == retained.id)
            .first()
        )
        r.tenant_isolation_ok = other is None
        r.ingestion_successful = bool(r.retrieval_verified and r.checksum_match and r.tenant_isolation_ok)
        if r.ingestion_successful:
            imported += 1
        results.append(r)

    status = "INGESTED" if imported == len(TRC001_IMAGES) else "PARTIAL" if imported else "NOT_INGESTED"
    return IntakeReport(
        status=status, images=results, imported_count=imported,
        note="Both images remain ground_truth_status=unknown, baseline pending_review, and "
             "research-training-ineligible. The borescope image is a display photograph, not a raw export.",
    )
