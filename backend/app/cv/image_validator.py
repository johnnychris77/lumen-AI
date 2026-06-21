"""R1: Image URL validation and SSRF protection.

Called at the API boundary before any URL is fetched or stored.
Returns a list of warning strings — empty list means valid.
"""
from __future__ import annotations

import base64
import ipaddress
from urllib.parse import urlparse

_PRIVATE_NETS = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("100.64.0.0/10"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]

_ALLOWED_SCHEMES = {"https", "http"}
_ALLOWED_EXTS = {".jpg", ".jpeg", ".png", ".tiff", ".tif", ".bmp", ".webp"}
_MAX_B64_BYTES = 20 * 1024 * 1024  # 20 MB

_INTERNAL_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0", "::1"}


def validate_image_url(url: str) -> list[str]:
    """Return validation warnings for an image URL. Empty list = valid."""
    if not url:
        return []
    warnings: list[str] = []
    try:
        parsed = urlparse(url)
    except Exception:
        return ["Invalid URL format"]

    if parsed.scheme not in _ALLOWED_SCHEMES:
        warnings.append(f"URL scheme '{parsed.scheme}' not allowed; use https")

    host = (parsed.hostname or "").lower()

    if host in _INTERNAL_HOSTS or host.endswith(".local") or host.endswith(".internal"):
        warnings.append(f"SSRF risk: host '{host}' is an internal address")

    try:
        ip = ipaddress.ip_address(host)
        for net in _PRIVATE_NETS:
            if ip in net:
                warnings.append(f"SSRF risk: IP {ip} is in private range {net}")
                break
    except ValueError:
        pass  # hostname, not an IP — fine

    path = parsed.path.lower()
    if path and "." in path:
        ext = "." + path.rsplit(".", 1)[-1].split("?")[0]
        if ext and ext not in _ALLOWED_EXTS:
            warnings.append(
                f"URL extension '{ext}' may not be an image; "
                f"expected {', '.join(sorted(_ALLOWED_EXTS))}"
            )

    return warnings


def validate_b64_payload(b64_str: str) -> list[str]:
    """Return validation warnings for a base64 image payload."""
    if not b64_str:
        return []
    warnings: list[str] = []

    raw_b64 = b64_str.split(",", 1)[-1] if "," in b64_str else b64_str
    try:
        raw = base64.b64decode(raw_b64, validate=True)
    except Exception:
        return ["image_data_b64 is not valid base64"]

    if len(raw) > _MAX_B64_BYTES:
        warnings.append(
            f"image_data_b64 payload ({len(raw) // 1024 // 1024} MB) "
            f"exceeds 20 MB limit"
        )

    # Magic byte detection
    if raw[:3] == b"\xff\xd8\xff":
        pass  # JPEG
    elif raw[:8] == b"\x89PNG\r\n\x1a\n":
        pass  # PNG
    elif raw[:4] in (b"II*\x00", b"MM\x00*"):
        pass  # TIFF
    elif raw[:4] == b"RIFF" and raw[8:12] == b"WEBP":
        pass  # WebP
    else:
        warnings.append(
            "image_data_b64 magic bytes do not match a recognized format "
            "(JPEG/PNG/TIFF/WebP)"
        )

    return warnings
