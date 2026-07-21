import os
from pydantic import BaseModel

class Settings(BaseModel):
    # SEC-H-01 — single canonical dev-only fallback, matching the value the
    # production startup guard rejects (app/main.py). The previous divergent
    # "dev-secret" default was a second weak signing key the guard did not catch.
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-change-in-production")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql+psycopg2://postgres:postgres@db:5432/lumenai")
    S3_BUCKET: str = os.getenv("S3_BUCKET", "lumenai-artifacts")
    S3_ENDPOINT: str = os.getenv("S3_ENDPOINT", "http://minio:9000")
    S3_ACCESS_KEY: str = os.getenv("S3_ACCESS_KEY", "")
    S3_SECRET_KEY: str = os.getenv("S3_SECRET_KEY", "")
    S3_REGION: str = os.getenv("S3_REGION", "us-east-1")

settings = Settings()
