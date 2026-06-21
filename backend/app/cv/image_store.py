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
    key = f"inspections/{tenant_id}/{inference_id}.bin"

    if image_bytes is None:
        # Try fetching from URL (best-effort; don't fail the pipeline if unreachable)
        image_bytes = _try_fetch(image_url)

    if image_bytes is None:
        return ArchiveResult(stored=False, object_key=key, backend=_BACKEND,
                             error="Image bytes unavailable and URL fetch failed")

    checksum = hashlib.sha256(image_bytes).hexdigest()

    try:
        if _BACKEND == "s3":
            return _store_s3(key, image_bytes, checksum, tenant_id)
        if _BACKEND == "gcs":
            return _store_gcs(key, image_bytes, checksum, tenant_id)
        if _BACKEND == "local":
            return _store_local(key, image_bytes, checksum)
        # noop
        return ArchiveResult(stored=False, object_key=key, backend="noop",
                             size_bytes=len(image_bytes), checksum_sha256=checksum)
    except Exception as exc:
        return ArchiveResult(stored=False, object_key=key, backend=_BACKEND,
                             error=str(exc))


def _try_fetch(url: str) -> bytes | None:
    if not url or not url.startswith("http"):
        return None
    try:
        import httpx
        r = httpx.get(url, timeout=5.0, follow_redirects=True)
        return r.content if r.status_code == 200 else None
    except Exception:
        return None


def _store_local(key: str, data: bytes, checksum: str) -> ArchiveResult:
    path = _LOCAL_DIR / key
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
