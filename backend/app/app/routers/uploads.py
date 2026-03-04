from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
import os, boto3

router = APIRouter(prefix="/uploads", tags=["uploads"])

S3_ENDPOINT   = os.getenv("S3_ENDPOINT")
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY")
S3_BUCKET     = os.getenv("S3_BUCKET", "lumenai")
S3_REGION     = os.getenv("S3_REGION", "us-east-1")
S3_SSL        = os.getenv("S3_SSL", "false").lower() == "true"

s3 = boto3.client(
    "s3",
    endpoint_url=S3_ENDPOINT,
    aws_access_key_id=S3_ACCESS_KEY,
    aws_secret_access_key=S3_SECRET_KEY,
    region_name=S3_REGION,
    use_ssl=S3_SSL,
)

class PutReq(BaseModel):
    key: str
    content_type: str

@router.post("/presign-put")
def presign_put(req: PutReq):
    try:
        url = s3.generate_presigned_url(
            "put_object",
            Params={"Bucket": S3_BUCKET, "Key": req.key, "ContentType": req.content_type},
            ExpiresIn=900,
        )
        return {"url": url}
    except Exception as e:
        raise HTTPException(500, str(e))

@router.get("/presign-get")
def presign_get(key: str = Query(...)):
    try:
        url = s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": S3_BUCKET, "Key": key},
            ExpiresIn=900,
        )
        return {"url": url}
    except Exception as e:
        raise HTTPException(500, str(e))
