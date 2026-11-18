"""R7: Image archival to object storage.

Archives inspection images to a tenant-namespaced location so the audit
record is self-contained regardless of source URL lifetime.

Backend is selected via IMAGE_STORE_BACKEND env var:
  local   — writes to IMAGE_STORE_LOCAL_DIR (default /tmp/lumenai-images)
  s3      — writes to S3_BUCKET / s3://{bucket}/inspections/{tenant}/{id}.jpg
  gcs     — writes to GCS_BUCKET / gs://{bucket}/...
  noop    — records metadata only, no bytes stored (default in tests)
"""
from __future__ import annotations

import hashlib
import os
import re
from dataclasses import dataclass
from pathlib import Path


_BACKEND = os.environ.get("IMAGE_STORE_BACKEND", "noop")
_LOCAL_DIR = Path(os.environ.get("IMAGE_STORE_LOCAL_DIR", "/tmp/lumenai-images"))  # noqa: S108
_S3_BUCKET = os.environ.get("S3_BUCKET", "")
_GCS_BUCKET = os.environ.get("GCS_BUCKET", "")


@dataclass
class ArchiveResult:
    stored: bool
    object_key: str = ""
    backend: str = "noop"
    size_bytes: int = 0
    checksum_sha256: str = ""
    error: str = ""


def archive_image(
    *,
    image_bytes: bytes | None,
    image_url: str,
    inference_id: str,
    tenant_id: str,
) -> ArchiveResult:
    """Archive image bytes (or record the URL if bytes are unavailable).

    Returns an ArchiveResult with the internal object_key for storage in
    CVInferenceRecord.archived_image_key.
    """
    # Key components are sanitised so a tenant/inference identifier can never
    # introduce a path separator or traversal segment into the object key.
    key = f"inspections/{_safe_component(tenant_id)}/{_safe_component(inference_id)}.bin"

    # P4.7.1: with no archive backend configured there is nothing to store, so
    # there is no reason to retrieve the image at all. (Previously the URL was
    # fetched on every analysis and the bytes then discarded.)
    if _BACKEND not in ("s3", "gcs", "local"):
        return ArchiveResult(stored=False, object_key=key, backend="noop")

    if image_bytes is None:
        # Only through the SSRF-safe, allow-listed fetcher (best-effort).
        image_bytes = _try_fetch(image_url)

    if image_bytes is None:
        return ArchiveResult(stored=False, object_key=key, backend=_BACKEND,
                             error="Image bytes unavailable (no permitted retrieval route)")

    checksum = hashlib.sha256(image_bytes).hexdigest()

    try:
        if _BACKEND == "s3":
            return _store_s3(key, image_bytes, checksum, tenant_id)
        if _BACKEND == "gcs":
            return _store_gcs(key, image_bytes, checksum, tenant_id)
        return _store_local(key, image_bytes, checksum)
    except Exception as exc:
        # Report the failure class only — never bucket names, keys or credentials.
        return ArchiveResult(stored=False, object_key=key, backend=_BACKEND,
                             error=f"Archive failed ({type(exc).__name__})")


def _try_fetch(url: str) -> bytes | None:
    """P4.7.1 (SEC-R2-02): prohibited / non-allow-listed URLs are never
    requested; redirects are not followed; size and time are bounded."""
    from app.cv.safe_fetch import try_fetch_image_bytes

    return try_fetch_image_bytes(url)


def _safe_component(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_-]", "_", str(value or ""))[:120]
    return cleaned or "unknown"


def _store_local(key: str, data: bytes, checksum: str) -> ArchiveResult:
    path = (_LOCAL_DIR / key).resolve()
    if not path.is_relative_to(_LOCAL_DIR.resolve()):
        raise ValueError("archive key escapes the archive directory")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return ArchiveResult(stored=True, object_key=str(path), backend="local",
                         size_bytes=len(data), checksum_sha256=checksum)


def _store_s3(key: str, data: bytes, checksum: str, tenant_id: str) -> ArchiveResult:
    import boto3  # type: ignore[import-untyped]
    s3 = boto3.client("s3")
    s3.put_object(
        Bucket=_S3_BUCKET,
        Key=key,
        Body=data,
        Metadata={"tenant_id": tenant_id, "sha256": checksum},
    )
    return ArchiveResult(stored=True, object_key=f"s3://{_S3_BUCKET}/{key}",
                         backend="s3", size_bytes=len(data), checksum_sha256=checksum)


def _store_gcs(key: str, data: bytes, checksum: str, tenant_id: str) -> ArchiveResult:
    from google.cloud import storage as gcs_storage  # type: ignore[import-untyped]
    client = gcs_storage.Client()
    bucket = client.bucket(_GCS_BUCKET)
    blob = bucket.blob(key)
    blob.metadata = {"tenant_id": tenant_id, "sha256": checksum}
    blob.upload_from_string(data, content_type="application/octet-stream")
    return ArchiveResult(stored=True, object_key=f"gs://{_GCS_BUCKET}/{key}",
                         backend="gcs", size_bytes=len(data), checksum_sha256=checksum)
