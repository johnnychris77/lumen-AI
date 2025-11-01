from datetime import timedelta
import os
from typing import Optional

import boto3
from botocore.client import Config
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from backend.app.db.session import SessionLocal
from backend.app.models.review import ReviewItem  # adjust import if your model path differs

router = APIRouter()

# --- S3 / MinIO config ---
S3_ENDPOINT  = os.getenv("S3_ENDPOINT", "http://minio:9000")
S3_REGION    = os.getenv("S3_REGION", "us-east-1")
S3_ACCESS    = os.getenv("S3_ACCESS_KEY", "minioadmin")
S3_SECRET    = os.getenv("S3_SECRET_KEY", "minioadmin")
S3_BUCKET    = os.getenv("S3_BUCKET", "lumenai-artifacts")
S3_USE_SSL   = os.getenv("S3_USE_SSL", "false").lower() in ("1", "true", "yes")
URL_EXPIRES  = int(os.getenv("S3_URL_EXPIRES", "3600"))

# Optional: public base URL for links visible from host/browser
PUBLIC_BASE  = os.getenv("PUBLIC_S3_BASE_URL")  # e.g. http://localhost:9000
if PUBLIC_BASE is None:
    # fallback to service name inside docker; host may not resolve this
    PUBLIC_BASE = S3_ENDPOINT

def _client():
    return boto3.client(
        "s3",
        endpoint_url=S3_ENDPOINT,
        aws_access_key_id=S3_ACCESS,
        aws_secret_access_key=S3_SECRET,
        region_name=S3_REGION,
        use_ssl=S3_USE_SSL,
        config=Config(s3={"addressing_style": "path"})
    )

# ---------- Schemas ----------
class PresignPutIn(BaseModel):
    key: str
    content_type: str

class PresignOut(BaseModel):
    url: str
    expires_in: int

class RegisterIn(BaseModel):
    key: str
    predicted_label: Optional[str] = None
    confidence: Optional[float] = None

# ---------- Presign PUT ----------
@router.post("/presign-put", response_model=PresignOut)
def presign_put(body: PresignPutIn):
    s3 = _client()
    try:
        url = s3.generate_presigned_url(
            ClientMethod="put_object",
            Params={
                "Bucket": S3_BUCKET,
                "Key": body.key,
                "ContentType": body.content_type,
            },
            ExpiresIn=URL_EXPIRES
        )
        return {"url": url, "expires_in": URL_EXPIRES}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ---------- Presign GET ----------
@router.get("/presign-get", response_model=PresignOut)
def presign_get(key: str = Query(..., description="Object key in the bucket")):
    s3 = _client()
    try:
        url = s3.generate_presigned_url(
            ClientMethod="get_object",
            Params={"Bucket": S3_BUCKET, "Key": key},
            ExpiresIn=URL_EXPIRES
        )
        return {"url": url, "expires_in": URL_EXPIRES}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ---------- Register uploaded object as a ReviewItem ----------
@router.post("/register")
def register(body: RegisterIn):
    # Build a browser-visible URL to the object
    # Use PUBLIC_S3_BASE_URL if provided (recommended: http://localhost:9000)
    object_url = f"{PUBLIC_BASE.rstrip('/')}/{S3_BUCKET}/{body.key}"

    db = SessionLocal()
    try:
        item = ReviewItem(
            image_url=object_url,
            predicted_label=body.predicted_label,
            confidence=body.confidence
        )
        db.add(item)
        db.commit()
        db.refresh(item)
        return {"id": item.id, "image_url": item.image_url}
    finally:
        db.close()
