import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO


@dataclass
class StoredObject:
    storage_uri: str
    public_url: str
    backend: str
    bucket: str
    object_key: str


def _storage_backend() -> str:
    return os.environ.get("LUMENAI_STORAGE_BACKEND", "local").strip().lower()


def _local_root() -> str:
    return os.environ.get("LUMENAI_LOCAL_STORAGE_DIR", "/tmp/lumenai-storage")


def _s3_client():
    import boto3

    endpoint_url = os.environ.get("LUMENAI_S3_ENDPOINT_URL") or None
    access_key = os.environ.get("LUMENAI_S3_ACCESS_KEY_ID")
    secret_key = os.environ.get("LUMENAI_S3_SECRET_ACCESS_KEY")
    region = os.environ.get("LUMENAI_S3_REGION", "us-east-1")

    kwargs = {
        "service_name": "s3",
        "region_name": region,
    }

    if endpoint_url:
        kwargs["endpoint_url"] = endpoint_url

    if access_key and secret_key:
        kwargs["aws_access_key_id"] = access_key
        kwargs["aws_secret_access_key"] = secret_key

    return boto3.client(**kwargs)


def save_upload_file(
    *,
    file_obj: BinaryIO,
    file_name: str,
    object_key: str,
    content_type: str = "application/octet-stream",
) -> StoredObject:
    backend = _storage_backend()

    if backend == "s3":
        bucket = os.environ["LUMENAI_S3_BUCKET"]
        client = _s3_client()

        client.upload_fileobj(
            file_obj,
            bucket,
            object_key,
            ExtraArgs={"ContentType": content_type or "application/octet-stream"},
        )

        endpoint_url = os.environ.get("LUMENAI_S3_ENDPOINT_URL", "").rstrip("/")
        if endpoint_url:
            public_url = f"{endpoint_url}/{bucket}/{object_key}"
        else:
            public_url = f"s3://{bucket}/{object_key}"

        return StoredObject(
            storage_uri=f"s3://{bucket}/{object_key}",
            public_url=public_url,
            backend="s3",
            bucket=bucket,
            object_key=object_key,
        )

    # Local fallback for development.
    root = Path(_local_root())
    target = root / object_key
    target.parent.mkdir(parents=True, exist_ok=True)

    with target.open("wb") as output:
        shutil.copyfileobj(file_obj, output)

    return StoredObject(
        storage_uri=str(target),
        public_url=str(target),
        backend="local",
        bucket="",
        object_key=object_key,
    )


def open_stored_object(storage_uri: str):
    if storage_uri.startswith("s3://"):
        import tempfile

        bucket_and_key = storage_uri.replace("s3://", "", 1)
        bucket, object_key = bucket_and_key.split("/", 1)

        client = _s3_client()
        tmp = tempfile.NamedTemporaryFile(delete=False)
        tmp.close()

        client.download_file(bucket, object_key, tmp.name)
        return tmp.name

    return storage_uri
