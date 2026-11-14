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
    tenant_access_authorized: bool | None = None
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
    authorization_basis: str = ""
    missing_documentation: list = field(default_factory=list)
    note: str = ""

    def to_dict(self) -> dict:
        return {"status": self.status, "instrument_id": self.instrument_id,
                "images": [i.to_dict() for i in self.images], "imported_count": self.imported_count,
                "authorization_basis": self.authorization_basis,
                "missing_documentation": list(self.missing_documentation), "note": self.note}


def _blocked_images(reason: str) -> list:
    return [ImageIntakeResult(image_id=k, modality=v["modality"],
                              is_borescope_display_photo=v.get("is_borescope_display_photo", False),
                              raw_borescope_export=v.get("raw_borescope_export", False),
                              authorization="BLOCKED", reason=reason)
            for k, v in TRC001_IMAGES.items()]


def _safe_kit_path(kit_dir: str, filename: str) -> str:
    """Resolve a manifest filename to a path INSIDE the kit directory. Rejects
    absolute paths, home expansion, and any traversal that escapes the kit dir."""
    name = str(filename or "")
    if not name or os.path.isabs(name) or name.startswith("~") or "\x00" in name:
        raise ValueError("unsafe_or_absolute_filename")
    base = os.path.realpath(kit_dir)
    full = os.path.realpath(os.path.join(base, name))
    if full != base and not full.startswith(base + os.sep):
        raise ValueError("path_escapes_kit_dir")
    return full


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


def _manifest_dimensions(entry: dict) -> tuple | None:
    """Pull declared (width, height) from a manifest entry, if present. Supports
    flat ``width``/``height`` keys and a ``dimensions``/``size`` [w, h] pair."""
    w = entry.get("width")
    h = entry.get("height")
    if w is None or h is None:
        pair = entry.get("dimensions") or entry.get("size")
        if isinstance(pair, (list, tuple)) and len(pair) == 2:
            w, h = pair[0], pair[1]
    if w is None or h is None:
        return None
    try:
        return (int(w), int(h))
    except (TypeError, ValueError):
        return None


