from __future__ import annotations

import os
import json
import hmac
import hashlib
from typing import Any


def _truthy(v: str | None) -> bool:
    return str(v or "").strip().lower() in {"1", "true", "yes", "on"}


def signing_enabled() -> bool:
    return _truthy(os.getenv("LUMENAI_EVIDENCE_SIGNING_ENABLED", "false"))


def signing_secret() -> str:
    return os.getenv("LUMENAI_EVIDENCE_SIGNING_SECRET", "").strip()


def canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def sha256_hex(payload: dict[str, Any]) -> str:
    canonical = canonical_json(payload).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def hmac_sha256_hex(payload: dict[str, Any]) -> str:
    secret = signing_secret()
    if not secret:
        return ""
    canonical = canonical_json(payload).encode("utf-8")
    return hmac.new(secret.encode("utf-8"), canonical, hashlib.sha256).hexdigest()


def sign_manifest(payload: dict[str, Any]) -> dict[str, Any]:
    base = {
        "algorithm": "sha256",
        "hash": sha256_hex(payload),
        "signing_enabled": signing_enabled(),
    }

    if signing_enabled() and signing_secret():
        base["signature_algorithm"] = "hmac-sha256"
        base["signature"] = hmac_sha256_hex(payload)
    else:
        base["signature_algorithm"] = "none"
        base["signature"] = ""

    return base


def verify_manifest(payload: dict[str, Any], manifest: dict[str, Any]) -> dict[str, Any]:
    computed_hash = sha256_hex(payload)
    provided_hash = str(manifest.get("integrity", {}).get("hash", ""))
    hash_valid = computed_hash == provided_hash

    expected_sig = ""
    provided_sig = str(manifest.get("integrity", {}).get("signature", ""))

    if signing_enabled() and signing_secret():
        expected_sig = hmac_sha256_hex(payload)
        signature_valid = expected_sig == provided_sig
    else:
        signature_valid = provided_sig == ""

    return {
        "hash_valid": hash_valid,
        "signature_valid": signature_valid,
        "computed_hash": computed_hash,
        "expected_signature": expected_sig,
        "provided_signature": provided_sig,
    }
