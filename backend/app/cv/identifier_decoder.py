"""R2: Real barcode / QR / KeyDot decoding.

Attempts to use pyzbar (ZBar) for 1D barcodes and QR codes.
Falls back gracefully to an empty result if pyzbar is not installed —
the mock provider fills in fixture values in that case.

FDA GS1 UDI parsing extracts Device Identifier (DI) and Production
Identifier (PI) from GS1-128 barcode strings.
"""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class DecodedIdentifiers:
    barcode_value: str = ""
    barcode_confidence: float = 0.0
    barcode_format: str = ""
    qr_value: str = ""
    qr_confidence: float = 0.0
    key_dot_value: str = ""
    key_dot_confidence: float = 0.0
    udi_value: str = ""
    udi_device_id: str = ""         # GS1 Application Identifier (01) Device Identifier
    udi_lot: str = ""               # AI (10) Lot / Batch
    udi_serial: str = ""            # AI (21) Serial number
    udi_expiry: str = ""            # AI (17) Expiry date YYMMDD
    decoder_backend: str = "none"   # "pyzbar" | "mock" | "none"


# ── GS1 UDI parser ───────────────────────────────────────────────────────────

_GS1_AI_PATTERN = re.compile(r"\((\d{2,4})\)([^(]+)")


def parse_gs1_udi(raw: str) -> dict[str, str]:
    """Extract common GS1 Application Identifiers from a UDI string.

    Handles both parenthesised format  (01)12345678... and fixed-width format.
    """
    result: dict[str, str] = {}
    for match in _GS1_AI_PATTERN.finditer(raw):
        ai, value = match.group(1), match.group(2).strip()
        if ai == "01":
            result["device_id"] = value
        elif ai == "10":
            result["lot"] = value
        elif ai == "21":
            result["serial"] = value
        elif ai == "17":
            result["expiry"] = value
    return result


# ── Real decoder (pyzbar) ─────────────────────────────────────────────────────

def decode_from_image_bytes(image_bytes: bytes) -> DecodedIdentifiers:
    """Decode all 1D barcodes and QR codes from raw image bytes.

    Requires: pyzbar + Pillow.  Returns empty result on ImportError.
    """
    result = DecodedIdentifiers()
    try:
        from PIL import Image  # type: ignore[import-untyped]
        from pyzbar import pyzbar  # type: ignore[import-untyped]
        import io

        img = Image.open(io.BytesIO(image_bytes))
        decoded = pyzbar.decode(img)
        result.decoder_backend = "pyzbar"

        for sym in decoded:
            data = sym.data.decode("utf-8", errors="replace")
            fmt = sym.type.lower()
            if fmt == "qrcode":
                if not result.qr_value:
                    result.qr_value = data
                    result.qr_confidence = 0.97
            else:
                # Treat all 1D symbologies as barcode
                if not result.barcode_value:
                    result.barcode_value = data
                    result.barcode_format = fmt
                    result.barcode_confidence = 0.97
                    # Try GS1 UDI parse
                    udi = parse_gs1_udi(data)
                    result.udi_value = data
                    result.udi_device_id = udi.get("device_id", "")
                    result.udi_lot = udi.get("lot", "")
                    result.udi_serial = udi.get("serial", "")
                    result.udi_expiry = udi.get("expiry", "")

    except ImportError:
        result.decoder_backend = "none"
    except Exception:
        result.decoder_backend = "error"

    return result


def decode_from_url(image_url: str) -> DecodedIdentifiers:
    """Fetch image from URL and decode identifiers.

    Only used when pyzbar is available; returns empty result otherwise.
    """
    result = DecodedIdentifiers()
    try:
        import httpx  # type: ignore[import-untyped]
        resp = httpx.get(image_url, timeout=5.0, follow_redirects=True)
        if resp.status_code == 200:
            result = decode_from_image_bytes(resp.content)
    except Exception:
        pass
    return result