def run_trc001_intake(
    db: Session, *, kit_dir: str | None, tenant_id: str, dataset_id: str, auth=None,
    authorization_basis: str = "institutional",
) -> IntakeReport:
    """Execute the TRC-001 intake, fail-closed. See module docstring for the order.

    ``authorization_basis`` selects how dataset authorization is resolved (both are
    fail-closed, both require a trusted authenticated tenant-matched actor):

    * ``"institutional"`` (default): approved institutional data-authorization +
      research-use consent + tenant consent + a dataset retention approval.
    * ``"owner_attested"``: an approved, non-withdrawn OWNER attestation for privately
      controlled nonclinical assets, authored by the authenticated owner, covering exactly
      the images' hashes, asserting ownership + permissible research use + retention +
      withdrawal. This is NOT institutional approval and NOT scientific verification;
      ground truth stays ``unknown`` and the images stay training-ineligible either way.
    """
    from research.lens_vision.scientific_authorization import (  # noqa: PLC0415
        REQ_RETENTION_AUTHORIZATION,
        ScientificAuthorizationError,
        authorize_tenant_actor,
        resolve_governance_approval,
        resolve_owner_attestation,
        verify_data_authorization,
    )

    # 1) Trusted, authenticated, tenant-matched actor. auth=None or an untrusted /
    #    cross-tenant context is refused BEFORE the kit or manifest is even read.
    try:
        authorized_actor = authorize_tenant_actor(db, auth, tenant_id=tenant_id)
    except ScientificAuthorizationError as exc:
        return IntakeReport(
            status="BLOCKED_AUTHORIZATION", images=_blocked_images(f"actor_not_authorized: {exc}"),
            missing_documentation=list(_REQUIRED_AUTHORIZATION_DOCS),
            note="No trusted authenticated tenant-matched actor. auth=None or an untrusted / "
                 "cross-tenant request context is refused; nothing loaded or retained; no IDs created.",
        )

    # 2) Private intake kit present?
    manifest_path = os.path.join(kit_dir, "manifest.json") if kit_dir else ""
    if not kit_dir or not os.path.exists(manifest_path):
        return IntakeReport(
            status="BLOCKED_MISSING_INTAKE_KIT", images=_blocked_images("intake_kit_absent"),
            missing_documentation=["TRC-001-private-intake-kit.zip (manifest + operator JPEG bytes)"],
            note="No private intake kit/manifest present. Nothing loaded or retained; no IDs created.",
        )

    # 3) Load the manifest (needed for owner-attestation hash binding below).
    with open(manifest_path, encoding="utf-8") as f:
        manifest = json.load(f)
    entries = {e.get("image_id"): e for e in manifest.get("images", [])}
    declared_hashes = [str(entries[k].get("sha256") or "") for k in TRC001_IMAGES
                       if k in entries and entries[k].get("sha256")]

    # 4) Authorization (fail-closed), resolved against governance records by basis:
    basis = str(authorization_basis or "institutional")
    try:
        if basis == "owner_attested":
            # Owner-attested privately controlled nonclinical asset. Distinct from
            # institutional approval; covers rights + permissible use + retention +
            # withdrawal, bound to exactly these image hashes.
            attestation = resolve_owner_attestation(
                db, auth, tenant_id=tenant_id, dataset_id=dataset_id, image_hashes=declared_hashes)
            authorization_label = f"resolved:owner_attested:attestation={attestation.approval_id}"
        else:
            # Institutional authorization: data-authorization + research-use consent +
            # tenant consent, plus a dataset-scoped RETENTION approval (not consent alone).
            verify_data_authorization(db, tenant_id=tenant_id, dataset_id=dataset_id, auth=auth)
            retention_approval = resolve_governance_approval(
                db, tenant_id=tenant_id, request_type=REQ_RETENTION_AUTHORIZATION,
                target_resource_id=dataset_id)
            authorization_label = f"resolved:institutional:retention_approval={retention_approval.id}"
    except ScientificAuthorizationError as exc:
        return IntakeReport(
            status="BLOCKED_AUTHORIZATION", images=_blocked_images(f"authorization_unresolved: {exc}"),
            authorization_basis=basis, missing_documentation=list(_REQUIRED_AUTHORIZATION_DOCS),
            note="Authorization not resolved against governance records "
                 f"(basis={basis}). No bytes retained; no IDs created. "
                 "Capturing an image personally does not by itself establish research permission.",
        )

    # 5) Authorized — ingest each image.
    from app.models.retained_image import RetainedImage  # noqa: PLC0415
    from app.services.image_retention_service import retain_image  # noqa: PLC0415

    kit_base = os.path.realpath(kit_dir)
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
        # Reject absolute filenames or any path that escapes the private kit directory.
        try:
            fpath = _safe_kit_path(kit_base, entry.get("filename"))
        except ValueError as exc:
            r.reason = f"unsafe_filename_rejected: {exc}"
            results.append(r)
            continue
        if not os.path.isfile(fpath):
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
        # Validate decode / readability BEFORE retaining.
        try:
            r.dimensions = _validate_decode(data)
        except ValueError as exc:
            r.reason = f"decode_failed: {exc}"      # do not persist malformed bytes
            results.append(r)
            continue
        # Validate the ACTUAL decoded dimensions against the manifest metadata.
        declared = _manifest_dimensions(entry)
        if declared is not None and tuple(r.dimensions) != declared:
            r.reason = f"dimension_mismatch: decoded {tuple(r.dimensions)} != manifest {declared}"
            results.append(r)
            continue
        # Retain through the existing service (real DB; EXIF-stripped). Consent is a
        # necessary service precondition, but retention here is authorized by the
        # resolved authorization (institutional retention approval, or owner attestation)
        # resolved in step 4 — not by the caller passing consent=True alone.
        r.authorization = authorization_label
        r.ingestion_attempted = True
        retained = retain_image(
            db, data=data, tenant_id=tenant_id, instrument_type=TRC001_INSTRUMENT_ID,
            content_type=str(entry.get("content_type") or "image/jpeg"),
            source="trc001_research_intake", uploaded_by=authorized_actor, consent=True)
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
        # Explicit tenant-access AUTHORIZATION test (not a storage lookup): the
        # authenticated actor's tenant, the ingestion tenant and the stored row's tenant
        # must all be the same principal. This gates success on authorization, not on a
        # query happening to return a row.
        r.tenant_access_authorized = bool(
            retained is not None
            and str(getattr(auth, "tenant_id", "") or "") == str(tenant_id or "")
            and str(retained.tenant_id or "") == str(tenant_id or "")
        )
        # Defence-in-depth storage integrity check: the row is not visible to a different
        # tenant. This is a SECONDARY isolation check, never the authorization decision.
        other = (
            db.query(RetainedImage)
            .filter(RetainedImage.tenant_id != tenant_id, RetainedImage.id == retained.id)
            .first()
        )
        r.tenant_isolation_ok = other is None
        r.ingestion_successful = bool(
            r.retrieval_verified and r.checksum_match
            and r.tenant_access_authorized and r.tenant_isolation_ok
        )
        if r.ingestion_successful:
            imported += 1
        results.append(r)

    status = "INGESTED" if imported == len(TRC001_IMAGES) else "PARTIAL" if imported else "NOT_INGESTED"
    return IntakeReport(
        status=status, images=results, imported_count=imported, authorization_basis=basis,
        note="Both images remain ground_truth_status=unknown, baseline pending_review, and "
             "research-training-ineligible (owner-attested authorization does not confer "
             "verified-normal/scientific/clinical status). The borescope image is a display "
             "photograph, not a raw export.",
    )
