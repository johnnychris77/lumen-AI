from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class AuthConfig:
    auth_mode: str
    enable_dev_auth: bool
    jwt_issuer: str | None
    jwt_audience: str | None
    jwt_algorithm: str
    jwt_secret: str | None
    jwt_public_key: str | None


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default

    return value.strip().lower() in {
        "1",
        "true",
        "yes",
        "y",
        "on",
    }


def get_auth_config() -> AuthConfig:
    return AuthConfig(
        auth_mode=os.getenv("AUTH_MODE", "jwt").strip().lower(),
        enable_dev_auth=_env_bool("ENABLE_DEV_AUTH", default=False),
        jwt_issuer=os.getenv("JWT_ISSUER"),
        jwt_audience=os.getenv("JWT_AUDIENCE"),
        jwt_algorithm=os.getenv("JWT_ALGORITHM", "HS256"),
        jwt_secret=os.getenv("JWT_SECRET"),
        jwt_public_key=os.getenv("JWT_PUBLIC_KEY"),
    )
